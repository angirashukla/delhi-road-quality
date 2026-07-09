# Delhi Roads — mapping reported road problems

**[▶ Open the map](https://angirashukla.github.io/delhi-road-quality/viewer.html)**

A personal, exploratory project mapping what public reports say about the condition
of Delhi's arterial roads. It combines three things that rarely sit on the same map:
police crash-prone zones, waterlogging locations, and road-surface damage detected
in street imagery — snapped to a common grid of 2,701 ~1 km road segments.

**What this is not.** It is not a measure of Delhi's road quality. Every layer is
*reported or detected* cases only, and coverage is thin: crash zones exist only
where police counts crossed a publication threshold, the waterlogging list is from
2021, and only 21% of segments have recent street imagery. A blank segment means
*no data*, not a good road. Treat this as a starting point for looking, not a
conclusion.

| Layer | Source | Vintage | Segments with data |
|---|---|---|---|
| Crash-prone zones | Delhi Traffic Police, Road Crash Report 2023 (Table 6.29, all 107 zones; transcription sums match published totals) | 2023 | 80 |
| Waterlogging | Delhi Traffic Police waterlogging list (211 locations, event frequency) | 2021 | 136 |
| Surface damage | Mapillary street imagery × an RDD2022-trained YOLOv8 detector (unvalidated for Delhi — noisy lower bound) | 2024–26 | 561 |

Where the layers can be compared (64 named roads ≥3 km), crashes/km and
waterlogging/km rank-correlate at ρ≈0.29, as do crashes/km and detected damage —
suggestive, not conclusive. Details in `AGREEMENT.md`.

## Files

```
data/segments.csv              one row per ~1 km segment, one column per layer
data/roads.csv                 road-level rollup (Ring Road name fragments merged)
data/segments_backbone.geojson segment geometries
data/crash_zones_2023.csv      the 107 zones as published
data/waterlogging_2021.csv     the 211 locations as published
data/source_*_segments.csv     per-layer segment aggregates
data/cv_coverage.csv           which segments have recent imagery (NA ≠ 0)
src/                           pipeline (backbone → scrape → geocode/snap → imagery → detect → fuse → viewer)
viewer.html                    the map (self-contained; same file the link serves)
source-audit.md                what was tried, incl. sources that didn't work out
AGREEMENT.md                   how the layers relate
```

Conventions: empty cell = unobserved, never 0. A segment with imagery and no
detections is 0.0 (observed clean); a segment with no imagery is empty.

## Caveats, in order of importance

1. **Reported cases only.** Police publish only zones above a threshold (≥3 fatal
   in 500 m or ≥10 crashes); the waterlogging list is what officers logged in 2021.
   Both carry reporting and enforcement bias.
2. **The damage detector is unvalidated here** — no India fine-tune, no ground
   truth; recall unknown and likely low.
3. **Geocoding is landmark-based** (91/107 zones, 163/211 waterlogging points
   placed; the rest listed in `data/geocode_misses.csv`), with up to ~1.5 km snap
   error.
4. **Arterials only**; dual carriageways are separate segments.

## Reproduce

Python 3.12, `requests shapely ultralytics pillow`. A free Mapillary token in
`.mapillary_token` for the imagery steps; everything else needs no keys. Run
`src/` scripts in pipeline order. GPU helps for detection.

## Attribution

Data sources: Delhi Traffic Police publications; © OpenStreetMap contributors
(ODbL); Mapillary imagery (CC BY-SA); RDD2022 detector weights via
[oracl4/RoadDamageDetection](https://github.com/oracl4/RoadDamageDetection).
Because the imagery-derived layer inherits share-alike terms, reuse of the data
files should credit sources and stay share-alike (see `LICENSE`); code is MIT.
