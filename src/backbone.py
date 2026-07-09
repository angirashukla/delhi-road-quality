#!/usr/bin/env python3
"""Phase 1: segment backbone for Delhi NCT arterials.

Pulls motorway/trunk/primary ways from OSM Overpass, cuts each way's polyline
into ~1 km segments with stable IDs, writes:
  data/arterials.geojson          raw ways (name, ref, highway class)
  data/segments_backbone.geojson  ~1 km segments keyed by segment_id
  data/segments_backbone.csv      flat table (segment_id, road, way_id, km, midpoint)

Segment IDs are stable as long as OSM way ids are: <roadslug>_<wayid>_<part>.
Dual carriageways appear as separate ways (both directions) — documented, not merged.
"""
import csv
import json
import math
import pathlib
import re
import time

import requests

ROOT = pathlib.Path.home() / "road_quality"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY = """
[out:json][timeout:180];
area["ISO3166-2"="IN-DL"][admin_level=4]->.delhi;
way(area.delhi)["highway"~"^(motorway|trunk|primary)$"];
out tags geom;
"""

SEG_KM = 1.0
M_PER_DEG_LAT = 111320.0


def dist_m(lon1, lat1, lon2, lat2):
    """Equirectangular approx — fine at city scale for segment cutting."""
    kx = M_PER_DEG_LAT * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot((lon2 - lon1) * kx, (lat2 - lat1) * M_PER_DEG_LAT)


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "unnamed").lower()).strip("-")
    return s[:40] or "unnamed"


def cut_way(coords, seg_len_m):
    """Split a polyline (list of (lon, lat)) into pieces of ~seg_len_m."""
    pieces, cur, acc = [], [coords[0]], 0.0
    for a, b in zip(coords, coords[1:]):
        d = dist_m(*a, *b)
        acc += d
        cur.append(b)
        if acc >= seg_len_m:
            pieces.append((cur, acc))
            cur, acc = [b], 0.0
    if len(cur) > 1:
        pieces.append((cur, acc))
    return pieces


def main():
    print("querying Overpass for Delhi arterials...")
    for attempt in range(3):
        try:
            r = requests.post(OVERPASS, data={"data": QUERY}, timeout=240,
                              headers={"User-Agent": "delhi-road-quality-research/0.1 (angiras@uchicago.edu)"})
            r.raise_for_status()
            ways = r.json()["elements"]
            break
        except Exception as e:
            print(f"  attempt {attempt + 1} failed: {e}; retrying in 20s")
            time.sleep(20)
    else:
        raise SystemExit("Overpass failed 3x — try again later or switch mirror")
    print(f"  {len(ways)} ways")

    arterial_features, seg_features, rows = [], [], []
    total_km = 0.0
    for w in ways:
        tags = w.get("tags", {})
        name = tags.get("name") or tags.get("ref") or "unnamed"
        geom = [(g["lon"], g["lat"]) for g in w.get("geometry", [])]
        if len(geom) < 2:
            continue
        arterial_features.append({
            "type": "Feature",
            "properties": {"way_id": w["id"], "name": name,
                           "ref": tags.get("ref", ""), "highway": tags["highway"]},
            "geometry": {"type": "LineString", "coordinates": geom},
        })
        slug = slugify(name)
        for i, (piece, length_m) in enumerate(cut_way(geom, SEG_KM * 1000)):
            sid = f"{slug}_{w['id']}_{i}"
            km = round(length_m / 1000, 3)
            total_km += km
            mid = piece[len(piece) // 2]
            seg_features.append({
                "type": "Feature",
                "properties": {"segment_id": sid, "road": name, "way_id": w["id"],
                               "highway": tags["highway"], "km": km},
                "geometry": {"type": "LineString", "coordinates": piece},
            })
            rows.append({"segment_id": sid, "road": name, "way_id": w["id"],
                         "highway": tags["highway"], "km": km,
                         "mid_lon": round(mid[0], 6), "mid_lat": round(mid[1], 6)})

    (DATA / "arterials.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": arterial_features}))
    (DATA / "segments_backbone.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": seg_features}))
    with open(DATA / "segments_backbone.csv", "w", newline="") as f:
        wcsv = csv.DictWriter(f, fieldnames=["segment_id", "road", "way_id",
                                             "highway", "km", "mid_lon", "mid_lat"])
        wcsv.writeheader()
        wcsv.writerows(rows)

    roads = {}
    for row in rows:
        roads[row["road"]] = roads.get(row["road"], 0) + row["km"]
    top = sorted(roads.items(), key=lambda kv: -kv[1])[:12]
    print(f"\n=== BACKBONE SUMMARY ===")
    print(f"ways: {len(arterial_features)} | segments: {len(rows)} | total: {total_km:.0f} km (incl. dual carriageways)")
    print("top roads by km:")
    for name, km in top:
        print(f"  {name:<40} {km:7.1f} km")


if __name__ == "__main__":
    main()
