#!/usr/bin/env python3
"""Track 3 (CV) step 2: download manifest images, run the RDD2022 detector on a
road ROI (lower 60%, upscaled inference for distant distress), aggregate per segment.

Output:
  data/source_cv_segments.csv  segment_id, cv_images, cv_detections, cv_damage_per_frame
  outputs/detect_v3.log        progress
  outputs/annotated_v3/        first 40 positive frames (QA sample)
"""
import csv
import pathlib
import time

import requests
from PIL import Image
from ultralytics import YOLO

ROOT = pathlib.Path.home() / "road_quality"
DATA = ROOT / "data"
IMG = DATA / "images_v3"; IMG.mkdir(exist_ok=True)
CROP = DATA / "cropped_v3"; CROP.mkdir(exist_ok=True)
ANN = ROOT / "outputs" / "annotated_v3"; ANN.mkdir(parents=True, exist_ok=True)
CONF = 0.45
ROI_TOP = 0.40          # keep lower 60% of frame (road region)
QA_SAMPLE = 40

manifest = list(csv.DictReader(open(DATA / "cv_manifest.csv")))
print(f"{len(manifest)} images in manifest")

model = YOLO(str(ROOT / "models" / "YOLOv8_Small_RDD.pt"))
per_seg = {}
n_dl_fail = n_pos = 0
t0 = time.time()
for i, m in enumerate(manifest):
    p = IMG / f"{m['image_id']}.jpg"
    if not p.exists():
        try:
            p.write_bytes(requests.get(m["url"], timeout=30).content)
        except Exception:
            n_dl_fail += 1
            continue
    try:
        im = Image.open(p).convert("RGB")
    except Exception:
        n_dl_fail += 1
        continue
    W, H = im.size
    cpath = CROP / f"{m['image_id']}.jpg"
    if not cpath.exists():
        im.crop((0, int(ROI_TOP * H), W, H)).save(cpath)
    res = model.predict(str(cpath), conf=CONF, imgsz=1280, verbose=False, device=0)[0]
    n = len(res.boxes)
    s = per_seg.setdefault(m["segment_id"], {"cv_images": 0, "cv_detections": 0})
    s["cv_images"] += 1
    s["cv_detections"] += n
    if n and n_pos < QA_SAMPLE:
        res.save(filename=str(ANN / f"{m['image_id']}.jpg"))
    if n:
        n_pos += 1
    if (i + 1) % 500 == 0:
        print(f"  {i+1}/{len(manifest)} | positives {n_pos} | dl_fail {n_dl_fail} | {time.time()-t0:.0f}s", flush=True)

with open(DATA / "source_cv_segments.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["segment_id", "cv_images", "cv_detections", "cv_damage_per_frame"])
    w.writeheader()
    for sid, s in sorted(per_seg.items()):
        w.writerow({"segment_id": sid, **s,
                    "cv_damage_per_frame": round(s["cv_detections"] / s["cv_images"], 4) if s["cv_images"] else ""})

print(f"\n=== DETECT SUMMARY ===")
print(f"frames analyzed: {sum(s['cv_images'] for s in per_seg.values())} | download failures: {n_dl_fail}")
print(f"frames with >=1 detection: {n_pos}")
print(f"segments with CV data: {len(per_seg)}")
