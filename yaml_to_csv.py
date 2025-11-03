import argparse
import csv
import os
import re

import yaml

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


def upcode(s: str) -> str:
    return (s or "").strip().upper()


def clean_number(s: str) -> str:
    return ALNUM_RE.sub("", (s or ""))


def yaml_iter(yaml_root: dict):
    if not isinstance(yaml_root, dict):
        return
    for date_key, flights in yaml_root.items():
        if not isinstance(flights, dict):
            continue
        flight_date = str(date_key)
        for flight_no, payload in flights.items():
            if not isinstance(payload, dict):
                continue
            flight_no_str = upcode(str(flight_no))
            dep_airport = upcode(str(payload.get("FROM", "")))
            arr_airport = upcode(str(payload.get("TO", "")))
            ff = payload.get("FF") or {}
            yield flight_date, flight_no_str, dep_airport, arr_airport, ff


def rows_from_yaml(input_path: str, p_source: str):
    with open(input_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for flight_date, flight_no, dep_airport, arr_airport, ff in yaml_iter(data):
        if isinstance(ff, dict) and ff:
            for key, meta in ff.items():
                key_str = str(key)
                parts = key_str.split(None, 1)
                prog = upcode(parts[0]) if parts else ""
                number = clean_number(parts[1]) if len(parts) > 1 else ""

                booking_class = ""
                fare_basis = ""
                if isinstance(meta, dict):
                    booking_class = str(meta.get("CLASS", "")).strip()
                    fare_basis = str(meta.get("FARE", "")).strip()

                loyalty_pairs = f"{prog}::{number}"

                yield {
                    "real_first_name": "",
                    "real_last_name": "",
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
                    "booking_class": booking_class,
                    "fare_basis": fare_basis,
                    "n_docs": "0",
                    "n_loyalty": "1",
                }
        else:
            continue


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_yaml", )
    ap.add_argument("output_csv")
    ap.add_argument("--source", dest="p_source", default="")
    return ap.parse_args()


def main():
    args = parse_args()
    p_source = args.p_source.strip() or os.path.splitext(os.path.basename(args.input_yaml))[0]

    with open(args.output_csv, "w", newline="", encoding="utf-8", buffering=1024 * 1024) as fout:
        writer = csv.DictWriter(
            fout, fieldnames=COLUMNS, delimiter=";", lineterminator="\n", quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        for row in rows_from_yaml(args.input_yaml, p_source):
            writer.writerow(row)


if __name__ == "__main__":
    main()
