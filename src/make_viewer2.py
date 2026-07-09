#!/usr/bin/env python3
"""Generate the multi-source QA viewer (v2): muted basemap, combined "all issues"
layer, clearer coverage view. Internal QA tool, not a public product.

Usage: python make_viewer2.py            -> viewer.html
Reads: data/segments_backbone.geojson (geometry) + data/segments.csv (metrics)
"""
import csv
import json
import pathlib

ROOT = pathlib.Path.home() / "road_quality"
DATA = ROOT / "data"

metrics = {r["segment_id"]: r for r in csv.DictReader(open(DATA / "segments.csv"))}
fc = json.load(open(DATA / "segments_backbone.geojson"))

features = []
for f in fc["features"]:
    sid = f["properties"]["segment_id"]
    m = metrics.get(sid)
    if not m:
        continue
    coords = [[round(x, 5), round(y, 5)] for x, y in f["geometry"]["coordinates"]]
    features.append({
        "type": "Feature",
        "properties": {
            "id": sid, "road": m["road_canonical"],
            "ct": m["crashes_total"], "cf": m["crashes_fatal"], "cz": m["czones"],
            "wp": m["wl_points"], "we": m["wl_events"],
            "ci": m["cv_images"], "cd": m["cv_detections"], "cdpf": m["cv_damage_per_frame"],
            "ns": m["n_sources"],
        },
        "geometry": {"type": "LineString", "coordinates": coords},
    })

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Delhi Roads — Multi-Source QA Viewer</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body { height:100%; margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
  #map { height:100%; background:#f4f4f2; }
  .panel { position:absolute; top:12px; right:12px; z-index:1000; background:rgba(255,255,255,.97);
    border-radius:10px; padding:14px 16px; box-shadow:0 2px 10px rgba(0,0,0,.25); width:280px; font-size:13px; }
  .panel h1 { font-size:15px; margin:0 0 8px; }
  label { display:block; margin:3px 0; cursor:pointer; }
  .lg { margin:8px 0 0; font-size:12px; line-height:1.6; }
  .sw { display:inline-block; width:22px; height:5px; margin-right:6px; vertical-align:2px; border-radius:2px; }
  .stat { color:#555; font-size:12px; margin:6px 0 0; }
  .warn { background:#fff3cd; border:1px solid #ffe08a; border-radius:6px; padding:7px 9px; margin-top:10px;
    font-size:11.5px; line-height:1.35; color:#664d03; }
  .popup td { padding:1px 6px 1px 0; }
</style>
</head>
<body>
<div id="map"></div>
<div class="panel">
  <h1>Delhi Roads — QA Viewer</h1>
  <label><input type="radio" name="layer" value="all" checked> All issues (combined)</label>
  <label><input type="radio" name="layer" value="crashes"> Crashes (2023 zones)</label>
  <label><input type="radio" name="layer" value="waterlog"> Waterlogging (2021)</label>
  <label><input type="radio" name="layer" value="cv"> CV damage (2024+ imagery)</label>
  <label><input type="radio" name="layer" value="coverage"> Data coverage</label>
  <div class="lg" id="legend"></div>
  <div class="stat" id="stat"></div>
  <div class="warn"><b>Internal QA.</b> Arterials only; sources cover different
  subsets (thin grey = unobserved, not "fine"). CV detector unvalidated.</div>
</div>
<script>
const FC = __DATA__;

const map = L.map("map");
// Muted grayscale basemap so data colors stand out
L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
  maxZoom: 19, subdomains: "abcd",
  attribution: "&copy; OpenStreetMap &copy; CARTO"
}).addTo(map);

const num = v => (v === "" || v === undefined) ? null : +v;
const BASE = {color:"#d0d0d0", weight:1, opacity:0.5};   // unobserved / background

// Issue tests per source
const hasCrash = p => num(p.ct) > 0;
const hasWL    = p => num(p.we) > 0;
const hasCV    = p => num(p.cdpf) > 0;

const LAYERS = {
  all: {
    kind: "cat",
    style(p) {
      const k = [hasCrash(p), hasWL(p), hasCV(p)].filter(Boolean).length;
      if (k >= 2) return {color:"#6a0dad", weight:7, opacity:0.95};   // multiple issue types
      if (hasCrash(p)) return {color:"#d7191c", weight:5, opacity:0.9};
      if (hasWL(p))    return {color:"#2b6cb8", weight:5, opacity:0.9};
      if (hasCV(p))    return {color:"#f08c00", weight:5, opacity:0.9};
      return null;
    },
    legend: [["#6a0dad","2-3 issue types on segment"],["#d7191c","crash zone"],
             ["#2b6cb8","waterlogging"],["#f08c00","CV surface damage"]],
    stat(fs) {
      const k = fs.filter(f => hasCrash(f.properties)||hasWL(f.properties)||hasCV(f.properties)).length;
      const multi = fs.filter(f => [hasCrash(f.properties),hasWL(f.properties),hasCV(f.properties)].filter(Boolean).length>=2).length;
      return `${k} segments flagged by any source; ${multi} by 2+ issue types`;
    },
  },
  crashes: {
    kind: "num", val: p => num(p.ct),
    stops: [[1,"#fca082"],[8,"#d7191c"],[15,"#67000d"]],
    legend: [["#fca082","1-7 crashes"],["#d7191c","8-14"],["#67000d","15+"]],
    stat(fs){ const k=fs.filter(f=>hasCrash(f.properties)).length; return `${k} segments carry a 2023 crash-prone zone`; },
  },
  waterlog: {
    kind: "num", val: p => num(p.we),
    stops: [[1,"#9ecae1"],[3,"#3182bd"],[6,"#08306b"]],
    legend: [["#9ecae1","1-2 events"],["#3182bd","3-5"],["#08306b","6+"]],
    stat(fs){ const k=fs.filter(f=>hasWL(f.properties)).length; return `${k} segments had 2021 waterlogging`; },
  },
  cv: {
    kind: "num", val: p => num(p.cdpf), zeroColor: "#1a9641",
    stops: [[0.0001,"#fdae61"],[0.2,"#e2540d"],[0.5,"#7f2704"]],
    legend: [["#1a9641","imagery, no damage found"],["#fdae61","low"],["#e2540d","medium"],["#7f2704","high det/frame"]],
    stat(fs){
      const cov=fs.filter(f=>num(f.properties.ci)>0).length;
      const pos=fs.filter(f=>hasCV(f.properties)).length;
      return `${cov} segments have 2024+ imagery; ${pos} show damage`;
    },
  },
  coverage: {
    kind: "num", val: p => num(p.ns) || null,
    stops: [[1,"#fdbe85"],[2,"#e6550d"],[3,"#7f2704"]],
    legend: [["#fdbe85","1 source"],["#e6550d","2 sources"],["#7f2704","3 sources"]],
    weightFor: v => v >= 2 ? 7 : 4,
    stat(fs){
      const n=fs.length;
      const c=[0,0,0,0];
      fs.forEach(f=>c[Math.min(3,num(f.properties.ns)||0)]++);
      return `${c[1]+c[2]+c[3]}/${n} segments observed (${Math.round(100*(c[1]+c[2]+c[3])/n)}%): `+
             `${c[1]} by one source, ${c[2]} by two, ${c[3]} by three`;
    },
  },
};

function popup(p) {
  return `<div class="popup"><b>${p.road}</b> &middot; ${p.id}<table>
  <tr><td>crash zones / crashes / fatal</td><td>${p.cz||0} / ${p.ct||0} / ${p.cf||0}</td></tr>
  <tr><td>waterlog points / events</td><td>${p.wp||0} / ${p.we||0}</td></tr>
  <tr><td>CV frames / detections</td><td>${p.ci||"NA"} / ${p.cd||"0"}</td></tr>
  <tr><td>sources observing</td><td>${p.ns}</td></tr></table></div>`;
}

let lg = L.layerGroup().addTo(map);
function render(which) {
  lg.clearLayers();
  const cfg = LAYERS[which];
  // draw unobserved background first, colored segments on top
  const colored = [];
  for (const f of FC.features) {
    const p = f.properties;
    let style = null;
    if (cfg.kind === "cat") {
      style = cfg.style(p);
    } else {
      const v = cfg.val(p);
      if (v !== null) {
        if (v === 0 && cfg.zeroColor) style = {color:cfg.zeroColor, weight:4, opacity:0.85};
        else if (v > 0) {
          let col = null;
          for (const [t, c] of cfg.stops) if (v >= t) col = c;
          if (col) style = {color:col, weight:cfg.weightFor ? cfg.weightFor(v) : 5, opacity:0.9};
        }
      }
    }
    const latlngs = f.geometry.coordinates.map(c => [c[1], c[0]]);
    if (style) colored.push([latlngs, style, p]);
    else L.polyline(latlngs, BASE).bindPopup(popup(p)).addTo(lg);
  }
  for (const [latlngs, style, p] of colored)
    L.polyline(latlngs, style).bindPopup(popup(p)).addTo(lg);

  document.getElementById("legend").innerHTML =
    cfg.legend.map(([c,t]) => `<span class="sw" style="background:${c}"></span>${t}`).join("<br>")
    + `<br><span class="sw" style="background:#d0d0d0"></span>unobserved / no data`;
  document.getElementById("stat").textContent = cfg.stat(FC.features);
}
document.querySelectorAll("input[name=layer]").forEach(el =>
  el.addEventListener("change", e => render(e.target.value)));
render("all");
map.setView([28.635, 77.15], 11);
</script>
</body>
</html>
"""

out = ROOT / "viewer.html"
out.write_text(TEMPLATE.replace("__DATA__", json.dumps(
    {"type": "FeatureCollection", "features": features}, separators=(",", ":"))))
print(f"wrote {out} ({out.stat().st_size/1e6:.1f} MB): {len(features)} segments")
