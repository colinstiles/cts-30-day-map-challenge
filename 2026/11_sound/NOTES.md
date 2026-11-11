# Day 11 — Senses: Sound

**Date:** November 11, 2026
**Theme:** Senses: Sound
**Working title:** Where the guns were heard
**Tools:** Python (`numpy`, `matplotlib`, `shapely`), Leaflet
**Script:** `scripts/build_day11_sound.py`

## Setup

From the repository root:

```text
pip install -r requirements.txt
python scripts/build_day11_sound.py
```

`shapely` comes in with `geopandas`. `--refresh` ignores the cached boundary, cemetery, city node, 3DEP GeoTIFF, and audibility grid.

Behind Zscaler, trust the local corporate cert if HTTPS fails. Do not disable TLS for routine runs.

## What the color means

Three washes, one for each battle. Where they overlap, the color mixes. The value is a relative reach from 0 to 1. It is not a decibel, a contour, or a measured sound level.

On open ground the proxy is 1 beside the gun, 0.60 at 10 miles, and 0 at 15 miles. Ten miles is the open-ground reference because Chickamauga's guns were heard in Chattanooga, on the order of ten miles away. Fifteen miles is the outer fade used for this sheet.

Terrain above the straight path multiplies that fade. Each 90 m of ridge above the path leaves about a third of the proxy (`exp(-height / 90)`). Lookout, hundreds of meters above the river, nearly silences the far side. A lower ridge reduces the reach without erasing it. Earth curvature is included. Atmospheric refraction is not: cannon sound ducts with the weather, and this map does not model that.

The profile is sampled on a grid of about 80 by 100 m. A rise narrower than that can be missed. These ridges are not that narrow.

## Representative points

Not batteries. Each point is one place standing in for a field of fire.

| Battle | Rule | Lat, lon | Elevation |
| --- | --- | --- | --- |
| Chickamauga, Sept 19–20, 1863 | Centroid of the main battlefield unit | 34.91897, -85.25454 | 227 m |
| Lookout Mountain, Nov 24, 1863 | Highest 3DEP cell at the north end of the mountain unit | 35.00969, -85.34395 | 644 m |
| Missionary Ridge, Nov 25, 1863 | Highest 3DEP cell in the largest ridge reservation | 35.06886, -85.24052 | 307 m |

The Missionary Ridge point is the north end of the ridge (the Sherman end of the November 25 line), because that reservation is the largest ridge unit in the park boundary. It is not the center of the charge.

Downtown Chattanooga is 9.3 miles from the Chickamauga point. Chattanooga National Cemetery is 8.2 miles from it. A straight path from the middle of the field toward downtown crosses the south end of Missionary Ridge, so the Chickamauga wash is fainter in the city than on open ground at the same distance. Guns farther north on the field, and sound through Rossville Gap, are not separate sources.

At those distances the cached proxy is about 0.21 at downtown and 0.22 at the cemetery for Chickamauga, and about 0.8 for Lookout and Missionary Ridge. Seven kilometers west of the Lookout point the Lookout proxy is about 0.34, against about 0.82 toward the city. That west-side drop is the mountain, not a circle.

## Outputs

- `2026/images/day-11.png` — gallery sheet
- `2026/day-11.html` — interactive toggles on an Esri topo basemap
- `2026/11_sound/audibility-*.png` — transparent washes for the page
- `2026/11_sound/bounds.json` — extent, distances, source points
- `2026/11_sound/places.geojson` — park units, cemetery, city, sources
- `data/raw/day11-3dep.tif` — USGS 3DEP cache (gitignored)
- `data/raw/day11_chch_boundary.geojson` — NPS boundary cache (gitignored)
- `data/processed/day11_audibility.npz` — coarse reach grids (gitignored)

Distances use a local equirectangular scale in EPSG:4326 at the map center. That is accurate enough for this proxy. It is not a survey.

## Sources

- NPS Land Resources Division boundary, Chickamauga and Chattanooga National Military Park (`UNIT_CODE` CHCH)
- USGS 3DEP ImageServer
- OpenStreetMap: Chattanooga National Cemetery and the Chattanooga place node
- Esri Dark Gray Canvas on the sheet; Esri World Topo Map on the interactive page

Chattanooga National Cemetery was established by Gen. George H. Thomas on December 25, 1863, for the Union dead of the battles around the city. It became a national cemetery in 1867.

## Daily record

```text
Date: 2026-11-11
Theme: Senses: Sound
Title: Where the guns were heard
Concept: Terrain-shadowed audible reach of Chickamauga, Lookout Mountain, and Missionary Ridge over modern Chattanooga
Data sources: NPS CHCH boundary; USGS 3DEP; OpenStreetMap cemetery and city; Esri basemaps
Software/tools: Python (numpy, matplotlib, shapely), Leaflet
Analysis: Distance fade to 15 miles, times an exponential ridge penalty. Not a decibel model.
Cartographic technique: Hillshade and dark canvas, three washes, 10-mile reference ring, cemetery callout
Time spent: Not tracked
What worked:
What I would change:
Post URL:
```
