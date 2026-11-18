# Day 15 — Inside out

**Date:** November 15, 2026
**Theme:** Inside out
**Working title:** North Chickamauga Creek Gorge, turned over
**Tools:** Python (`numpy`, `matplotlib`, `shapely`), USGS 3DEP, optional `forge3d`
**Script:** `scripts/build_day15_inside_out.py`

## Setup

From the repository root, with the repo requirements installed:

```text
python scripts/build_day15_inside_out.py
```

`--refresh` ignores the cached park polygon and the 3DEP GeoTIFF. `--no-forge` skips the path-traced plate. `--samples` sets forge3d samples per pixel (default 4).

forge3d is optional. When it imports and a GPU is available, the script also writes `data/processed/day15-forge3d.png`. The gallery sheet is the matplotlib relief, so the model, the plan, and the legend share one ramp.

Behind Zscaler, trust the local corporate cert if HTTPS fails. Do not disable TLS for routine runs.

## What is turned over

The frame is the TDEC state-park polygon TSP-0322, North Chickamauga Creek Gorge State Park, plus 450 m. Elevations are USGS 3DEP, bilinear, near 15 m.

Inside the park, the samples are reflected through their midpoint:

```text
inverted = highest + lowest - elevation
```

The creek bottom becomes the crest. The rims become the trough. The range in meters is unchanged. Ground outside the polygon is reflected with the same two numbers, so the pad does not invent a second datum.

The plan inset is that same surface, north up, with the park outline. The oblique view exaggerates the vertical until it is about two-fifths of the width, and never more than 6×. Light is from the northwest.

The legend numbers are the original elevations. The light crest is the creek bottom. The dark trough is the rim.

## Sources

- Boundary: TDEC State Park Boundaries Primary, March 2024, feature service layer 331, `TSP_UID = TSP-0322`
- Elevation: USGS 3DEP Elevation ImageServer
- Park page: https://tnstateparks.com/parks/north-chickamauga

## Outputs

- `2026/images/day-15.png` — gallery sheet, 12×9 in at 200 dpi
- `2026/15_inside_out/bounds.json` — frame, elevation range, exaggeration, renderer
- `data/raw/day15-north-chickamauga-park.geojson` — cached boundary, gitignored
- `data/raw/day15-3dep-north-chickamauga.tif` — cached DEM, gitignored
- `data/processed/day15-forge3d.png` — path-traced plate, only when forge3d renders
