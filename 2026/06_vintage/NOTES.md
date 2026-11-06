# Day 6 — Vintage

**Date:** November 6, 2026
**Theme:** Vintage
**Working title:** Chattanooga, Then & Now — historic topo swipe map
**Tools:** Leaflet, OpenStreetMap, Python (`rasterio` / `rioxarray`, `matplotlib`)
**Script:** `scripts/day06_vintage_chattanooga.py`

## Open choice (pick before download)

| Option | Scale | Why |
| --- | --- | --- |
| **Preferred:** Chattanooga 1940 (printed 1956) | 1:24,000 | Classic mid-century sheet; tight city + ridge frame |
| Chattanooga 1969 (printed 1987) | 1:24,000 | Later culture; still readable with blend |
| Chattanooga 1957 / 1959 | 1:250,000 | Wider regional context; coarser linework |

## Setup

```text
pip install -r 2026/06_vintage/requirements.txt
```

Includes `matplotlib` (required for export). If the script exits with `Missing packages: matplotlib`, re-run that install in the same venv.

Behind Zscaler, trust the local corporate cert if HTTPS to USGS fails. Do not disable TLS for routine runs.

1. Download HTMC GeoTIFF from [TopoView](https://ngmdb.usgs.gov/topoview/) → save as `data/raw/chattanooga_htmc.tif`
2. Run:

```text
python scripts/day06_vintage_chattanooga.py
```

Hillshade-only smoke test (no topo file yet):

```text
python scripts/day06_vintage_chattanooga.py --bbox-only
```

Useful flags: `--blend soft-light`, `--layer "Hillshade Multidirectional"`, `--topo-weight 0.55`, `--topo path/to.tif`

## Stack

| Role | Package | Notes |
| --- | --- | --- |
| 3DEP hillshade | [py3dep](https://docs.hyriver.io/readme/py3dep.html) | `get_map("Hillshade Gray", ...)` |
| Read / reproject | `rasterio`, `rioxarray` | Align hillshade to HTMC grid |
| Composite + layout | `numpy`, `matplotlib` | Multiply / soft-light; title + export |
| Historic topo | USGS HTMC via TopoView | Manual GeoTIFF download |

## Outputs

- `data/processed/chattanooga_hillshade.tif` (gitignored)
- `2026/images/day-06-historic.png` (historic overlay used by `2026/day-06.html`)
- `2026/day-06.html` (gallery slider visualization)

Year layout: see `2026/README.md`.

## Daily record

```text
Date: 2026-11-06
Theme: Vintage
Title: Chattanooga, Then & Now
Concept: Historic USGS Chattanooga topo compared with modern streets and places
Data sources: USGS HTMC (TopoView); OpenStreetMap contributors
Software/tools: Leaflet; Python (rasterio/rioxarray, matplotlib)
Analysis: Georeferenced historic sheet over a synchronized modern basemap
Cartographic technique: Slider-controlled image-overlay swipe
Time spent: Not tracked
What worked: The shared geography makes changes to roads, city fabric, and place names immediately visible.
What I would change: Add annotation callouts for a curated set of visible changes.
Post URL:
```
