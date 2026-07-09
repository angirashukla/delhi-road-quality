#!/usr/bin/env python3
"""Track 1+2 (v2): geocode crash zones and waterlogging locations, snap to
backbone segments, write per-segment source metrics.

v2 fixes: Photon (fuzzy, Delhi-biased) as primary geocoder; cleaned query
variants; Nominatim fallback; network errors are NOT cached as misses.

Outputs:
  data/geocode_cache.json
  data/source_accidents_segments.csv   segment_id, czones, crashes_total, crashes_fatal
  data/source_waterlog_segments.csv    segment_id, wl_points, wl_events
  data/geocode_misses.csv              source, name, reason
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
CACHE = DATA / "geocode_cache.json"
PHOTON = "https://photon.komoot.io/api/"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
UA = {"User-Agent": "delhi-road-quality-research/0.1 (angiras@uchicago.edu)"}
# Delhi bbox: minlon, minlat, maxlon, maxlat
BBOX = (76.84, 28.40, 77.35, 28.90)
SNAP_MAX_M = 1500.0
M_PER_DEG_LAT = 111320.0

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}


def in_bbox(lon, lat):
    return BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]


def photon(q):
    r = requests.get(PHOTON, params={"q": q, "limit": 3, "lat": 28.65, "lon": 77.2},
                     headers=UA, timeout=30)
    r.raise_for_status()
    for f in r.json().get("features", []):
        lon, lat = f["geometry"]["coordinates"]
        if in_bbox(lon, lat):
            return [lon, lat]
    return None


def nominatim(q):
    r = requests.get(NOMINATIM, params={"q": q, "format": "json", "limit": 3},
                     headers=UA, timeout=30)
    r.raise_for_status()
    for h in r.json():
        lon, lat = float(h["lon"]), float(h["lat"])
        if in_bbox(lon, lat):
            return [lon, lat]
    return None


def geocode(q):
    key = f"v2:{q}"
    if key in cache:
        return cache[key]
    res = None
    for fn, pause in ((photon, 0.6), (nominatim, 1.1)):
        try:
            res = fn(q)
            time.sleep(pause)
        except Exception:
            time.sleep(2)
            return None          # network error: do NOT cache
        if res:
            break
    cache[key] = res             # cache real answers, incl. genuine empties
    return res


def clean_location(s):
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"^(near|opp\.?|opposite|both carriageway|in front of|at)\s+", "", s, flags=re.I)
    s = re.sub(r"\s+towards\s+.*$", "", s, flags=re.I)
    s = re.sub(r"^metro station\s+(.*)$", r"\1 metro station", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip(" ,")


def variants(name, road):
    n = clean_location(name)
    out = [f"{n}, Delhi", f"{n} {road}, Delhi"]
    # last resort: strongest two tokens of the name
    toks = [t for t in re.split(r"[^A-Za-z0-9]+", n) if len(t) > 3]
    if len(toks) >= 2:
        out.append(f"{' '.join(toks[:2])}, Delhi")
    return out


def dist_m(lon1, lat1, lon2, lat2):
    kx = M_PER_DEG_LAT * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot((lon2 - lon1) * kx, (lat2 - lat1) * M_PER_DEG_LAT)


segments = []
with open(DATA / "segments_backbone.csv") as f:
    for r in csv.DictReader(f):
        segments.append((r["segment_id"], float(r["mid_lon"]), float(r["mid_lat"])))
print(f"{len(segments)} backbone segments", flush=True)


def snap(lon, lat):
    best, bestd = None, 1e12
    for sid, slon, slat in segments:
        d = dist_m(lon, lat, slon, slat)
        if d < bestd:
            best, bestd = sid, d
    return best, bestd


def run_track(rows, name_field, road_field, agg_init, agg_add, out_path, out_fields, label):
    agg, misses = {}, []
    matched = 0
    for row in rows:
        ll = None
        for q in variants(row[name_field], row[road_field]):
            ll = geocode(q)
            if ll:
                break
        if not ll:
            misses.append({"source": label, "name": row[name_field], "reason": "no geocode"})
            continue
        sid, d = snap(*ll)
        if d > SNAP_MAX_M:
            misses.append({"source": label, "name": row[name_field], "reason": f"snap {d:.0f}m"})
            continue
        a = agg.setdefault(sid, dict(agg_init))
        agg_add(a, row)
        matched += 1
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["segment_id"] + out_fields)
        w.writeheader()
        for sid, a in sorted(agg.items()):
            w.writerow({"segment_id": sid, **a})
    print(f"{label}: {matched}/{len(rows)} matched -> {len(agg)} segments", flush=True)
    return misses


all_misses = []
crash_rows = list(csv.DictReader(open(DATA / "crash_zones_2023.csv")))
print(f"geocoding {len(crash_rows)} crash zones...", flush=True)
all_misses += run_track(
    crash_rows, "zone", "road",
    {"czones": 0, "crashes_total": 0, "crashes_fatal": 0},
    lambda a, r: (a.__setitem__("czones", a["czones"] + 1),
                  a.__setitem__("crashes_total", a["crashes_total"] + int(r["total"])),
                  a.__setitem__("crashes_fatal", a["crashes_fatal"] + int(r["fatal"]))),
    DATA / "source_accidents_segments.csv",
    ["czones", "crashes_total", "crashes_fatal"], "accidents")

wl_rows = list(csv.DictReader(open(DATA / "waterlogging_2021.csv")))
print(f"geocoding {len(wl_rows)} waterlogging locations...", flush=True)
all_misses += run_track(
    wl_rows, "location", "road",
    {"wl_points": 0, "wl_events": 0},
    lambda a, r: (a.__setitem__("wl_points", a["wl_points"] + 1),
                  a.__setitem__("wl_events", a["wl_events"] + int(r["frequency"]))),
    DATA / "source_waterlog_segments.csv",
    ["wl_points", "wl_events"], "waterlog")

with open(DATA / "geocode_misses.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["source", "name", "reason"])
    w.writeheader()
    w.writerows(all_misses)
CACHE.write_text(json.dumps(cache))
print(f"misses: {len(all_misses)}; cache {len(cache)} queries", flush=True)
