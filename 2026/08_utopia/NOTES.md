# Day 8 — Utopia

**Date:** November 8, 2026  
**Theme:** Utopia  
**Working title:** Tugalo Undammed — Lake Tugalo drained  
**Focus:** Georgia Power Tugalo plant `34.71396, -83.35183`  
**Script:** `scripts/day08_tugalo_undammed.py`

## Story

Tugalo Dam (1923) drowned ~597 acres at the Tallulah–Chattooga confluence. Utopia = dam gone, pool gone, free rivers back.

## Deliverables

| Output | Role |
| --- | --- |
| `2026/day-08.html` | Leaflet swipe (now left ↔ utopia right) |
| `2026/images/day-08-now.png` | Now overlay |
| `2026/images/day-08-utopia.png` | Utopia overlay |
| `2026/images/day-08.png` | Static dual-panel gallery still |
| `2026/images/day-08-bounds.json` | Image overlay bounds + dam |

## Setup / run

```text
pip install -r 2026/08_utopia/requirements.txt
python scripts/day08_tugalo_undammed.py
```

If USGS 3DEP is down (504 / WMS unavailable):

```text
python scripts/day08_tugalo_undammed.py --source opentopo
# optional: export OPENTOPOGRAPHY_API_KEY=...  (else uses OT demo key)
# or: python scripts/day08_tugalo_undammed.py --dem data/raw/tugalo_dem.tif
```

Behind Zscaler, trust the corporate cert if HTTPS fails.

## Honesty

Lake outline and restored valley are **schematic** (not surveyed bathymetry). Credit that on the map.
