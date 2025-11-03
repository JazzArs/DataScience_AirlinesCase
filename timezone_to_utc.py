import csv
import os
import re
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

COLUMNS = [
    "real_first_name", "real_last_name", "birth_date",
    "flight_date", "flight_time", "flight_no", "codeshare",
    "dep_city", "dep_airport", "arr_city", "arr_airport",
    "e_code", "e_ticket", "docs", "seat", "meal",
    "booking_class", "fare_basis", "baggage", "loyalty_pairs",
]

INPUT_DELIM = ";"
OUTPUT_DELIM = ";"


def normalize_header(name: str) -> str:
    return " ".join(name.strip().split())


def normalize_date(s: str) -> str:
    if not s or not s.strip():
        return ""
    v = s.strip()
    fmts = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y")
    for fmt in fmts:
        try:
            return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return v


def normalize_time(s: str) -> str:
    if not s or not s.strip():
        return ""
    v = s.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(v, fmt).strftime("%H:%M")
        except ValueError:
            pass
    m = re.fullmatch(r"\s*(\d{1,2})(\d{2})\s*", v)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return f"{hh:02d}:{mm:02d}"
    return v


def to_utc(date_s: str, time_s: str, tz_name: str):
    """Вернёт (YYYY-MM-DD, HH:MM) в UTC или None, если не удалось."""
    ds = normalize_date(date_s)
    ts = normalize_time(time_s)
    if not ds or not ts or not tz_name:
        return None
    try:
        local_naive = datetime.strptime(ds + " " + ts, "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    try:
        local_aware = local_naive.replace(tzinfo=ZoneInfo(tz_name))
    except Exception:
        return None
    utc_dt = local_aware.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%d"), utc_dt.strftime("%H:%M")


def load_iata_tz_map(path: str) -> dict:
    """Ожидаем файл с заголовком 'iata;tz' или 'iata,tz'."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        head = f.readline()
        if not head:
            return {}
        delim = ";" if head.count(";") >= head.count(",") else ","
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delim)
        cols = [c.strip().lower() for c in (reader.fieldnames or [])]
        if "iata" not in cols or "tz" not in cols:
            f.seek(0)
            mapping = {}
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                if i == 0 and any(x in line.lower() for x in ("iata", "tz")):
                    continue
                parts = [p.strip() for p in line.split(delim)]
                if len(parts) >= 2:
                    iata, tz = parts[0].upper(), parts[1]
                    if len(iata) == 3 and iata.isalpha() and tz:
                        mapping[iata] = tz
            return mapping
        mapping = {}
        for row in reader:
            iata = (row.get("iata") or row.get("IATA") or "").strip().upper()
            tz = (row.get("tz") or row.get("TZ") or "").strip()
            if len(iata) == 3 and iata.isalpha() and tz:
                mapping[iata] = tz
        return mapping


def main():
    if len(sys.argv) != 3 and len(sys.argv) != 4:
        sys.exit(1)

    in_csv = sys.argv[1]
    tz_map_csv = sys.argv[2]
    out_csv = sys.argv[3] if len(sys.argv) == 4 else os.path.splitext(in_csv)[0] + "_utc.csv"

    if not os.path.isfile(in_csv):
        sys.exit(1)
    if not os.path.isfile(tz_map_csv):
        sys.exit(1)

    iata2tz = load_iata_tz_map(tz_map_csv)

    with open(in_csv, "r", encoding="utf-8-sig", newline="", errors="replace") as fin:
        reader = csv.reader(fin, delimiter=INPUT_DELIM, skipinitialspace=True)
        try:
            raw_header = next(reader)
        except StopIteration:
            with open(out_csv, "w", encoding="utf-8", newline="") as fout:
                writer = csv.writer(fout, delimiter=OUTPUT_DELIM)
                writer.writerow(COLUMNS)
            return

        header = [normalize_header(h) for h in raw_header]

        rows = []
        for r in reader:
            if len(r) < len(header):
                r = r + [""] * (len(header) - len(r))
            elif len(r) > len(header):
                r = r[:len(header)]
            row = {}
            for i, h in enumerate(header):
                v = r[i]
                row[h] = v.strip() if isinstance(v, str) else v
            rows.append(row)

    updated = 0
    skipped = 0
    for row in rows:
        dep = (row.get("dep_airport") or "").strip().upper()
        tz_name = iata2tz.get(dep, "")
        fd = row.get("flight_date", "")
        ft = row.get("flight_time", "")
        converted = to_utc(fd, ft, tz_name)
        if converted is None:
            skipped += 1
            continue
        new_d, new_t = converted
        row["flight_date"] = new_d
        row["flight_time"] = new_t
        updated += 1

    extra = [c for c in header if c not in COLUMNS]
    out_fields = COLUMNS + extra

    with open(out_csv, "w", encoding="utf-8", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=out_fields, delimiter=OUTPUT_DELIM)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    main()
