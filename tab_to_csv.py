# -*- coding: utf-8 -*-
import csv
import re

COLUMNS = [
    "real_first_name", "real_last_name", "birth_date", "p_source",
    "flight_date", "flight_time", "flight_no", "codeshare",
    "dep_city", "dep_airport", "dep_country",
    "arr_city", "arr_airport", "arr_country",
    "e_code", "e_ticket",
    "docs", "seat", "meal", "booking_class", "fare_basis", "baggage", "loyalty_pairs"
]

RE_HEAD = re.compile(
    r"""^(?P<PaxName>.+?)\s{2,}
        (?P<PaxBirthDate>\S+)\s{2,}
        (?P<DepartDate>\d{4}-\d{2}-\d{2})\s{2,}
        (?P<DepartTime>\d{2}:\d{2})\s{2,}
        (?P<ArrivalDate>\d{4}-\d{2}-\d{2})\s{2,}
        (?P<ArrivalTime>\d{2}:\d{2})\s{2,}
        (?P<FlightCode>[A-Z]{2}\d+)
        (?P<Codeshare>[A-Z]{2,3})\s+
        (?P<From>[A-Z]{3})\s+
        (?P<Dest>[A-Z]{3})\s+
        (?P<PNR>[A-Z0-9]{6})
        (?P<eTicket>\d{15,16})\s+
        (?P<rest>.*)$
    """,
    re.VERBOSE
)


def parse_tail(rest: str):
    tokens = rest.split()
    docs = seat = meal = booking_class = fare_basis = baggage = loyalty_pairs = ""
    i = 0

    if i < len(tokens):
        if tokens[i].upper() == "N/A":
            docs = "N/A"
            i += 1
        else:
            if i + 1 < len(tokens) and tokens[i].isdigit() and tokens[i + 1].isdigit():
                docs = f"{tokens[i]} {tokens[i + 1]}"
                i += 2
            else:
                docs = tokens[i]
                i += 1

    if i < len(tokens):
        seat = tokens[i]
        i += 1
        if seat.upper() == "N/A":
            seat = ""

    if i < len(tokens) and re.fullmatch(r"[A-Z]{3,4}", tokens[i]) and not re.fullmatch(r"[A-Z]", tokens[i]):
        meal = tokens[i]
        i += 1

    if i < len(tokens) and re.fullmatch(r"[A-Z]", tokens[i]):
        booking_class = tokens[i]
        i += 1

    if i < len(tokens):
        fare_token = tokens[i]
        i += 1
        core = fare_token
        if booking_class and core.startswith(booking_class):
            core = core[1:]

        m = re.match(r"^([A-Z][A-Z0-9]+?)(\d+PC|[0-9#F]|[0-9]{1,2}KG)$", core, flags=re.IGNORECASE)
        if m:
            fare_basis = m.group(1)
            baggage = m.group(2)
        else:
            fare_basis = core
            if i < len(tokens):
                nxt = tokens[i]
                if (re.fullmatch(r"\d+PC", nxt, flags=re.IGNORECASE) or
                        re.fullmatch(r"[#FS0-9]", nxt) or
                        re.fullmatch(r"\d{1,2}KG", nxt, flags=re.IGNORECASE) or
                        nxt.upper() in {"0PC", "1PC", "2PC"}):
                    baggage = nxt
                    i += 1

    for j in range(i, len(tokens)):
        if tokens[j].startswith("FF#"):
            prog = tokens[j][3:].strip()
            number = tokens[j + 1] if (j + 1 < len(tokens) and re.fullmatch(r"\d+", tokens[j + 1])) else ""
            if prog:
                loyalty_pairs = f"{prog}::{number}"
            break

    return docs, seat, meal, booking_class, fare_basis, baggage, loyalty_pairs


def parse_line(line: str, p_source="tab"):
    m = RE_HEAD.match(line.rstrip())
    if not m:
        return None, f"HEAD_PARSE_FAIL: {line[:160]}..."

    g = m.groupdict()

    parts = g["PaxName"].strip().split()
    first = parts[0] if parts else ""
    last = parts[1] if len(parts) > 1 else ""

    docs, seat, meal, booking_class, fare_basis, baggage, loyalty_pairs = parse_tail(g["rest"])

    row = {
        "real_first_name": first,
        "real_last_name": last,
        "birth_date": "" if g["PaxBirthDate"].upper() == "N/A" else g["PaxBirthDate"],
        "p_source": p_source,
        "flight_date": g["DepartDate"],
        "flight_time": g["DepartTime"],
        "flight_no": g["FlightCode"],
        "codeshare": "0",
        "dep_city": "",
        "dep_airport": g["From"],
        "dep_country": "",
        "arr_city": "",
        "arr_airport": g["Dest"],
        "arr_country": "",
        "e_code": g["PNR"],
        "e_ticket": g["eTicket"],
        "docs": docs,
        "seat": seat,
        "meal": meal,
        "booking_class": booking_class,
        "fare_basis": fare_basis,
        "baggage": baggage,
        "loyalty_pairs": loyalty_pairs
    }
    return row, None


def convert(input_path: str, output_path: str, p_source="tab"):
    bad = 0
    with open(output_path, "w", newline="", encoding="utf-8") as fout, \
            open(input_path, "r", encoding="utf-8") as fin:
        writer = csv.DictWriter(fout, fieldnames=COLUMNS, delimiter=";", lineterminator="\n")
        writer.writeheader()

        first = fin.readline()
        if first and not first.strip().startswith("PaxName"):
            row, err = parse_line(first, p_source)
            if row:
                writer.writerow(row)
            else:
                bad += 1

        for line in fin:
            if not line.strip():
                continue
            row, err = parse_line(line, p_source)
            if row:
                writer.writerow(row)
            else:
                bad += 1


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("input_tab")
    ap.add_argument("output_csv")
    ap.add_argument("--source", dest="p_source", default="tab")
    args = ap.parse_args()
    convert(args.input_tab, args.output_csv, p_source=args.p_source)
