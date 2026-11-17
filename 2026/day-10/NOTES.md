# Day 10 — Prompting only

**Date:** November 10, 2026  
**Theme:** Prompting only  
**Map:** Vael: The Crescent Sea  
**Datum:** VAEL:2026 (sphere, R = 1,250,000 m)

No Earth coastline, DEM, gazetteer, or basemap was used. Plate carrée is the drawing on this sheet. It is not the datum.

## Prompt chain

### Prompt 1 — Colin, day brief

Work the Day 10 map from the 2026 plan. Theme: Prompting only. Use AI from start to finish, purely through prompting, to invent an entirely fictional place or world. No real-world data. Document the prompt chain beside the result. The world is also the base for Day 22, so keep a coordinate system, extent, and coastline geometry in a reusable form. Static, interactive, or both.

### Prompt 2 — working prompt, invent the world

Invent one ocean world, not a copy of Earth. Name it Vael. Radius 1,250 km, a sphere. Longitude 0 is the meridian of Cape Orro. Latitude 0 crosses an inland sea. Chart only the inhabited sheet: one crescent continent (Cairn) wrapped around that sea (the Glass Mere), open to the east through a strait (the Narrows), a northern plateau with a crater lake (Merrin), a western mountain arc (the Pale Spine), and a volcanic island arc to the southeast (the Cinder Chain). Three polities: Orro Reach on the highlands and cape, the Mere Compact around the inland sea, the Cinder League on the islands. Place names, borders, rivers, and terrain must come from this description and a fixed seed (20261110). Do not import Earth coastlines, DEMs, or place names.

### Prompt 3 — working prompt, draw it and file the geometry

Turn that description into a deterministic elevation field and extract coastline, realm, river, and place geometry. Publish the sheet as a plate carrée chart, labeled as a display choice rather than the datum. Write VAEL:2026 (sphere, R = 1,250,000 m), the mapped extent, and GeoJSON in Vael degrees for Day 22. Keep the generator and the geometry in the repo so the projection day can reuse them without redrawing.

## What that produced

| Piece | Where |
| --- | --- |
| Chart, pan and zoom | `2026/day-10.html` |
| Print frame | `2026/day-10.html?still=1` (1800×1350 canvas) |
| Generator | `assets/js/vael-world.js` |
| Datum and extent | `2026/10_prompting/vael-frame.json` |
| Coastline, realms, rivers, places | `2026/10_prompting/vael.geojson` |

`vael.geojson` carries a `crs_vael` member and a notice. Coordinates are degrees of longitude and latitude on the Vael sphere. Do not plot them as WGS84.

Rebuild after any change to the generator:

```text
node scripts/day10_vael_export.js
```

`--ascii` prints a text chart before the audit.

## Datum notes for Day 22

- Sphere, a = b = 1,250,000 m. One degree of latitude is about 21.82 km.
- Prime meridian: Cape Orro, published as longitude 0. Not Greenwich.
- Equator: crosses the Glass Mere.
- Mapped extent: the `mappedExtent` object in `vael-frame.json`.
- Shorelines are `kind: "shoreline"` LineStrings. Land polygons use the same rings, with lakes and the mere as holes where the tracer found them.
- Seed `20261110` and `designShift` in the frame file freeze the meridian. Do not recompute the shift from the coastline or the longitudes will move.
