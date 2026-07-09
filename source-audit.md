# Source Feasibility Audit — Delhi NCR Road Quality Dataset

**Date:** 2026-07-08 (Phase 0 deliverable)
**Gate:** v1 needs ≥3 sources including accidents.

## Verdicts at a glance

| # | Source | Verdict | Basis |
|---|--------|---------|-------|
| 1 | Accidents / crash-prone zones | **PASS** | Verified against actual data (see below) |
| 2 | Street imagery + CV | **PARTIAL PASS** | Coverage verified uneven; keep with missingness handling |
| 3 | Citizen complaints | **UNVERIFIED — needs Angira's India connection** | Portals unreachable from US IPs |
| 4 | Repair tenders | **PARKED (v1.1)** | Captcha-gated; no stable automated path found in timebox |
| 5 | Waterlogging-prone points | **PASS** (probed 2026-07-08) | traffic.delhipolice.gov.in/water-logging-area: structured table, **211 locations** with road name + specific location + dates + **frequency count** (2021 vintage; 2025 list of 445 points exists per press — upgrade path via newsletters/RTI). **GATE MET: accidents + CV + waterlogging = 3.** |

## 1. Accidents — PASS

**Primary artifact:** Delhi Road Crash Report 2023 (Delhi Traffic Police, 225 pp PDF,
downloaded to scratchpad; URL: traffic.delhipolice.gov.in/sites/default/files/uploads/2023/Delhi-Crash-Report-2023.pdf).

**Verified contents (pages read directly):**
- **Table 6.29 (pp. 121–124): all 107 crash-prone zones of 2023** — each row has a
  named location ("ISBT Kashmiri Gate", "Britannia Chowk", "Moti Bagh Flyover"…),
  simple/fatal/total crash counts, **and explicit road attribution** (Ring Road ~18
  zones, Outer Ring Road ~15, GTK Road ~11, Rohtak Rd, NH-8, Najafgarh Rd…).
  CPZ definition: ≥3 fatal crashes within 500 m diameter, or ≥10 total crashes.
- Table 6.4/6.5: top fatal crash-prone roads; crashes by road of occurrence
- Tables 6.7/6.8: **Ring Road & Outer Ring Road crashes 2021–2023** (our arterials)
- Table 6.9: crash-prone roads >10 deaths; 6.10: top-25 pedestrian roads
- Table 6.41/6.42: top-10 blackspots 2023 + comparative 2022
- Map 6.1: GIS map of all 107 zones (visual; coordinates not published, but zone
  names are major landmarks — geocodable via Nominatim + manual check)

**Also available:** crash reports for earlier years (2022 PDF confirmed), OpenCity
CSVs (city-level aggregates only — context, not segment-mappable), Data-to-Action
report (district high-risk locations 2019–21).

**Extraction plan (Phase 2):** transcribe Table 6.29 (+ 6.42 for 2022) from PDF →
geocode named zones → snap to segment backbone → `crashes_3yr`, `fatal_crashes`,
`blackspot` flag per segment. ~107 + ~100 rows; manual-verifiable size.

**Caveats:** enforcement/reporting bias (police data); zones are intersections more
than mid-block stretches; only crash-*prone* zones published (censored below
threshold) — segment metric is therefore "zone count / crash count at qualifying
zones", not total crashes.

## 2. Street imagery + CV — PARTIAL PASS

Verified 2024+ Mapillary density on three arterial sample boxes:
- Ring Rd (south, Lajpat Nagar area): **98+ images** (hit query cap) — dense
- NH-48 (Dhaula Kuan): **0 images**
- Outer Ring Rd (west): **0 images**

Coverage is real but patchy even on major arterials. Keep as a source with explicit
per-segment `cv_coverage` flag; segments without recent imagery get NA (not zero).
Collection fixes (full pagination, sequence dedup, ≥2024 filter) required first —
already specced in plan Phase 2.

## 3. Citizen complaints — UNVERIFIED (action: Angira)

- `pwdsewa.pwddelhi.gov.in` — DNS dead from US server *and* US web fetcher
- `mcd311.mcd.gov.in` — unreachable from US server
- main `pwddelhi.gov.in` — reachable (200)

Hypothesis: India-geo-restricted or flaky hosting. **2-minute test for Angira from
her India connection:** open pwdsewa.pwddelhi.gov.in and mcd311.mcd.gov.in — if they
load, check whether complaint listings/dashboards are public (not login-walled) and
whether complaints show location + category + date. Verdict follows from that.

## 4. Repair tenders — PARKED for v1.1

- eprocure.gov.in reachable; CPPP search returns no parseable HTML (JS/session)
- govtprocurement.delhi.gov.in up (200) but tender listings are **captcha-gated**
  (16 captcha refs on the active-tenders page)

No stable automated path within the timebox. Alternatives to explore later:
CPPP bulk/XML feeds, OCDS mirrors, RTI request, manual quarterly export.
Not needed for the v1 gate if sources 1+2+3 (or 1+2+5) hold.

## 5. NEW candidate — waterlogging-prone points

Delhi Traffic Police and PWD publish annual lists of waterlogging-prone locations
(named points, often road-attributed). Road-condition-adjacent, public, geocodable,
and connects directly to the drainage/monsoon angle in the broader project. Probe
next session; if it passes, v1 = accidents + CV + waterlogging even if complaints
fail.

## Gate status

Accidents PASS + CV partial = 2 firm. Third source comes from complaints (her
India test) and/or waterlogging points (next probe). **Gate not yet met — but no
blocker identified; two candidate paths to ≥3.**
