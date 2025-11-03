import csv
import os
import sys

TARGET_COLUMNS = [
    "real_first_name", "real_last_name", "birth_date",
    "flight_date", "flight_time", "flight_no", "codeshare",
    "dep_city", "dep_airport", "arr_city", "arr_airport",
    "e_code", "e_ticket", "docs", "seat", "meal",
    "booking_class", "fare_basis", "baggage", "loyalty_pairs",
]

OUTPUT_DELIMITER = ";"


def detect_delimiter(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        line = f.readline()
        return ";" if line.count(";") >= line.count(",") else ","


def normalize_header(name: str) -> str:
    return " ".join(name.strip().split())


def read_csv(path):
    delimiter = detect_delimiter(path)
    with open(path, "r", encoding="utf-8-sig", newline="", errors="replace") as f:
        reader = csv.reader(f, delimiter=delimiter)
        try:
            raw_header = next(reader)
        except StopIteration:
            return [], []

        header = [normalize_header(h) for h in raw_header]
        rows = []
        for r in reader:
            if len(r) < len(header):
                r += [""] * (len(header) - len(r))
            elif len(r) > len(header):
                r = r[:len(header)]
            row_dict = {h: (r[i].strip() if i < len(r) else "") for i, h in enumerate(header)}
            rows.append(row_dict)
        return header, rows


def transform_to_target(header, rows):
    name_map = {}
    lower_header = {h.lower(): h for h in header}
    for col in TARGET_COLUMNS:
        name_map[col] = lower_header.get(col.lower())

    out_rows = []
    for row in rows:
        new_row = {col: row.get(name_map[col], "") if name_map[col] else "" for col in TARGET_COLUMNS}
        out_rows.append(new_row)
    return out_rows


def write_csv(path_out, rows):
    with open(path_out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TARGET_COLUMNS, delimiter=OUTPUT_DELIMITER)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    if len(sys.argv) != 2:
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.isfile(input_path):
        sys.exit(1)

    header, rows = read_csv(input_path)

    if not header:
        output_path = os.path.splitext(input_path)[0] + "_cutted_fields.csv"
        write_csv(output_path, [])
        return

    out_rows = transform_to_target(header, rows)
    output_path = os.path.splitext(input_path)[0] + "_cutted_fields.csv"
    write_csv(output_path, out_rows)


if __name__ == "__main__":
    main()
