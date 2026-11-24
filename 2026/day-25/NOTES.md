# Day 25 — Is this a map?

**Date:** November 25, 2026
**Map:** Hamilton County elevation, in a table
**Notion:** https://app.notion.com/p/422592b9f5818120a7b6da1f82613e5d
**Gallery:** `2026/day-25/day-25.html`

The map is a Notion table. Nothing in a mapping program drew it. This script only asks for elevations and writes the table markup.

Each cell is the USGS 3DEP elevation at the cell center, kept when that center is inside the Census TIGER outline of Hamilton County (GEOID 47065). Blank cells are outside the county. North is the first row. A cell is about 1.35 km on a side. The frame is 48.5 km east to west and 53.0 km north to south. 826 of the 1,404 cells fall inside the county.

Color is Notion's background swatches:

| Color | Feet |
| --- | --- |
| Blue | Below 700 |
| Green | 700–1,000 |
| Yellow | 1,000–1,400 |
| Orange | 1,400–1,800 |
| Red | 1,800–2,100 |
| Purple | Above 2,100 |

The only purple cell is Lookout Mountain, 2,116 feet. Walden's Ridge reaches 2,048 feet in the red cells on the northwest. Along the river the blue cells run from 634 to 699 feet. Moccasin Bend is 652, the Chickamauga Dam cell is 658, and downtown Chattanooga is 723. Missionary Ridge is narrower than a cell, so it does not separate from the valley.

The gallery page repeats the same cells so the card can show them. Those colors are stronger than Notion's own swatches. The Notion page is the map.

The page was created as a private draft. It is not on a shared parent.

Rebuild the markup and the gallery page from the repository root:

```text
python3 scripts/2026/build_day25_notion_terrain.py
python3 scripts/2026/build_day25_notion_terrain.py --markup-only
```

The first command downloads the county outline, if it is not already cached, and samples 3DEP again. The outline cache is `data/raw/day25_hamilton_county.geojson`, which is gitignored. `--markup-only` rewrites `notion-body.md` and `day-25.html` from `grid.json`. A corporate proxy may need the local Zscaler CA on `SSL_CERT_FILE`. Do not disable TLS verification.

## Files

| Piece | Where |
| --- | --- |
| Notion page | https://app.notion.com/p/422592b9f5818120a7b6da1f82613e5d |
| Gallery page | `2026/day-25/day-25.html` |
| Table markup | `2026/day-25/notion-body.md` |
| Cell values | `2026/day-25/grid.json` |
| Sampler | `scripts/2026/build_day25_notion_terrain.py` |

## Daily record

```text
Date: 2026-11-25
Theme: Is this a map?
Title: Hamilton County elevation, in a table
Concept: Terrain of Hamilton County drawn only as a Notion table
Data sources: USGS 3DEP; Census TIGER county outline, GEOID 47065
Software/tools: Notion. Python only collected the elevations.
Analysis: Bilinear 3DEP sample at each cell center inside the county
Cartographic technique: Six Notion background colors, north at the top
Time spent: Not tracked
What worked:
What I would change:
Post URL:
```
