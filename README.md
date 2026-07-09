# Delhi Road Quality — a multi-source open dataset

**[▶ Open the interactive map](https://angirashukla.github.io/delhi-road-quality/viewer.html)** — crashes, waterlogging, detected surface damage, and data coverage on Delhi's arterial network.

A segment-level dataset triangulating **three independent public sources** of road
quality for ~985 km of Delhi's arterial roads (motorway / trunk / primary), cut into
2,701 ~1 km segments. No composite index: each source is reported in its own
column, with per-segment source counts, so users can weight (or distrust) sources
themselves.

| Source | What it measures | Vintage | Segments covered |
|---|---|---|---|
| **Crash-prone zones** (Delhi Traffic Police, Road Crash Report 2023, Table 6.29) | 107 zones with simple/fatal crash counts, road-attributed | 2023 | 80 |
| **Waterlogging locations** (Delhi Traffic Police) | 211 locations with event dates + frequency | 2021 | 136 |
| **CV surface damage** (Mapillary street imagery × RDD2022 YOLOv8 detector) | cracks/potholes per frame, recent imagery only | 2024–26 | 561 (21%) |

Cross-source agreement (road level, 64 named roads ≥3 km): crashes/km ×
waterlogging/km ρ≈0.29; crashes/km × CV damage ρ≈0.29. Segment-level correlations
are attenuated by geocoding noise and small overlaps — see `AGREEMENT.md`.

## Files

```
data/
  segments.csv               ← the dataset: one row per ~1 km segment, per-source columns
  roads.csv                  road-level rollup (canonical names; Ring Road fragments merged)
  segments_backbone.geojson  segment geometries
  arterials.geojson          raw OSM arterial ways
  crash_zones_2023.csv       all 107 crash-prone zones (transcribed; sums verified
                             against published totals: 697 simple / 366 fatal / 1,063)
  waterlogging_2021.csv      211 scraped waterlogging locations
  source_*_segments.csv      per-source segment aggregates
  cv_coverage.csv            recent-imagery coverage per segment (NA ≠ 0)
src/                         full pipeline (see Reproduce)
viewer.html                  self-contained interactive map (also served via the link above)
AGREEMENT.md                 cross-source agreement analysis
source-audit.md              source feasibility audit (incl. sources that failed)
```

**Conventions.** Missing source at a segment = empty cell (unobserved), never 0.
CV: a segment *with* recent imagery and no detections is `0.0` (observed clean); a
segment with no recent imagery is empty (unobserved). `n_sources` counts sources
observing each segment.

## Pipeline

1. `backbone.py` — OSM Overpass → Delhi arterials → 1 km segments with stable IDs
2. `scrape_waterlogging.py` — Delhi Traffic Police waterlogging table → CSV
3. `geocode_snap.py` — Photon/Nominatim geocoding (cleaned query variants) → snap
   to nearest segment (≤1.5 km)
4. `collect.py` — Mapillary imagery manifest along the backbone (2024+, sequence-
   deduped at 50 m, capped 8 frames/segment)
5. `detect.py` — RDD2022-trained YOLOv8 on road ROI (lower 60%, 1280 px inference)
6. `fuse.py` — join everything, road-name alias consolidation (Ring Road = Mahatma
   Gandhi Marg/Road — spatially verified; Outer Ring Road = Dr KB Hedgewar Marg),
   agreement analysis
7. `make_viewer2.py` — regenerate `viewer.html` from the data

## Known limitations (read before using)

- **CV detector is unvalidated for Delhi.** Raw RDD2022 transfer, no India
  fine-tune, no ground-truth comparison; recall is unknown and likely low.
  Treat `cv_*` columns as a noisy lower bound on visible damage.
- **Crash zones are censored.** Only zones meeting the police threshold (≥3 fatal
  within 500 m, or ≥10 total crashes) are published — segment crash columns are
  "crashes at qualifying zones," not total crashes. Police data carries
  reporting/enforcement bias.
- **Geocoding is landmark-based.** 91/107 crash zones and 163/211 waterlogging
  locations geocoded and snapped (misses listed in the audit); positions carry
  snap error up to 1.5 km.
- **Waterlogging list is 2021 vintage** (the last published structured table);
  press reports 445 points for 2025 — an upgrade path, not yet in the data.
- **Coverage varies by source** — see the coverage layer in the viewer. Absence of
  data is not evidence of a good road.
- Arterials only; dual carriageways appear as separate segments.

## Reproduce

Python 3.12 venv with `requests shapely ultralytics pillow`. A free
[Mapillary token](https://www.mapillary.com/developer) in `.mapillary_token` is
needed for imagery collection (steps 4–5); everything else runs without keys.
Run the pipeline in the numbered order above. GPU recommended for step 5
(tested on an NVIDIA A40; a consumer GPU works).

## Licensing & attribution

- **Data** (`data/`, `viewer.html`): **CC BY-SA 4.0** — inherits share-alike from
  Mapillary imagery (CC BY-SA) and the RDD2022 dataset (CC BY-SA 4.0).
- **Code** (`src/`): MIT.
- Crash and waterlogging figures derive from Delhi Traffic Police publications
  (Road Crash Report 2023; delhitrafficpolice.gov.in). Road network © OpenStreetMap
  contributors (ODbL). Detector weights from
  [oracl4/RoadDamageDetection](https://github.com/oracl4/RoadDamageDetection).

## Status

Exploratory research dataset (v1, July 2026). Built as part of ongoing work on
measuring Indian road quality from public data. Feedback and corrections welcome —
open an issue.
