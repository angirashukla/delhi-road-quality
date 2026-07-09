#!/usr/bin/env python3
"""Phase 3 (v2): fuse per-source tracks onto the segment backbone.

v2 adds: road-name alias consolidation (OSM fragments -> canonical road), and the
road-level agreement analysis folded in (AGREEMENT.md fully regenerated).

Inputs:  data/segments_backbone.csv, source_accidents_segments.csv,
         source_waterlog_segments.csv, source_cv_segments.csv, cv_coverage.csv
Outputs: data/segments.csv   one row per segment, per-source columns + road_canonical
         data/roads.csv      road-level aggregation by canonical name
         outputs/AGREEMENT.md

Conventions: missing source at a segment = empty cell (NA), never 0.
CV: covered segment with zero detections = 0.0 (observed clean); no recent
imagery = NA (unobserved).
"""
import csv
import math
import pathlib
from collections import defaultdict

ROOT = pathlib.Path.home() / "road_quality"
DATA = ROOT / "data"
OUT = ROOT / "outputs"

# OSM name fragments -> canonical road (verified spatially, 2026-07-09:
# "Mahatma Gandhi Road" arc sits at lat 28.66-28.71 = Ring Road north, NOT the
# south-Delhi Mehrauli-Gurgaon MG Road).
ALIASES = {
    "Mahatma Gandhi Marg": "Ring Road",
    "Mahatma Gandhi Road": "Ring Road",
    "Mahatma Gandhi Marg Bridge": "Ring Road",
    "Ring Road": "Ring Road",
    "Outer Ring Road": "Outer Ring Road",
    "Doctor KB Hedgewar Marg": "Outer Ring Road",
    "Outer Ring Road Underpass": "Outer Ring Road",
}


def canonical(name):
    return ALIASES.get(name, name)


def load_keyed(path, key="segment_id"):
    if not pathlib.Path(path).exists():
        return {}
    return {r[key]: r for r in csv.DictReader(open(path))}


backbone = list(csv.DictReader(open(DATA / "segments_backbone.csv")))
acc = load_keyed(DATA / "source_accidents_segments.csv")
wl = load_keyed(DATA / "source_waterlog_segments.csv")
cv = load_keyed(DATA / "source_cv_segments.csv")
cov = load_keyed(DATA / "cv_coverage.csv")

rows = []
for seg in backbone:
    sid = seg["segment_id"]
    a, w_, c = acc.get(sid), wl.get(sid), cv.get(sid)
    covered = int(cov.get(sid, {}).get("n_kept", 0) or 0) > 0
    rows.append({
        "segment_id": sid, "road": seg["road"], "road_canonical": canonical(seg["road"]),
        "highway": seg["highway"], "km": seg["km"],
        "mid_lon": seg["mid_lon"], "mid_lat": seg["mid_lat"],
        "czones": a["czones"] if a else "",
        "crashes_total": a["crashes_total"] if a else "",
        "crashes_fatal": a["crashes_fatal"] if a else "",
        "wl_points": w_["wl_points"] if w_ else "",
        "wl_events": w_["wl_events"] if w_ else "",
        "cv_images": c["cv_images"] if c else ("0" if not covered else ""),
        "cv_detections": c["cv_detections"] if c else "",
        "cv_damage_per_frame": (c["cv_damage_per_frame"] if c else ("0.0" if covered else "")),
        "n_sources": sum([bool(a), bool(w_), covered]),
    })

with open(DATA / "segments.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

# ---- road-level aggregation by canonical name
roads = defaultdict(lambda: {"km": 0.0, "segments": 0, "czones": 0, "crashes_total": 0,
                             "crashes_fatal": 0, "wl_points": 0, "wl_events": 0,
                             "cv_images": 0, "cv_detections": 0, "cv_covered_segs": 0})
for r in rows:
    g = roads[r["road_canonical"]]
    g["km"] += float(r["km"]); g["segments"] += 1
    for k in ("czones", "crashes_total", "crashes_fatal", "wl_points", "wl_events",
              "cv_images", "cv_detections"):
        g[k] += int(r[k]) if r[k] not in ("", None) else 0
    if r["cv_images"] not in ("", "0"):
        g["cv_covered_segs"] += 1
road_rows = []
for name, g in sorted(roads.items(), key=lambda kv: -kv[1]["crashes_fatal"]):
    road_rows.append({"road": name, "km": round(g["km"], 1), "segments": g["segments"],
                      "czones": g["czones"], "crashes_total": g["crashes_total"],
                      "crashes_fatal": g["crashes_fatal"],
                      "crashes_per_km": round(g["crashes_total"] / g["km"], 2) if g["km"] else "",
                      "wl_points": g["wl_points"], "wl_events": g["wl_events"],
                      "cv_covered_segs": g["cv_covered_segs"], "cv_images": g["cv_images"],
                      "cv_detections": g["cv_detections"],
                      "cv_damage_per_frame": round(g["cv_detections"] / g["cv_images"], 4) if g["cv_images"] else ""})
with open(DATA / "roads.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(road_rows[0].keys()))
    w.writeheader()
    w.writerows(road_rows)


# ---- agreement
def spearman(pairs):
    if len(pairs) < 5:
        return None
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                rk[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return rk
    xs, ys = ranks([p[0] for p in pairs]), ranks([p[1] for p in pairs])
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx and dy else None


def fnum(r, k):
    return float(r[k]) if r[k] not in ("", None) else None


lines = ["# Cross-source agreement\n",
         "Sources measure different failure modes over different subsets; sparse",
         "overlap is expected. Segment-level correlations are attenuated by geocode/",
         "snap noise (points near segment boundaries land on neighbors) and small n —",
         "read the road level as the primary signal.\n",
         "## Segment level\n",
         "| pair | n overlap | spearman |", "|---|---|---|"]
seg_metrics = {"crashes_total": lambda r: fnum(r, "crashes_total"),
               "wl_events": lambda r: fnum(r, "wl_events"),
               "cv_damage_per_frame": lambda r: fnum(r, "cv_damage_per_frame")}
names = list(seg_metrics)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        pairs = [(x, y) for x, y in ((seg_metrics[names[i]](r), seg_metrics[names[j]](r))
                                     for r in rows) if x is not None and y is not None]
        rho = spearman(pairs)
        lines.append(f"| {names[i]} vs {names[j]} | {len(pairs)} | "
                     + (f"{rho:.3f} |" if rho is not None else "NA |"))

lines += ["\n## Road level (canonical roads >= 3 km, named)\n",
          "| pair | n roads | spearman |", "|---|---|---|"]
rds = [r for r in road_rows if float(r["km"]) >= 3 and r["road"] != "unnamed"]
road_metrics = {
    "crashes_per_km": lambda r: fnum(r, "crashes_per_km"),
    "wl_per_km": lambda r: (float(r["wl_events"]) / float(r["km"])) if r["wl_events"] not in ("", None) else None,
    "cv_damage_per_frame": lambda r: fnum(r, "cv_damage_per_frame"),
}
rnames = list(road_metrics)
for i in range(len(rnames)):
    for j in range(i + 1, len(rnames)):
        pairs = [(x, y) for x, y in ((road_metrics[rnames[i]](r), road_metrics[rnames[j]](r))
                                     for r in rds) if x is not None and y is not None]
        rho = spearman(pairs)
        lines.append(f"| {rnames[i]} vs {rnames[j]} | {len(pairs)} | "
                     + (f"{rho:.3f} |" if rho is not None else "NA |"))
(OUT / "AGREEMENT.md").write_text("\n".join(lines) + "\n")

n2 = sum(1 for r in rows if int(r["n_sources"]) >= 2)
print("=== FUSION SUMMARY (v2, aliased) ===")
print(f"segments: {len(rows)} | >=1 source: {sum(1 for r in rows if int(r['n_sources'])>=1)} | >=2: {n2}")
print(f"canonical roads: {len(road_rows)}")
print("top canonical roads by fatal crashes:")
for rr in road_rows[:8]:
    print(f"  {rr['road']:<24} km={rr['km']:>6} fatal={rr['crashes_fatal']:>3} total={rr['crashes_total']:>4} "
          f"wl_ev={rr['wl_events']:>3} cv_dpf={rr['cv_damage_per_frame']}")
