import csv
import os
import sys
from datetime import datetime

TARGET_COLUMNS = [
    "real_first_name", "real_last_name", "birth_date",
    "flight_date", "flight_time", "flight_no", "codeshare",
    "dep_city", "dep_airport", "arr_city", "arr_airport",
    "e_code", "e_ticket", "docs", "seat", "meal",
    "booking_class", "fare_basis", "baggage", "loyalty_pairs",
]

SOURCE_TO_TARGET = {
    "PassengerFirstName": "real_first_name",
    "PassengerLastName": "real_last_name",
    "PassengerBirthDate": "birth_date",
    "FlightDate": "flight_date",
    "FlightTime": "flight_time",
    "FlightNumber": "flight_no",
    "CodeShare": "codeshare",
    "Destination": "arr_city",
    "BookingCode": "e_code",
    "TicketNumber": "e_ticket",
    "PassengerDocument": "docs",
    "Baggage": "baggage",
}

OUTPUT_DELIMITER = ";"


def normalize_header(name: str) -> str:
    return " ".join(name.strip().split())


def parse_date(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    fmts = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y"]
    for fmt in fmts:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return value


def parse_time(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    fmts = ["%H:%M", "%H:%M:%S"]
    for fmt in fmts:
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            pass
    return value


def detect_delimiter(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        head = f.readline()
    return ";" if head.count(";") >= head.count(",") else ","


def main():
    if len(sys.argv) != 2:
        sys.exit(1)

    in_path = sys.argv[1]
    if not os.path.isfile(in_path):
        sys.exit(1)

    out_path = os.path.splitext(in_path)[0] + "_normalized.csv"
    delimiter = detect_delimiter(in_path)

    with open(in_path, "r", encoding="utf-8-sig", newline="", errors="replace") as fin, \
            open(out_path, "w", encoding="utf-8", newline="") as fout:

        reader = csv.reader(fin, delimiter=delimiter)
        writer = csv.DictWriter(fout, fieldnames=TARGET_COLUMNS, delimiter=OUTPUT_DELIMITER)
        writer.writeheader()

        try:
            raw_header = next(reader)
        except StopIteration:
            return

        src_header = [normalize_header(h) for h in raw_header]
        idx_by_name = {name: i for i, name in enumerate(src_header)}

        for row in reader:
            if len(row) < len(src_header):
                row = row + [""] * (len(src_header) - len(row))
            elif len(row) > len(src_header):
                row = row[:len(src_header)]

            src_vals = {col: row[idx_by_name[col]].strip() if idx_by_name[col] < len(row) else ""
                        for col in src_header}

            out = {col: "" for col in TARGET_COLUMNS}

            for src_col, tgt_col in SOURCE_TO_TARGET.items():
                if src_col in src_vals:
                    out[tgt_col] = src_vals.get(src_col, "")

            out["birth_date"] = parse_date(out.get("birth_date", ""))
            out["flight_date"] = parse_date(out.get("flight_date", ""))
            out["flight_time"] = parse_time(out.get("flight_time", ""))

            writer.writerow(out)


if __name__ == "__main__":
    main()
