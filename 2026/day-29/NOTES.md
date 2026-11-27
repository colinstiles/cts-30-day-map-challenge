# Day 29 — Raster

**Date:** November 29, 2026
**Theme:** Raster
**Title:** Same fuels, a 2047 climate
**Tools:** Python, LANDFIRE, FSim

## What is drawn

`day-29.html` is one 270 m grid of Tennessee, three ways.

Threat brightens each cell by the annual chance a large fire burns it under weather for 2040–2054. The hue is the LANDFIRE fuel group. Fuels is that fuel mosaic on its own. Change warms where the 2047 probability is higher than 2004–2018 and cools where it is lower. The state outline is the Tennessee STS county polygons, dissolved. Agriculture, urban, water, and barren are LANDFIRE non-burnable and stay dark.

The pointer reads the cell: fuel model, both probabilities as a share of simulated years, the percent change, and slope. Burn probability is times burned divided by simulated years. It is not a fire-return interval, so the pointer does not say "1 year in N."

Summed over every Tennessee cell whose center falls in the state, the probabilities come to about 23,400 acres a year under 2004–2018 weather and about 20,400 under 2040–2054 weather. That is a sum of cell probabilities, not the footprint of one fire. In the published county table, the mean falls in 75 of 95 counties. The largest falls are the eastern mountain counties. The rises are small and mostly in the west. The picture leaves LF2022 urban, agriculture, water, and barren dark, but those cells still hold about 1,800 acres a year of simulated probability from the 2020 landscape, and the acre total keeps them. A burnable-only sum is about 21,700 to 18,900 and the same 13% drop. The figures are rewritten into `meta.json` by the build script.

## What the model is

This is not a new fire-spread model. It is the Riley et al. 2025 FSim experiment, sampled onto a LANDFIRE grid:

- Both runs use a 2020 LANDFIRE landscape. Vegetation, fuels, and topography are not projected forward. The point of that design is to isolate climate.
- Recent weather is 2004–2018. The future run shifts temperature, relative humidity, and precipitation with the median of six CMIP5 RCP8.5 models (ACCESS1-3, CanESM2, GFDL-CM3, HadGEM2-CC, inmcm4, MPI-ESM-LR) to a 15-year period centered on 2047.
- Burn probability is the share of simulated years in which an FSim large fire burned the cell. It is not a fire-return interval and not a forecast of a particular fire.

The drawn fuel grid is LF2022 FBFM40. The LANDFIRE Product Service no longer serves LF2020 fuels. LF2022 is the closest fuel mosaic still on that service. Elevation and slope are LF2020, the topographic vintage in the FSim landscape. The national burn-probability grid is the same projection and cell size, with this extract's origin 30 m off the national origin. Probabilities are joined with nearest neighbor.

The threat stretch tops out at the 98th percentile of the 2047 probability on burnable cells, so a few hot cells do not flatten the rest. The hover uses the stored probability, not the stretch.

Checked against the source grids: nearest neighbor onto this extract matches sampling the national raster at the cell centers. The same 13% drop appears on the national grid with no resample. The state mask of cell centers is about 26.97 million acres, in line with the state's area. The county means are the authors' own table, `Data/CountyChange/county_change.csv`.

## Sources

- Riley, Zimmer, Kodra, Grenfell, Dillon, Scott, Jaffe, Olszewski, Vogler, Finney, Short, Jolly, Brittain, and Callahan, 2025, [doi:10.2737/RDS-2025-0006](https://doi.org/10.2737/RDS-2025-0006). `Data/2011ClimateRun/BP.tif` and `Data/2047ClimateRun/BP.tif`.
- LANDFIRE Product Service, LF2020 elevation and slope degrees, LF2022 Scott and Burgan 40. Scott and Burgan, 2005, RMRS-GTR-153.
- Tennessee State Geographic Information Systems Services, Hosted/TN_Counties.

## Output

- `2026/day-29/day-29.html` — the raster, with Fuels and Change beside Threat
- `2026/day-29/day-29.png` — threat, also the gallery still
- `2026/day-29/fuels.png`, `change.png` — the other two pictures
- `2026/day-29/values.png`, `recent.png` — cell values for the pointer
- `2026/day-29/meta.json` — statewide figures and fuel names
- `assets/2026/js/day29-raster.js`, `assets/2026/css/day29.css`
- `scripts/2026/build_day29_raster.py`

Rebuild from the repository root, after the raw files are cached:

```bash
python scripts/2026/build_day29_raster.py
```

The FSim archive and the LANDFIRE extract stay in `data/raw/day29/`, which is gitignored. A corporate proxy may need the local Zscaler CA on `SSL_CERT_FILE`. The Forest Service archive is on Box; HTTP/2 to that host can drop the handshake, and HTTP/1.1 succeeds.
