# Year 5 GIS layers

Built by `python scripts/build_day12_power.py`. Everything here is EPSG:4326. Area fields were measured earlier, on a Ukraine Albers projection (standard parallels 46°N and 52°N, origin 48°N, 32°E, WGS84). Recomputing area from these vertices in Web Mercator will not match the fields.

Assessed control is the DeepStateMap occupied-area polygon, clipped to the geoBoundaries Ukraine outline. Link the source: https://deepstatemap.live/

## Files

| File | What it is |
| --- | --- |
| `gis/year5-power.gpkg` | All of the layers below, one GeoPackage. Git ignores `*.gpkg`. |
| `gis/ukraine.geojson` | Ukraine ADM0 |
| `gis/neighbors.geojson` | Natural Earth countries around Ukraine |
| `gis/claims.geojson` | Crimea, Sevastopol, Luhansk, Donetsk, Zaporizhzhia, Kherson |
| `gis/occupied.geojson` | One feature per assessment date. Use this for a time slider. |
| `gis/change.geojson` | Ground that changed relative to 24 February 2026 |
| `gis/gained.geojson` | `change` where `status` is `gained` |
| `gis/retaken.geojson` | `change` where `status` is `retaken` |
| `gis/cities.geojson` | City centers for labeling |
| `year5-the-claim-and-the-hold.geolibre.json` | GeoLibre project with the time slider bound to `assess_date` |

## Fields

`occupied`

| Field | Meaning |
| --- | --- |
| `assess_date` | Snapshot date, `YYYY-MM-DD` |
| `held_km2` | Assessed occupation inside Ukraine that day |
| `gained_km2` | Drawn area that passed to Russian control since 24 February 2026 |
| `retaken_km2` | Drawn area that passed back to Ukrainian control since that day |

`change`

| Field | Meaning |
| --- | --- |
| `assess_date` | Snapshot date |
| `status` | `gained` or `retaken` |
| `area_km2` | Drawn area of that status on that date, cumulative from 24 February 2026 |
| `baseline` | `2026-02-24` |

The change polygons are opened by 150 m, and pieces under 0.5 km² are dropped. A thin redraw of the line is left out. `occupied.held_km2` is the full clipped assessment, before that opening.

`claims`

| Field | Meaning |
| --- | --- |
| `name` | Claimed region |
| `shape_iso` | geoBoundaries ISO code |
| `area_km2` | Area of that geoBoundaries polygon |
| `held_start_km2` | Intersection with occupation on 24 February 2026 |
| `held_end_km2` | Intersection with occupation on the last snapshot |
| `held_start_pct` | Start share of the polygon |
| `held_end_pct` | End share of the polygon |

`held_end_pct` divides by the geoBoundaries polygon. The Autonomous Republic of Crimea polygon is about 41,700 km² and Sevastopol about 3,100 km², because those outlines include sea. The occupied assessment is the land polygon, so those two percentages are not the share of dry land. Look at the shapes before treating the leftover as unheld ground. Kherson, Zaporizhzhia, Donetsk, and Luhansk are closer to their land area.

## Suggested drawing order

1. Neighbors, then Ukraine
2. Claims, ochre
3. Occupation on the first day, or the `occupied` feature for one date, in a quiet stone
4. `retaken` in green, `gained` in clay, for the last date or for the active week
