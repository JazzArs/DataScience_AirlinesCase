import argparse
import csv
import os
import re

import ijson
import orjson

ALNUM_RE = re.compile(r"[^A-Za-z0-9]")

COLUMNS = [
    "real_first_name",
    "real_last_name",
    "p_source",
    "flight_date",
    "flight_no",
    "codeshare",
    "dep_city", "dep_airport", "dep_country",
    "arr_city", "arr_airport", "arr_country",
    "nickname",
    "docs_pairs", "loyalty_pairs", "booking_class", "fare_basis", "n_docs", "n_loyalty",
]


def safe_str(x: object) -> str:
    if x is None:
        return ""
    if isinstance(x, (dict, list)):
        return orjson.dumps(x).decode("utf-8")
    return str(x)


def extract(d: dict, *path, default: str = "") -> str:
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur.get(key)
    return safe_str(cur)


def to_bool01(val) -> str:
    s = str(val).strip().lower()
    if s in ("1", "true", "t", "yes", "y"):
        return "1"
    if s in ("0", "false", "f", "no", "n", "", "none", "null"):
        return "0"
    try:
        return "1" if float(s) != 0 else "0"
    except Exception:
        return "0"


def upcode(s: str) -> str:
    return (s or "").strip().upper()


def clean_number(s: str) -> str:
    return ALNUM_RE.sub("", (s or ""))


def build_docs_pairs(profile: dict) -> tuple[str, int]:
    docs = profile.get("Travel Documents") or []
    pairs = []
    if isinstance(docs, list):
        for entry in docs:
            if isinstance(entry, dict):
                for k, v in entry.items():
                    doc_type = upcode(str(k).replace(".", "").replace(" ", ""))
                    doc_num = clean_number(safe_str(v))
                    if doc_type or doc_num:
                        pairs.append(f"{doc_type}:{doc_num}")
            else:
                val = clean_number(safe_str(entry))
                if val:
                    pairs.append(f"UNKNOWN:{val}")
    return ("|".join(pairs), len(pairs))


def build_loyalty_pairs(profile: dict) -> tuple[str, int]:
    items = profile.get("Loyality Programm") or []
    pairs = []
    if isinstance(items, list):
        for lp in items:
            if not isinstance(lp, dict):
                continue
            prog = upcode(extract(lp, "programm"))
            status = extract(lp, "Status").strip()
            number = clean_number(extract(lp, "Number"))
            pairs.append(f"{prog}:{status}:{number}")
    return ("|".join(pairs), len(pairs))


def process_profile(profile: dict, writer: csv.DictWriter, p_source: str):
    real_first = extract(profile, "Real Name", "First Name")
    real_last = extract(profile, "Real Name", "Last Name")
    nickname = extract(profile, "NickName")

    docs_pairs, n_docs = build_docs_pairs(profile)
    loyalty_pairs, n_loyalty = build_loyalty_pairs(profile)

    flights = profile.get("Registered Flights") or []
    if not isinstance(flights, list):
        flights = []

    for fl in flights:
        if not isinstance(fl, dict):
            continue

        row = {
            "real_first_name": real_first,
            "real_last_name": real_last,
            "p_source": p_source,
            "flight_date": extract(fl, "Date"),
            "flight_no": upcode(extract(fl, "Flight")),
            "codeshare": to_bool01(extract(fl, "Codeshare")),
            "dep_city": extract(fl, "Departure", "City"),
            "dep_airport": upcode(extract(fl, "Departure", "Airport")),
            "dep_country": extract(fl, "Departure", "Country"),
            "arr_city": extract(fl, "Arrival", "City"),
            "arr_airport": upcode(extract(fl, "Arrival", "Airport")),
            "arr_country": extract(fl, "Arrival", "Country"),
            "nickname": nickname,
            "docs_pairs": docs_pairs,
            "loyalty_pairs": loyalty_pairs,
            "booking_class": "",
            "fare_basis": "",
            "n_docs": str(n_docs),
            "n_loyalty": str(n_loyalty),
        }
        writer.writerow(row)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json")
    ap.add_argument("output_csv")
    ap.add_argument("--source", dest="p_source", default="")
    return ap.parse_args()


def main():
    args = parse_args()
    p_source = args.p_source.strip() or os.path.splitext(os.path.basename(args.input_json))[0]

    with open(args.output_csv, "w", newline="", encoding="utf-8", buffering=1024 * 1024) as fout:
        writer = csv.DictWriter(
            fout, fieldnames=COLUMNS, delimiter=";", lineterminator="\n", quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        with open(args.input_json, "rb") as fin:
            for prof in ijson.items(fin, "Forum Profiles.item"):
                if isinstance(prof, dict):
                    process_profile(prof, writer, p_source)


if __name__ == "__main__":
    main()
