import csv
import os
import re
import sys
from datetime import datetime

COLUMNS = [
    "real_first_name", "real_last_name", "birth_date",
    "flight_date", "flight_time", "flight_no", "codeshare",
    "dep_city", "dep_airport", "arr_city", "arr_airport",
    "e_code", "e_ticket", "docs", "seat", "meal",
    "booking_class", "fare_basis", "baggage", "loyalty_pairs",
]

DELIM = ";"

def normalize_spaces_upper(s: str) -> str:
    if not s:
        return ""
    s = " ".join(s.strip().split())
    return s.upper()


def normalize_date(s: str) -> str:
    if not s or not s.strip():
        return ""
    s = s.strip()
    fmts = [
        "%Y-%m-%d",  # 2017-03-22
        "%d/%m/%Y",  # 22/03/2017
        "%m/%d/%Y",  # 03/22/2017
        "%d.%m.%Y",  # 22.03.2017
        "%Y/%m/%d",  # 2017/03/22
        "%d-%m-%Y",  # 22-03-2017
        "%m-%d-%Y",  # 03-22-2017
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s


def normalize_time(s: str) -> str:
    if not s or not s.strip():
        return ""
    s = s.strip()
    fmts = ["%H:%M", "%H:%M:%S"]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).strftime("%H:%M")
        except ValueError:
            continue
    m = re.fullmatch(r"\s*(\d{1,2})(\d{2})\s*", s)
    if m:
        hh = int(m.group(1))
        mm = int(m.group(2))
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return f"{hh:02d}:{mm:02d}"
    return s


def normalize_flight_no(s: str) -> str:
    if not s or not s.strip():
        return ""
    s = s.strip().upper()
    m = re.search(r"([A-Z]{2,3})\s*[-\s_]*\s*(\d+)", s)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    return re.sub(r"\s+", "", s)


def normalize_codeshare(s: str) -> str:
    if s is None:
        return "0"
    v = s.strip().lower()
    if v == "":
        return "0"
    if v in {"own", "0", "no", "none"}:
        return "0"
    if v in {"operated", "1", "yes"}:
        return "1"
    return "0"


def normalize_city(s: str) -> str:
    return normalize_spaces_upper(s)


def normalize_airport(s: str) -> str:
    if not s or not s.strip():
        return ""
    v = s.strip().upper()
    return v if re.fullmatch(r"[A-Z]{3}", v) else ""


def normalize_e_code(s: str) -> str:
    if not s or not s.strip():
        return ""
    v = re.sub(r"[^0-9A-Za-z]", "", s).upper()
    return v if len(v) == 6 else ""


def normalize_e_ticket(s: str) -> str:
    if not s:
        return ""
    digits = re.sub(r"\D", "", s)
    return digits if 13 <= len(digits) <= 16 else ""


def normalize_docs(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", "", s)


def normalize_seat(s: str) -> str:
    if not s or not s.strip():
        return ""
    v = s.strip()
    if v.upper() in {"N/A", "NA", "-", "NONE"}:
        return ""
    return v


def normalize_meal(s: str) -> str:
    if not s:
        return ""
    return s.strip().upper()


def normalize_booking_class(s: str) -> str:
    if not s:
        return ""
    v = s.strip().upper().replace(" ", "")
    if re.fullmatch(r"[A-Z]", v):
        return v
    m = re.search(r"[A-Z]", v)
    return m.group(0) if m else ""


def normalize_fare_basis(s: str) -> str:
    if not s:
        return ""
    v = " ".join(s.strip().split()).upper()
    return v


def normalize_baggage(s: str) -> str:
    if not s:
        return ""
    return s.strip().upper()


def identity_keep(s: str) -> str:
    return s if s is not None else ""


NORMALIZERS = {
    "real_first_name": normalize_spaces_upper,
    "real_last_name": normalize_spaces_upper,
    "birth_date": normalize_date,
    "flight_date": normalize_date,
    "flight_time": normalize_time,
    "flight_no": normalize_flight_no,
    "codeshare": normalize_codeshare,
    "dep_city": normalize_city,
    "dep_airport": normalize_airport,
    "arr_city": normalize_city,
    "arr_airport": normalize_airport,
    "e_code": normalize_e_code,
    "e_ticket": normalize_e_ticket,
    "docs": normalize_docs,
    "seat": normalize_seat,
    "meal": normalize_meal,
    "booking_class": normalize_booking_class,
    "fare_basis": normalize_fare_basis,
    "baggage": normalize_baggage,
    "loyalty_pairs": identity_keep,
}


def main():
    in_path = sys.argv[1]
    if not os.path.isfile(in_path):
        sys.exit(1)

    out_path = os.path.splitext(in_path)[0] + "_normalized.csv"

    with open(in_path, "r", encoding="utf-8-sig", newline="") as fin, \
            open(out_path, "w", encoding="utf-8", newline="") as fout:

        reader = csv.DictReader(fin, delimiter=DELIM)
        missing = [c for c in COLUMNS if c not in reader.fieldnames]
        if missing:
            for c in missing:
                print(f"  - {c}")

        writer = csv.DictWriter(fout, fieldnames=COLUMNS, delimiter=DELIM)
        writer.writeheader()

        for row in reader:
            out_row = {}
            for col in COLUMNS:
                raw_val = row.get(col, "")
                norm_func = NORMALIZERS[col]
                out_row[col] = norm_func(raw_val)
            writer.writerow(out_row)


if __name__ == "__main__":
    main()
