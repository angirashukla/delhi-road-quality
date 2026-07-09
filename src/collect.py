#!/usr/bin/env python3
"""Track 3 (CV) step 1: collect a recent-imagery manifest along the backbone.

Fixes all pilot audit debts:
  - full coverage: one bbox query per backbone segment (no premature stop)
  - recency: start_captured_at >= 2024-01-01 at the API level
  - sequence dedup: per sequence, keep frames >= 50 m apart, cap per segment

Output:
  data/cv_manifest.csv    image_id, lon, lat, captured_at, sequence, segment_id, url
  data/cv_coverage.csv    per-segment: n_raw, n_kept  (0-rows included -> NA handling)
"""
import csv
import math
import pathlib
import time

import requests

ROOT = pathlib.Path.home() / "road_quality"
DATA = ROOT / "data"
TOKEN = (ROOT / ".mapillary_token").read_text().strip()
API = "https://graph.mapillary.com/images"
HEADERS = {"Authorization": f"OAuth {TOKEN}"}
START = "2024-01-01T00:00:00Z"
HALF_LON, HALF_LAT = 0.006, 0.0055   # ~600 m half-window around segment midpoint
MIN_GAP_M = 50.0
CAP_PER_SEGMENT = 8
M_PER_DEG_LAT = 111320.0


def dist_m(lon1, lat1, lon2, lat2):
    kx = M_PER_DEG_LAT * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot((lon2 - lon1) * kx, (lat2 - lat1) * M_PER_DEG_LAT)


segments = []
with open(DATA / "segments_backbone.csv") as f:
    for r in csv.DictReader(f):
        segments.append((r["segment_id"], float(r["mid_lon"]), float(r["mid_lat"])))
print(f"{len(segments)} segments to query")

seen_ids = set()
manifest, coverage = [], []
t0 = time.time()
for i, (sid, mlon, mlat) in enumerate(segments):
    bbox = f"{mlon-HALF_LON:.5f},{mlat-HALF_LAT:.5f},{mlon+HALF_LON:.5f},{mlat+HALF_LAT:.5f}"
    imgs = []
    try:
        r = requests.get(API, headers=HEADERS, timeout=30, params={
            "fields": "id,captured_at,computed_geometry,sequence,thumb_1024_url",
            "bbox": bbox, "start_captured_at": START, "limit": 100})
        if r.status_code == 200:
            imgs = r.json().get("data", [])
    except Exception:
        pass

    # group by sequence, sort by time, keep frames >= MIN_GAP_M apart
    bysec = {}
    for d in imgs:
        if d["id"] in seen_ids:
            continue
        geo = (d.get("computed_geometry") or {}).get("coordinates")
        if not geo:
            continue
        bysec.setdefault(d.get("sequence", "?"), []).append(d)
    kept = []
    for sec, frames in bysec.items():
        frames.sort(key=lambda d: d.get("captured_at") or 0)
        last = None
        for d in frames:
            lon, lat = d["computed_geometry"]["coordinates"]
            if last is None or dist_m(lon, lat, *last) >= MIN_GAP_M:
                kept.append(d)
                last = (lon, lat)
    kept = kept[:CAP_PER_SEGMENT]
    for d in kept:
        seen_ids.add(d["id"])
        lon, lat = d["computed_geometry"]["coordinates"]
        manifest.append({"image_id": d["id"], "lon": round(lon, 6), "lat": round(lat, 6),
                         "captured_at": d.get("captured_at"), "sequence": d.get("sequence", ""),
                         "segment_id": sid, "url": d.get("thumb_1024_url", "")})
    coverage.append({"segment_id": sid, "n_raw": len(imgs), "n_kept": len(kept)})
    if (i + 1) % 250 == 0:
        el = time.time() - t0
        print(f"  {i+1}/{len(segments)} segments, {len(manifest)} images kept, {el:.0f}s elapsed")
    time.sleep(0.12)

with open(DATA / "cv_manifest.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["image_id", "lon", "lat", "captured_at",
                                      "sequence", "segment_id", "url"])
    w.writeheader()
    w.writerows(manifest)
with open(DATA / "cv_coverage.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["segment_id", "n_raw", "n_kept"])
    w.writeheader()
    w.writerows(coverage)

ncov = sum(1 for c in coverage if c["n_kept"] > 0)
print(f"\n=== CV COLLECTION SUMMARY ===")
print(f"images kept: {len(manifest)} | segments with >=1 recent image: {ncov}/{len(segments)} ({100*ncov/len(segments):.0f}%)")
