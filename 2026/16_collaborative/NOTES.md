# Day 16 — Collaborative map

**Date:** November 16, 2026
**Theme:** Collaborative map
**Working title:** Afghanistan's Konar Valley
**Tools:** Cesium, Esri World Elevation

## What this is

The source is a CIA Cartography Center sheet, 802538AI 11-01, November 2001: a 3D block of eastern Afghanistan titled "Afghanistan's Konar Valley." The collaboration is with that sheet. The page keeps the cut block and the oblique from the southwest, and draws the ground from modern elevation instead of the printed hillshade.

The scan is `2026/16_collaborative/2001-Afghanistan-Konar-Valley-3D.jpg`. The page is `2026/day-16.html`. The gallery embeds it.

Konar is the spelling on the sheet. Current maps usually spell the river and the province Kunar.

## The scene

Cesium runs from a CDN. The page does not use a Cesium ion token.

- Terrain is the Esri World Elevation Terrain3D image service.
- Satellite mode drapes Esri World Imagery.
- Relief mode drapes Esri World Hillshade. The elevation mesh has no slope normals to shade in the browser, so the hillshade is what makes the ridges read.
- The globe is clipped to about 68.5°E–72.15°E and 33.7°N–36.25°N. That covers Kabol and the near edge of the sheet, Peshawar on the east, and the high country of Nurestan and southern Badakhshan.
- Exaggeration starts at 1.8, measured from 900 m, so the valley floor stays put and the ridges rise. The slider runs from 1 to 3.
- The sheet camera looks north-northeast across the whole block. The valley camera looks up the Konar toward Asadabad. Keys: `1` sheet, `2` valley, `L` labels, `B` boundaries, `R` roads.
- The scale bar is ground distance along the terrain, not the exaggerated relief.

The gallery card pauses the render loop when the frame is off screen.

## Names

Town coordinates are published city locations. Province labels are placed in the province so they do not sit on the capital.

| Name on the sheet | Kind | Longitude | Latitude |
| --- | --- | ---: | ---: |
| Kabol | town | 69.1658 | 34.5328 |
| Jalalabad | town | 70.4478 | 34.4342 |
| Asadabad | town | 71.1528 | 34.8742 |
| Mehtar Lam | town | 70.2089 | 34.6683 |
| Peshawar | town | 71.5781 | 34.0153 |
| Konar | province | 71.00 | 35.08 |
| Nurestan | province | 70.72 | 35.35 |
| Nangarhar | province | 70.70 | 34.16 |
| Laghman | province | 70.02 | 34.80 |
| Badakhshan | province | 70.65 | 35.95 |

Labels start on. Boundaries and roads start off.

Boundaries are geoBoundaries lines, clipped to the block and saved as `boundaries.geojson`. The international line is Afghanistan's ADM0 edge. Province lines are ADM1 edges for Afghanistan and Pakistan. The sheet's own legend says the boundary representation is not necessarily authoritative. These lines are a current reference, not a trace of the 2001 drawing.

Roads are OpenStreetMap motorway, trunk, and primary ways inside the block, saved as `roads.geojson`. They are the main paved routes, including the Kabul–Jalalabad road and the road up the valley. They are not every track.

## Sources

- CIA Cartography Center, "Afghanistan's Konar Valley," 802538AI 11-01, November 2001.
- Esri World Elevation, Terrain3D. Sources include Airbus, USGS, NASA, NGA, and the GIS User Community.
- Esri World Imagery. Sources include Maxar, Airbus, USGS, and the GIS User Community.
- Esri World Hillshade, for the relief surface.
- Boundaries: geoBoundaries gbOpen, Afghanistan ADM0 and ADM1, Pakistan ADM1, CC BY 4.0. Runge and others, www.geoboundaries.org. Clipped to the block.
- Roads: © OpenStreetMap contributors, ODbL. Motorway, trunk, and primary, queried 2026-11-16.

Esri's services are called directly from the browser. Behind Zscaler, the elevation or imagery request can fail until the local certificate is trusted. Do not turn TLS verification off to get around that.
