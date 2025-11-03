import argparse
import csv
import os
import re
import xml.etree.ElementTree as ET

ALNUM_RE = re.compile(r"[^A-Za-z0-9]")

COLUMNS = [
    "uid",
    "real_first_name",
    "real_last_name",
    "p_source",
    "flight_date",
    "flight_no",
    "codeshare",
    "dep_city", "dep_airport", "dep_country",
    "arr_city", "arr_airport", "arr_country",
    "nickname",
    "docs_pairs",
    "loyalty_pairs",
    "booking_class",
    "fare_basis",
    "n_docs",
    "n_loyalty",
]


def upcode(s: str) -> str:
    return (s or "").strip().upper()


def clean_number(s: str) -> str:
    return ALNUM_RE.sub("", (s or ""))


def parse_xml_to_csv(input_xml: str, output_csv: str, p_source_hint: str = ""):
    p_source = (p_source_hint or os.path.splitext(os.path.basename(input_xml))[0]).strip()

    with open(output_csv, "w", newline="", encoding="utf-8", buffering=1024 * 1024) as fout:
        writer = csv.DictWriter(
            fout, fieldnames=COLUMNS, delimiter=";", lineterminator="\n", quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()

        cur_uid = ""
        cur_first = ""
        cur_last = ""
        cur_prog = ""
        cur_prog_number = ""

        for event, elem in ET.iterparse(input_xml, events=("start", "end")):
            tag = elem.tag

            if event == "start":
                if tag == "user":
                    cur_uid = (elem.attrib.get("uid") or "").strip()
                    cur_first = cur_last = ""
                    cur_prog = cur_prog_number = ""
                elif tag == "name":
                    cur_first = (elem.attrib.get("first") or "").strip()
                    cur_last = (elem.attrib.get("last") or "").strip()
                elif tag == "card":
                    card_num = (elem.attrib.get("number") or "").strip()
                    parts = card_num.split(None, 1)
                    cur_prog = upcode(parts[0]) if parts else ""
                    cur_prog_number = clean_number(parts[1]) if len(parts) > 1 else ""
                continue

            if tag == "activity":
                if (elem.attrib.get("type") or "").strip().lower() == "flight":
                    flight_no = upcode(elem.findtext("Code") or "")
                    flight_date = (elem.findtext("Date") or "").strip()
                    dep_airport = upcode(elem.findtext("Departure") or "")
                    arr_airport = upcode(elem.findtext("Arrival") or "")
                    fare_basis = (elem.findtext("Fare") or "").strip()

                    loyalty_pairs = f"{cur_prog}::{cur_prog_number}"

                    row = {
                        "uid": cur_uid,
                        "real_first_name": cur_first,
                        "real_last_name": cur_last,
                        "p_source": p_source,
                        "flight_date": flight_date,
                        "flight_no": flight_no,
                        "codeshare": "0",
                        "dep_city": "",
                        "dep_airport": dep_airport,
                        "dep_country": "",
                        "arr_city": "",
                        "arr_airport": arr_airport,
                        "arr_country": "",
                        "nickname": "",
                        "docs_pairs": "",
                        "loyalty_pairs": loyalty_pairs,
                        "booking_class": "",
                        "fare_basis": fare_basis,
                        "n_docs": "0",
                        "n_loyalty": "1",
                    }
                    writer.writerow(row)

                elem.clear()

            elif tag in ("card", "user", "activities", "cards", "name"):
                elem.clear()

            else:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_xml")
    ap.add_argument("output_csv")
    ap.add_argument("--source", dest="p_source", default="")
    args = ap.parse_args()

    parse_xml_to_csv(args.input_xml, args.output_csv, p_source_hint=args.p_source)


if __name__ == "__main__":
    main()
