
#!/usr/bin/env python3
import pandas as pd
import yaml
import hashlib
import unicodedata
import re
import json
from pathlib import Path

# ---------- Helpers ----------
def normalize_name(s):
    if not s:
        return ""
    s = s.strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    s = re.sub(r'\s+', ' ', s)
    return s

def runner_id(full_name):
    return hashlib.sha1(normalize_name(full_name).encode('utf-8')).hexdigest()

def parse_time_to_seconds(x):
    if pd.isna(x) or x is None:
        return None
    s = str(x).strip()
    if not s or s.upper() in {"DNF", "DNS", "DSQ"}:
        return None
    try:
        parts = s.split(":")
        if len(parts) == 3:
            h, m, sec = map(float, parts)
            return int(h * 3600 + m * 60 + sec)
        elif len(parts) == 2:
            m, sec = map(float, parts)
            return int(m * 60 + sec)
        elif len(parts) == 1:
            return int(float(parts[0]))
    except Exception:
        return None
    return None

def detect_csv_params(path: Path):
    encodings = ["utf-8", "cp1252", "latin1"]
    seps = [",", ";", "\t"]
    for enc in encodings:
        for sep in seps:
            try:
                pd.read_csv(path, nrows=1, encoding=enc, sep=sep)
                return enc, sep
            except Exception:
                continue
    return None, None

def detect_format(header_cols):
    hset = {str(c).strip().lower() for c in header_cols}
    if "sortida sant julià de vilatorta" in hset:
        return "F1"
    if "inter 1" in hset or "intermediate 1" in hset:
        return "F2"
    if "nombre" in hset and "apellidos" in hset:
        return "F3"
    return "UNKNOWN"

def load_mapping(fmt):
    with open(Path("configs") / f"mapping_{fmt}.yml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["mapping"]

def get_cell(row: pd.Series, colname: str):
    if not colname:
        return None
    if colname in row.index:
        return row.get(colname)
    low_index = {str(c).lower(): c for c in row.index}
    c2 = low_index.get(str(colname).lower())
    return row.get(c2) if c2 else None

def build_full_name(row: pd.Series, full_name_mapping):
    if isinstance(full_name_mapping, dict) and "combine" in full_name_mapping:
        parts = []
        for col in full_name_mapping["combine"]:
            val = get_cell(row, col)
            if pd.isna(val) or val is None:
                val = ""
            parts.append(str(val).strip())
        return " ".join(p for p in parts if p).strip()
    elif isinstance(full_name_mapping, str):
        val = get_cell(row, full_name_mapping)
        return str(val).strip() if val is not None else ""
    else:
        return ""

def process_file(edition_year: int,csv_path: Path, mapping: dict, encoding: str = None, sep: str = None):
    df = pd.read_csv(csv_path, encoding=encoding, sep=sep)
    out = []
    for _, row in df.iterrows():
        full_name = build_full_name(row, mapping.get("full_name"))
        if not full_name:
            continue
        bib = get_cell(row, mapping.get("bib", ""))
        first_name = get_cell(row, mapping.get("first_name", ""))
        last_name = get_cell(row, mapping.get("last_name", ""))
        gender = None
        gmap = mapping.get("gender")
        if isinstance(gmap, dict) and "from" in gmap:
            raw = get_cell(row, gmap.get("from"))
            raw_s = str(raw).strip() if raw is not None else ""
            gender = gmap.get("map", {}).get(raw_s)
            if gender is None:
                gender = gmap.get("map", {}).get(raw_s.lower())
        club = get_cell(row, mapping.get("club", ""))
        time_raw = get_cell(row, mapping.get("time_net", ""))
        time_net = parse_time_to_seconds(time_raw)
        status = "FINISH" if time_net is not None else None
        if status is None:
            tag = str(time_raw).strip().upper() if time_raw is not None else ""
            if tag in {"DNF", "DNS", "DSQ"}:
                status = tag
            else:
                status = "UNKNOWN"
        sant_raw = get_cell(row, mapping.get("sant_julia", ""))
        sant_julia = parse_time_to_seconds(sant_raw)
        out.append({
            "bib": bib,
            "runner_id": runner_id(full_name),
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "year": edition_year,
            "gender": gender,
            "club": club,
            "status": status,
            "time_net": time_net,
            "sant_julia": sant_julia
        })
    return out

def write_all_years_json(all_participations, out_dir):
    """
    Writes all participations to out/ALL_YEARS.json, sorted by time_net (ascending, None last).
    Each entry includes the year and all runner fields.
    """
    sorted_participations = sorted(
        all_participations,
        key=lambda x: (x["time_net"] is None, x["time_net"] if x["time_net"] is not None else float('inf'))
    )
    out_path = out_dir / "ALL_YEARS.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"results": sorted_participations}, f, ensure_ascii=False, indent=2)
    print(f"[OK] Aggregated {len(sorted_participations)} participations into {out_path}")

# ---------- Main ----------
def main():
    data_dir = Path("data")
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)

    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        print("No s'han trobat CSVs a la carpeta data/.")
        return

    all_participations = []

    for csv_file in csv_files:
        enc, sep = detect_csv_params(csv_file)
        df_head = pd.read_csv(csv_file, nrows=1, encoding=enc, sep=sep)
        header = df_head.columns.tolist()
        fmt = detect_format(header)
        if fmt == "UNKNOWN":
            print(f"[SKIP] Format desconegut per {csv_file.name}. Capçalera: {header}")
            continue
        mapping = load_mapping(fmt)
        m = re.search(r"(?:\(|^|\D)(\d{4})(?:\)|\D|$)", csv_file.name)
        year = int(m.group(1)) if m else None
        results = process_file(year,csv_file, mapping, encoding=enc, sep=sep)
        
        edition = {
            "year": year,
            "name": "Rupit-Taradell",
            "route_id": "rupit-taradell",
            "distance_km": 43,
            "elevation_m": 1400
        }
        out_json = {"edition": edition, "results": results}
        out_path = out_dir / f"{year or csv_file.stem}.json"
        sep_display = sep if sep is not None else ","
        enc_display = enc if enc is not None else "default"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_json, f, ensure_ascii=False, indent=2)
        print(f"[OK] {csv_file.name} → {out_path} (fmt={fmt}, enc={enc_display}, sep='{sep_display}')")
        for r in results:
            entry = dict(r)
            entry["year"] = year
            all_participations.append(entry)

    write_all_years_json(all_participations, out_dir)

if __name__ == "__main__":
    main()
