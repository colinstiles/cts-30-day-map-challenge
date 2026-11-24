# Day 27 — New tool

**Date:** November 27, 2026
**Theme:** New tool
**Working title:** Middle Tennessee-Chickamauga, HUC 06020001
**Tools:** Python, USGS services, forge3d
**Script:** `scripts/2026/build_day27_forge.py`

## Setup

From the repository root, with the repo requirements and forge3d installed:

```text
python scripts/2026/build_day27_forge.py
```

`--refresh` ignores the cached watershed, NHD GeoJSON, and 3DEP GeoTIFF. `--frames` sets the orbit length (default 24). `--no-render` prepares the elevation grid and the water mask and skips forge3d.

forge3d needs a GPU. The script renders an offscreen orbit, then one larger still frame.

Behind Zscaler, trust the local corporate cert if HTTPS fails. Do not disable TLS for routine runs.

## What is drawn

The model is one USGS hydrologic unit, not a rectangle of terrain. HUC 06020001 is the Middle Tennessee-Chickamauga subbasin, about 4,827 km² in Alabama, Georgia, and Tennessee. North Chickamauga Creek, the Day 26 gorge, is inside this unit. Cells outside the watershed boundary are omitted.

Elevations are USGS 3DEP, bilinear, about 215 m. Lakes, reservoirs, and the NHD flowline network (perennial streams, artificial paths, and canals at least 1 km long) are burned into a mask. forge3d shades that mask as water. The basin is wider than forge3d's world limit, so the model is scaled down and the heights move with it. The shape is unchanged. The vertical scale is then exaggerated so the valley reads at the size of the basin. The amount is recorded in `bounds.json`.

The page plays the orbit and lets you drag to turn it. The still frame is the same model from the southwest.

## Sources

- Watershed: USGS Watershed Boundary Dataset, 8-digit hydrologic unit 06020001
- Elevation: USGS 3DEP Elevation ImageServer
- Hydrography: USGS National Hydrography Dataset, large-scale flowlines (layer 6) and waterbodies (layer 12)

## Outputs

- `2026/day-27/day-27.png` — still frame
- `2026/day-27/day-27.html` — orbit player
- `2026/day-27/frames/frame-NN.jpg` — orbit frames
- `2026/day-27/orbit.json` — frame count
- `2026/day-27/bounds.json` — frame, elevation range, exaggeration
- `data/raw/day27-huc-06020001.geojson` — cached boundary, gitignored
- `data/raw/day27-nhd-flowlines.geojson` — cached flowlines, gitignored
- `data/raw/day27-nhd-waterbodies.geojson` — cached waterbodies, gitignored
- `data/raw/day27-3dep-06020001.tif` — cached DEM, gitignored
- `data/processed/day27-water-mask.npy` — water mask, gitignored
