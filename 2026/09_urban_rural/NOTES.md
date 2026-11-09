# Day 9 — Urban-rural

**Date:** November 9, 2026
**Theme:** Urban-rural
**Working title:** Where the city meets the woods
**Sheet:** 11 × 17 in landscape
**Tools:** Python (`geopandas`, `matplotlib`, `rasterio`)
**Script:** `scripts/build_day09_wui_map.py`

## Setup

From the repository root:

```text
pip install -r requirements.txt
pip install -r 2026/08_utopia/requirements.txt
python scripts/build_day09_wui_map.py
```

`rasterio` is only in the Day 8 requirements file. It is used to sample the county footprints from the CONUS raster. The script does not load the national grid into memory.

`--neighborhood 500` switches to the 500 m map. Choices: 100, 250, 500, 750, 1000, 1500. The default is 100 m, the tightest edge. Carlson validated the 500 m map. `--refresh` ignores the cached extract and queries FEMA again. `--raster` overrides the GeoTIFF path.

Behind Zscaler, trust the local corporate cert if HTTPS fails. Do not disable TLS for routine runs.

## What the color means

The local folder is the USGS data release, stored as 30 m GeoTIFFs. `data_dictionary.csv` documents them. `CONUS_WUI_100m.tif` values:

| Value | Class | Poster color | Rule |
| --- | --- | --- | --- |
| 1 | Intermix | Gold | At least 50% wildland vegetation in the neighborhood |
| 2 | Interface | Ember | Within 2.4 km of a wildland patch of at least 5 km², with less vegetation mixed in |
| 0 | Not WUI | Quiet olive | Neither class |

Both WUI classes also require at least 6.17 buildings per km². Citation: Carlson, Helmers, Hawbaker, Mockrin, and Radeloff, 2022, [doi:10.5066/P94BT6Q7](https://doi.org/10.5066/P94BT6Q7). The raster uses 2018 Microsoft footprints and 2016 NLCD. The dots are current FEMA / Overture footprints, sampled onto that raster.

The composite raster (`CONUS_WUI_composite.tif`) records where a pixel enters or leaves the WUI as the neighborhood grows. It is not on this sheet.

## Outputs

- `2026/images/day-09.png` — gallery raster, 17 × 11 in at 200 dpi
- `2026/09_urban_rural/day-09-11x17.pdf` — same sheet for print
- `data/processed/day09_hamilton_wui_100m.npz` — cached centroids and class (gitignored)
- `data/raw/hamilton_county.geojson` — county boundary (gitignored)
- `data/raw/day09_hillshade.png` — USGS 3DEP hillshade (gitignored)

The CONUS rasters stay on disk at `G:\GIS\D_tin-topo\project_data\30_day_map_challenge\2026\CONUS_building_footprint_WUI_data`. They are not copied into the repo.

## Sources

- FEMA WUI Structures V2, current building footprints
- Carlson et al. 2022, USGS data release, `CONUS_WUI_100m.tif`
- Hamilton County GIS county boundary, with Tennessee STS counties as a fallback
- USGS 3DEP hillshade

## Daily record

```text
Date: 2026-11-09
Theme: Urban-rural
Title: Where the city meets the woods
Concept: Hamilton County building footprints classed as intermix or interface WUI
Data sources: FEMA WUI Structures V2; Carlson et al. 2022 CONUS WUI (100 m); Hamilton County GIS; USGS 3DEP
Software/tools: Python (geopandas, matplotlib, rasterio)
Analysis: County clip of structure centroids, sampled onto the 100 m WUI raster
Cartographic technique: 11×17 poster, hillshade ground, three WUI classes
Time spent: Not tracked
What worked:
What I would change:
Post URL:
```
