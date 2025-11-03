# -*- coding: utf-8 -*-
import argparse
import itertools
from collections import defaultdict
from typing import List, Tuple, Dict, Set

import pandas as pd

REQUIRED_COLS = [
    "real_first_name","real_last_name","birth_date",
    "flight_date","flight_time","flight_no","codeshare",
    "dep_city","dep_airport","arr_city","arr_airport",
    "e_code","e_ticket","docs","seat","meal",
    "booking_class","fare_basis","baggage","loyalty_pairs",
]
OUTPUT_COLS = REQUIRED_COLS[:]


SYNONYMS = {
    "dep-airport": "dep_airport",
    "dep airport": "dep_airport",
    "dep_air":     "dep_airport",
    "arr-airport": "arr_airport",
    "arr airport": "arr_airport",
    "arr_air":     "arr_airport",
    "flight time": "flight_time",
    "flight date": "flight_date",
    "flight no":   "flight_no",
    "loyalty":     "loyalty_pairs",
    "loyaltypair": "loyalty_pairs",
    "e-ticket":    "e_ticket",
    "e ticket":    "e_ticket",
    "e_code ":     "e_code",
    "fare":        "fare_basis",
}

def clean_header_name(name: str) -> str:
    if name is None:
        return ""
    s = (str(name)
         .replace("\ufeff", "")
         .replace("\xa0", " ")
         .strip())
    s = "_".join(s.lower().replace("-", " ").split())
    if s in SYNONYMS:
        s = SYNONYMS[s]
    return s

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.loc[:, [c for c in df.columns if str(c).strip() != ""]]
    new_cols = [clean_header_name(c) for c in df.columns]
    df.columns = new_cols
    return df


def empty(x: str) -> bool:
    return x is None or (isinstance(x, float) and pd.isna(x)) or (isinstance(x, str) and x.strip() == "")

def norm(x: str) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return str(x).strip()

def eq_wild(a: str, b: str) -> bool:
    a = norm(a); b = norm(b)
    return (a == b) or empty(a) or empty(b)

def parse_loyalty_set(s: str) -> Set[str]:
    s = norm(s)
    if s == "": return set()
    parts = [p.strip() for p in s.split("|") if p.strip() != ""]
    return set(parts)

def loyalty_equal(s1: str, s2: str) -> bool:
    A = parse_loyalty_set(s1); B = parse_loyalty_set(s2)
    if len(A) == 0 or len(B) == 0:
        return True
    return len(A & B) > 0

def loyalty_union(*values: List[str]) -> str:
    uni = set()
    for v in values:
        uni |= parse_loyalty_set(v)
    return "|".join(sorted(uni)) if uni else ""


def passenger_equal(r1: Dict[str, str], r2: Dict[str, str]) -> bool:
    return (
        eq_wild(r1["real_first_name"], r2["real_first_name"]) and
        eq_wild(r1["real_last_name"],  r2["real_last_name"])  and
        eq_wild(r1["birth_date"],      r2["birth_date"])      and
        eq_wild(r1["docs"],            r2["docs"])            and
        eq_wild(r1["e_code"],          r2["e_code"])          and
        eq_wild(r1["e_ticket"],        r2["e_ticket"])        and
        eq_wild(r1["fare_basis"],      r2["fare_basis"])      and
        loyalty_equal(r1["loyalty_pairs"], r2["loyalty_pairs"])
    )

def flight_equal(r1: Dict[str, str], r2: Dict[str, str]) -> bool:
    return (
        eq_wild(r1["flight_date"],   r2["flight_date"])   and
        eq_wild(r1["flight_time"],   r2["flight_time"])   and
        eq_wild(r1["dep_airport"],   r2["dep_airport"])   and
        eq_wild(r1["arr_airport"],   r2["arr_airport"])   and
        eq_wild(r1["flight_no"],     r2["flight_no"])     and
        eq_wild(r1["booking_class"], r2["booking_class"])
    )

def is_duplicate(r1: Dict[str, str], r2: Dict[str, str]) -> bool:
    return passenger_equal(r1, r2) and flight_equal(r1, r2)


class DSU:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n
    def find(self, a: int) -> int:
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a
    def union(self, a: int, b: int):
        ra = self.find(a); rb = self.find(b)
        if ra == rb: return
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[rb] < self.rank[ra]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1


def add_bucket(buckets: Dict[Tuple, List[int]], key_tuple: Tuple, idx: int):
    if any(empty(k) for k in key_tuple):
        return
    buckets[key_tuple].append(idx)

def build_buckets(df: pd.DataFrame) -> Dict[str, Dict[Tuple, List[int]]]:
    B = {
        "B1": defaultdict(list),  # (flight_date, flight_no, dep_airport, arr_airport)
        "B2": defaultdict(list),  # (flight_date, flight_no, booking_class)
        "B3": defaultdict(list),  # (e_ticket,)
        "B4": defaultdict(list),  # (e_code,)
        "B5": defaultdict(list),  # (docs,)
        "B6": defaultdict(list),  # (loyalty_pair,)
    }

    n = len(df)
    for i in range(n):
        add_bucket(B["B1"], (df.at[i,"flight_date"], df.at[i,"flight_no"], df.at[i,"dep_airport"], df.at[i,"arr_airport"]), i)
        add_bucket(B["B2"], (df.at[i,"flight_date"], df.at[i,"flight_no"], df.at[i,"booking_class"]), i)
        add_bucket(B["B3"], (df.at[i,"e_ticket"],), i)
        add_bucket(B["B4"], (df.at[i,"e_code"],), i)
        add_bucket(B["B5"], (df.at[i,"docs"],), i)
        loy = parse_loyalty_set(df.at[i,"loyalty_pairs"])
        for token in loy:
            add_bucket(B["B6"], (token,), i)
    return B

def sorted_neighborhood_pairs(indices: List[int],
                              sort_keys: List[Tuple],
                              window: int) -> List[Tuple[int, int]]:
    combined = sorted(zip(indices, sort_keys), key=lambda x: x[1])
    out_pairs = []
    n = len(combined)
    for i in range(n):
        a = combined[i][0]
        for j in range(i + 1, min(i + 1 + window, n)):
            b = combined[j][0]
            out_pairs.append((min(a, b), max(a, b)))
    return out_pairs

def generate_candidate_pairs(df: pd.DataFrame,
                             buckets: Dict[str, Dict[Tuple, List[int]]],
                             bucket_max: int = 200,
                             window: int = 8) -> Set[Tuple[int, int]]:
    candidates: Set[Tuple[int, int]] = set()

    def sort_key(i: int) -> Tuple:
        return (
            norm(df.at[i,"real_last_name"]),
            norm(df.at[i,"real_first_name"]),
            norm(df.at[i,"birth_date"]),
            norm(df.at[i,"docs"]),
            norm(df.at[i,"e_ticket"]),
            norm(df.at[i,"e_code"]),
            norm(df.at[i,"fare_basis"]),
        )

    for _, bdict in buckets.items():
        for _, idxs in bdict.items():
            if len(idxs) <= 1:
                continue
            if len(idxs) <= bucket_max:
                for a, b in itertools.combinations(sorted(idxs), 2):
                    candidates.add((a, b))
            else:
                keys = [sort_key(i) for i in idxs]
                for a, b in sorted_neighborhood_pairs(idxs, keys, window):
                    candidates.add((a, b))
    return candidates

def pick_first_nonempty(values: List[str]) -> str:
    for v in values:
        if not empty(v):
            return norm(v)
    return ""

def aggregate_cluster(df: pd.DataFrame, indices: List[int]) -> Dict[str, str]:
    out = {}
    idxs = sorted(indices)
    out["loyalty_pairs"] = loyalty_union(*[df.at[i, "loyalty_pairs"] for i in idxs])
    for col in OUTPUT_COLS:
        if col == "loyalty_pairs":
            continue
        vals = [df.at[i, col] for i in idxs]
        out[col] = pick_first_nonempty(vals)
    return out

def read_one_strict(path: str, sep: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False, engine="python", quoting=3)
    df = normalize_columns(df)
    present = set(df.columns)

    missing = [c for c in REQUIRED_COLS if c not in present]
    if len(missing) <= len(REQUIRED_COLS) // 2:
        if missing:
            raise ValueError(f"{path}: missing columns after header normalization: {missing}\n"
                             f"Seen columns: {sorted(present)}")
        return df

    df2 = pd.read_csv(path, sep=None, engine="python", dtype=str, keep_default_na=False, quoting=3)
    df2 = normalize_columns(df2)
    present2 = set(df2.columns)
    missing2 = [c for c in REQUIRED_COLS if c not in present2]
    if missing2:
        raise ValueError(f"{path}: missing columns even after autodetect sep. Missing: {missing2}\n"
                         f"Seen columns: {sorted(present2)}")
    return df2

def main():
    ap = argparse.ArgumentParser(description="Merge flights CSVs into unique trips per passenger by strict rules.")
    ap.add_argument("inputs", nargs="+", help="Input CSV files.")
    ap.add_argument("--output", "-o", required=True, help="Output merged CSV path.")
    ap.add_argument("--sep", default=";", help="Input CSV delimiter (default=';').")
    ap.add_argument("--bucket-max", type=int, default=200, help="Max bucket size before sorted-neighborhood.")
    ap.add_argument("--window", type=int, default=8, help="Neighborhood window size for large buckets.")
    args = ap.parse_args()

    frames = []
    for path in args.inputs:
        df = read_one_strict(path, sep=args.sep)

        df = df.reindex(columns=REQUIRED_COLS)

        try:
            df = df.map(norm)
        except Exception:
            df = df.applymap(norm)

        frames.append(df)

    if not frames:
        raise SystemExit("No input data.")

    df_all = pd.concat(frames, ignore_index=True)
    for c in REQUIRED_COLS:
        df_all[c] = df_all[c].astype(str).map(norm)

    print(f"Loaded rows: {len(df_all)}")

    buckets = build_buckets(df_all)
    candidate_pairs = generate_candidate_pairs(df_all, buckets, bucket_max=args.bucket_max, window=args.window)
    print(f"pairs to check: {len(candidate_pairs)}")

    dsu = DSU(len(df_all))

    def row_dict(i: int) -> Dict[str, str]:
        return {col: df_all.at[i, col] for col in REQUIRED_COLS}

    checked = merged = 0
    for a, b in candidate_pairs:
        checked += 1
        if is_duplicate(row_dict(a), row_dict(b)):
            dsu.union(a, b)
            merged += 1

    print(f"Checked pairs: {checked}, merged pairs: {merged}")

    clusters = defaultdict(list)
    for i in range(len(df_all)):
        clusters[dsu.find(i)].append(i)

    out_rows = []
    for _, idxs in clusters.items():
        agg = aggregate_cluster(df_all, idxs)
        out_rows.append([agg.get(col, "") for col in OUTPUT_COLS])

    df_out = pd.DataFrame(out_rows, columns=OUTPUT_COLS)
    df_out.to_csv(args.output, sep=";", index=False)
    print(f"Output rows: {len(df_out)}")

if __name__ == "__main__":
    main()
