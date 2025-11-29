#!/usr/bin/env python3
import json
from pathlib import Path

OUT_DIR = Path("out")
LEADERS_DIR = OUT_DIR / "leaders"
PARTICIPANTS_DIR = OUT_DIR / "participants"
LEADERS_DIR.mkdir(exist_ok=True, parents=True)
PARTICIPANTS_DIR.mkdir(exist_ok=True, parents=True)

# Collect all results from yearly JSONs
all_rows = []
for jf in OUT_DIR.glob("*.json"):
    with open(jf, "r", encoding="utf-8") as f:
        data = json.load(f)
    edition = data.get("edition", {})
    year = edition.get("year")
    for r in data.get("results", []):
        # Only consider rows with net time for leaderboards
        time_net = r.get("time_net")
        if time_net is None:
            continue
        all_rows.append({
            "year": year,
            "bib": r.get("bib"),
            "runner_id": r.get("runner_id"),
            "full_name": r.get("full_name"),
            "gender": r.get("gender"),
            "club": r.get("club"),
            "time_net": time_net,
            "sant_julia": r.get("sant_julia"),
            "status": r.get("status"),
        })

# Helper to sort and format entries

def fmt_entry(e):
    return {
        "year": e["year"],
        "runner_id": e["runner_id"],
        "full_name": e["full_name"],
        "gender": e.get("gender"),
        "club": e.get("club"),
        "time_net": e["time_net"],
        "sant_julia": e.get("sant_julia")
    }

# Compute overall FKTs (top fastest 10) and SKTs (slowest 10 with a finish time)
finished = [e for e in all_rows if e.get("status") == "FINISH" and isinstance(e.get("time_net"), int)]
fastest_10 = sorted(finished, key=lambda x: x["time_net"])[:10]
slowest_10 = sorted(finished, key=lambda x: x["time_net"], reverse=True)[:10]

leaders = {
    "overall": {
        "FKT_top10": [fmt_entry(e) for e in fastest_10],
        "SKT_top10": [fmt_entry(e) for e in slowest_10]
    },
    "by_gender": {}
}

# By gender leaderboards
for g in ["M", "F", None]:
    subset = [e for e in finished if e.get("gender") == g]
    if not subset:
        continue
    leaders["by_gender"][g or "unknown"] = {
        "FKT_top10": [fmt_entry(e) for e in sorted(subset, key=lambda x: x["time_net"])[:10]],
        "SKT_top10": [fmt_entry(e) for e in sorted(subset, key=lambda x: x["time_net"], reverse=True)[:10]],
    }

# Save leaderboards JSON
with open(LEADERS_DIR / "leaders_fkt_skt.json", "w", encoding="utf-8") as f:
    json.dump(leaders, f, ensure_ascii=False, indent=2)

# Participant histories: one JSON per runner_id with all their participations
by_runner = {}
for e in all_rows:
    rid = e.get("runner_id")
    if not rid:
        rid = "unknown"
    by_runner.setdefault(rid, {"runner_id": rid, "full_name": e.get("full_name"), "entries": []})
    by_runner[rid]["entries"].append({
        "year": e.get("year"),
        "time_net": e.get("time_net"),
        "sant_julia": e.get("sant_julia"),
        "status": e.get("status"),
        "club": e.get("club"),
        "gender": e.get("gender"),
    })

# Sort each runner's entries by year ascending
for rid, rec in by_runner.items():
    rec["entries"].sort(key=lambda x: (x.get("year") or 0))
    with open(PARTICIPANTS_DIR / f"{rid}.json", "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)

# Index of participants (basic)
index = [{"runner_id": rid, "full_name": rec.get("full_name"), "count": len(rec.get("entries", []))} for rid, rec in by_runner.items()]
with open(PARTICIPANTS_DIR / "index.json", "w", encoding="utf-8") as f:
    json.dump(sorted(index, key=lambda x: x["full_name"] or ""), f, ensure_ascii=False, indent=2)

print("Leaderboards → out/leaders/leaders_fkt_skt.json")
print("Participants → out/participants/index.json i out/participants/<runner_id>.json")
