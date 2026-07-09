#!/usr/bin/env python3
"""Track 2: scrape the Delhi Traffic Police waterlogging table (2021 list).
Source: https://traffic.delhipolice.gov.in/water-logging-area
Output: data/waterlogging_2021.csv (sno, road, location, dates, frequency)
"""
import csv
import pathlib
import re
from html.parser import HTMLParser

import requests

ROOT = pathlib.Path.home() / "road_quality"
URL = "https://traffic.delhipolice.gov.in/water-logging-area"


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_td = False
        self.rows, self.cur = [], []
        self.buf = ""

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self.in_td, self.buf = True, ""
        elif tag == "tr":
            self.cur = []

    def handle_endtag(self, tag):
        if tag == "td":
            self.in_td = False
            self.cur.append(re.sub(r"\s+", " ", self.buf).strip())
        elif tag == "tr" and self.cur:
            self.rows.append(self.cur)

    def handle_data(self, data):
        if self.in_td:
            self.buf += data


r = requests.get(URL, timeout=60, headers={"User-Agent": "Mozilla/5.0 (research; angiras@uchicago.edu)"})
r.raise_for_status()
p = TableParser()
p.feed(r.text)

out = []
for row in p.rows:
    if len(row) < 4 or not row[0].strip(".").strip().isdigit():
        continue
    freq = row[4] if len(row) > 4 else ""
    m = re.search(r"\d+", freq)
    out.append({"sno": row[0].strip("."), "road": row[1], "location": row[2],
                "dates": row[3], "frequency": int(m.group()) if m else max(1, row[3].count(",") + 1)})

path = ROOT / "data" / "waterlogging_2021.csv"
with open(path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["sno", "road", "location", "dates", "frequency"])
    w.writeheader()
    w.writerows(out)
print(f"scraped {len(out)} waterlogging locations -> {path}")
print("first 3:", out[:3])
print("total events:", sum(r['frequency'] for r in out))
