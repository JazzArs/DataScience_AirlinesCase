import csv
import sys
import os

def read_iata_list(path: str):
    items = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip().upper()
            if len(s) == 3 and s.isalpha():
                items.append(s)
    return sorted(set(items))

def parse_openflights_airports(dat_path: str):
    mapping = {}
    with open(dat_path, "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        for row in r:
            if not row or len(row) < 12:
                continue
            iata = (row[4] or "").strip().upper()
            tz = (row[11] or "").strip()
            typ = (row[12] or "").strip().lower() if len(row) > 12 else ""
            if iata and len(iata) == 3 and iata.isalpha() and tz and "airport" in typ:
                mapping[iata] = tz
    return mapping

def main():
    if len(sys.argv) != 3 and len(sys.argv) != 4:
        sys.exit(1)

    iata_list_path, source_path, out_map_path = sys.argv[1], sys.argv[2], sys.argv[3]

    if not os.path.isfile(iata_list_path):
        sys.exit(1)
    if not os.path.isfile(source_path):
        sys.exit(1)

    want = read_iata_list(iata_list_path)
    if not want:
        sys.exit(1)

    iata2tz = parse_openflights_airports(source_path)

    found, missing = [], []
    for code in want:
        tz = iata2tz.get(code)
        if tz:
            found.append((code, tz))
        else:
            missing.append(code)

    with open(out_map_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["iata", "tz"])
        for code, tz in sorted(found):
            w.writerow([code, tz])

if __name__ == "__main__":
    main()
