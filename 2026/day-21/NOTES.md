# Day 21 — OpenStreetMap

**Date:** November 21, 2026
**Theme:** OpenStreetMap
**Working title:** Who maps OpenStreetMap
**Sheet:** `2026/images/day-21.png`
**Tools:** Python (`geopandas`, `matplotlib`, `pandas`)
**Script:** `scripts/build_day21_osm.py`

## Setup

From the repository root:

```text
pip install -r requirements.txt
python scripts/build_day21_osm.py
```

`--refresh` ignores the cached ohsomeNow response, the World Bank population CSV, and the Natural Earth download. Those files live in `data/raw/`, which is gitignored. The country table written for the sheet is `2026/21_osm/contributors.csv`.

Behind Zscaler, trust the local corporate cert if HTTPS fails. Do not disable TLS for routine runs.

## What the color means

The color is distinct OpenStreetMap accounts who edited in that country from 1 January 2024 through 1 July 2026, per 100,000 residents. The end date is the first of the month. A person who edited in two countries is counted in both. This is where mapping happened, not the mapper's nationality.

Counts come from the HeiGIT ohsomeNow country stats with no hashtag filter, so the figure is all mapped edits, not one campaign. Population is World Bank `SP.POP.TOTL` for 2025, from the Open Knowledge population table. The live World Bank API was returning HTTP 502 when this sheet was built.

The scale is logarithmic, from 0.5 to the highest rate among countries of at least one million people (Slovenia, about 235). Smaller places can sit above that. They share the darkest green. Greenland, Andorra, Monaco, and several Caribbean islands do, because a modest number of editors is a large rate against a small population.

Countries with no World Bank population are blank. Taiwan is the main one: ohsomeNow counts 4,023 contributors there, and the World Bank table does not include it. Antarctica is left off the sheet.

## Rank among countries over one million

Highest per 100,000: Slovenia, Austria, Estonia, Switzerland, Croatia.

Lowest per 100,000: China, India, Bangladesh, Pakistan, Ethiopia.

China is about 0.7 contributors per 100,000 people. Central Europe is mostly above 100.
