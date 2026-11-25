# Day 28 — Feeling

**Date:** November 28, 2026
**Theme:** Senses: Feeling
**Title:** The north face gives way
**Tools:** Three.js

## What is drawn

`day-28.html` is an oblique view of a real elevation model, not footage and not a hazard map. The film opens on the north face of Langtang Lirung. Once the flood leaves the glacier, the camera follows it downstream from behind.

The surface is AWS Terrain tiles at zoom 13, mostly SRTM, draped with Esri World Imagery. Closed pits are filled so the valley drains. Vertical scale is 1.15. The mesh is finer than the flood grid. The flood's path is routed on a 53 m grid. The drawn surface uses that path, at the reported wave height, on the finer terrain.

The water surface is 250 m above a smoothed channel bed, the middle of the 200–300 m wave observers reported at the border. Where the valley floor is below that surface, and the routed flood has reached it, the mesh is lifted to the surface. The surface is smooth. It is not a surveyed water level, and another reconstruction put the wave nearer 130 m. The routing itself is a 2D diffusive-wave model. Flux follows Manning's equation on the water-surface slope, with n = 0.045 and a speed cap of 32 m/s. A step cannot overshoot a level surface, and a cell cannot give away more water than it holds. Water stays in the drainage that passes Rasuwagadhi, so neighboring basins do not catch it. The simulated reach ends at the crossing. The release is 28 m of water on the cells within 900 m of the ice tongue, between 4,700 m and 5,900 m. That is about 2 km² and about 54 million m³. It is an assumption, not a measured volume. The drawn height is that reported wave, not the model's own depth. The routing reaches Rasuwagadhi later than the reported 7–8 minutes. The film uses the reported clock, not the model's travel time.

The sequence:

1. Slope failure on the face near 5,200 m, shown as the flood leaving the release.
2. Impact on the glacier, drawn as the energy of an M5.2 earthquake. The signal is the collapse, at 08:37.
3. Debris flow and flood down the valley. The path is the routing. The height is the reported wave.
4. Destruction at Rasuwagadhi. The bridge and the buildings mark the crossing. They are not a surveyed footprint. The film uses about 08:45, from NDRRMA, once the simulated water has reached the bridge.

The locator draws the valley drainage from the release to the crossing, traced on this elevation model. The run of about 100 km down the Bhotekoshi and Trishuli stays in the caption. That reach is not on this elevation model.

The M4.2 signal three hours later is a caption only. Published locations for that second signal do not agree, so it is not drawn as another impact in this valley.

## Sources

- USGS Landslide Hazards Program, “2026 Nepal Debris Avalanche and Flash Flood,” preliminary page, last update 28 August 2026. The user’s paste of that page is `notes.txt`. The USGS extent map is `nepal5.png`.
- Government of Nepal, NDRRMA, “Bhotekoshi–Trishuli Flood: Search, Rescue and Relief Update,” reporting period 26 August–3 October 2026. Used for the fall from about 5,200 m onto the Lhende Glacier at about 3,800 m, the 08:37 seismic time, the about 08:45 arrival at Rasuwagadhi, and the observer report of a wave about 200–300 m high.
- Langtang Lirung summit elevation, 7,227 m, is the surveyed height of the peak, not a measurement from this event.

USGS spells the river Lende. NDRRMA and several scientific notes spell it Lhende. The page uses Lende and says so.

This mountain also produced a large debris avalanche in 2015. That event is not in the animation.

## Output

- `2026/day-28/day-28.html` — the view
- `assets/2026/js/day28-valley.js` — the Three.js film
- `2026/day-28/terrain.bin` — float32 elevations, row 0 north
- `2026/day-28/flow.bin` — uint8 depth frames, meters = value × `depth_scale_m`
- `2026/day-28/imagery.jpg` — draped imagery
- `2026/day-28/bounds.json` — grid, places, and model notes
- `scripts/2026/build_day28_valley.py` — rebuilds the grids

Rebuild from the repository root:

```bash
python scripts/2026/build_day28_valley.py
```

Tiles are cached in `data/raw/day28/`, which is gitignored. A corporate proxy may need the local Zscaler CA on `SSL_CERT_FILE`.
