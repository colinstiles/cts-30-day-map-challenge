# Day 7 — 10 Minute Map

**Date:** November 7, 2026  
**Theme:** 10 minute map  
**Working title:** Chimney Tops 2 — Sevier County pixel fire (2016)  
**Tools:** HTML5 canvas (no MapLibre), vanilla JS  
**Gallery:** `2026/day-07.html` (embed in `days-data.js`)

## Rule

Build in **≤ 10 minutes**. Stop. Do not polish afterward.  
Badge on the map: **Built in 1 minute and 1 second** (timed dummy rebuild via timeapi.io).

## Why pixelated

- 64×40 cell grid, nearest-neighbor upscale → fast to code and to paint
- No tile basemap, no Pro export, no video encode in the timebox
- Reads as intentional style, not an unfinished render

## Map layers (canvas)

1. **Terrain** — ridged elevation field (Smokies massif south, valley north) with dither
2. **Cities** — schematic rings + light urban fill for Gatlinburg, Pigeon Forge, Sevierville
3. **Fire** — cellular spread; acreage callout = burned cells × cell area (~acres)

## Data

InFORM Fire Occurrence (Sevier County, Nov–Dec 2016) ignition seeds:

| Incident | Discovery (approx) | Lon | Lat | Size (ac) |
| --- | --- | --- | --- | ---: |
| Chimney Tops | 2016-11-13 | -83.4781 | 35.6286 | 0.3 |
| Chimney Tops 2 | 2016-11-23 | -83.4778 | 35.6308 | 17140 |
| Cobbly Nob | 2016-11-28 | -83.3431 | 35.7700 | 767 |

Spread is **stylized** (wind-biased cellular growth with a Nov 28 blow-up), not WFIGS official daily perimeters. Credit that on the map.

## Files

| Path | Role |
| --- | --- |
| `2026/day-07.html` | Page / gallery embed |
| `assets/js/day07-pixel-fire.js` | Pixel sim + UI |
| `assets/css/day07.css` | Pixel HUD styling |

## Deliverable

Interactive embed `2026/day-07.html` (no raster export required).
