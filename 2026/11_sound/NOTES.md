# Day 11 — Senses: Sound

**Date:** November 11, 2026
**Theme:** Senses: Sound
**Working title:** Where the guns were heard
**Tools:** Python (`numpy`, `matplotlib`, `shapely`), Leaflet
**Script:** `scripts/build_day11_sound.py`

## Setup

From the repository root:

```text
pip install -r requirements.txt
python scripts/build_day11_sound.py
```

`shapely` comes in with `geopandas`. `--refresh` ignores the cached boundary, cemetery, city node, 3DEP GeoTIFF, and audibility grid.

Behind Zscaler, trust the local corporate cert if HTTPS fails. Do not disable TLS for routine runs.

## What the color means

Three washes, one for each battle. Where they overlap, the color mixes. The value is a relative reach from 0 to 1. It is not a decibel, a contour, or a measured sound level.

On open ground the proxy is 1 beside the gun, 0.60 at 10 miles, and 0 at 15 miles. Ten miles is the open-ground reference because Chickamauga's guns were heard in Chattanooga, on the order of ten miles away. Fifteen miles is the outer fade used for this sheet.

Terrain above the straight path multiplies that fade. Each 90 m of ridge above the path leaves about a third of the proxy (`exp(-height / 90)`). Lookout, hundreds of meters above the river, nearly silences the far side. A lower ridge reduces the reach without erasing it. Earth curvature is included. Atmospheric refraction is not: cannon sound ducts with the weather, and this map does not model that.

The profile is sampled on a grid of about 80 by 100 m. A rise narrower than that can be missed. These ridges are not that narrow.

## Decibel sheet

`2026/images/day-11-decibels.png` is the same ground and the same three points, scored as one-shot sound exposure.

0 dB is open ground at 10 miles, the distance at which Chickamauga was heard in the city. That dashed ring is the audibility contour used here. Closer than 10 miles the level rises 6 dB each time the distance is cut in half. Farther out it keeps falling. There is no hard stop at 15 miles.

Air absorption is 0.1 dB per kilometer, the order of magnitude in ISO 9613-1 near 63 Hz, 20 °C, and 70% humidity. The boom is treated as that one low frequency, not a summed spectrum.

A ridge is one knife edge: the extra path length over the highest point on the curved-earth chord, turned into a Fresnel number, then `10 log10(3 + 20N)` decibels. The loss is capped at 20 dB, the single-diffraction limit in ISO 9613-2. A bump under half a meter is ignored.

The wash drops out at -12 dB and is solid at +18 dB and above. Weather refraction is still absent. The numbers are not a measurement of an 1863 gun.

## Representative points

Each point is one published place standing in for a field of fire. The script snaps it to the nearest 3DEP cell, about 40 m across. The built coordinates and elevations are in `bounds.json`. These are not a survey of every battery.

| Battle | Published position | Anchor (lat, lon) |
| --- | --- | --- |
| Chickamauga, Sept 19–20, 1863 | Brotherton House, the breakthrough on the LaFayette Road (GNIS) | 34.91785, -85.26079 |
| Lookout Mountain, Nov 24, 1863 | Corput's Georgia Battery on the Point, 2 p.m. (1890 commission tablet, 35° 0.686′ N, 85° 20.658′ W) | 35.01143, -85.34430 |
| Missionary Ridge, Nov 25, 1863 | Bragg's headquarters, Bragg Reservation, center of the line (1909 tablet, 35° 1.161′ N, 85° 15.787′ W) | 35.01935, -85.26312 |

An earlier build put Missionary Ridge on the largest ridge reservation, at the north end near Tunnel Hill (about 35.069, -85.241). That is Sherman's attack, which was stopped. The guns that faced the city, and the line Thomas broke, were at the center. Lookout was already within about 200 m of Corput's battery; it is now on that tablet. Chickamauga was the centroid of the park unit, about 0.4 miles east of the Brotherton House, and is now on the house.

On November 24 the Confederate guns on the mountain were Corput's four Napoleons on the Point. Union artillery fired from below the mountain and did not climb it. Chickamauga's guns were spread across the field; the house marks the center of the fighting, not one battery. Missionary Ridge had about nine batteries along the crest; the point is the center of that line.

Downtown is on the order of nine miles from the Brotherton House, and the cemetery is a little closer. The script prints both distances. A straight path from the house toward downtown crosses the south end of Missionary Ridge, so the Chickamauga wash is fainter in the city than on open ground at the same distance. Guns farther north on the field, and sound through Rossville Gap, are not separate sources.

Lookout still cuts the reach on its far side. The script prints the proxy seven kilometers west of the Point and the same distance toward the city.

## Dates

Checked against the battle days and Thomas's cemetery order:

- Chickamauga, September 19–20, 1863. September 18 was the approach. The sheet keeps the two battle days.
- Lookout Mountain, November 24, 1863.
- Missionary Ridge, November 25, 1863. Orchard Knob was November 23. The order below also names November 26 and 27, the pursuit. Those days are not separate sources on this sheet.
- Chattanooga National Cemetery: General Orders No. 296, Headquarters, Department of the Cumberland, December 25, 1863, Maj. Gen. George H. Thomas. The grounds were chosen a few days after the battles. The War Department designated it a national cemetery in 1867. The sheet says established December 25, 1863.
- The sheet is dated Veterans Day, November 11, 2026.

## Sheet

The gallery raster is a portrait tabloid, 11 by 17 inches, at 150 dpi (1650 by 2550 pixels). Type is Bookman Old Style, Alexander Phemister's 1860 oldstyle, from the Windows faces `BOOKOS.TTF`, `BOOKOSB.TTF`, `BOOKOSI.TTF`, and `BOOKOSBI.TTF`.

The ground is Esri World Imagery draped on the 3DEP hillshade. Only two boundaries are drawn: the main Chickamauga battlefield unit and Chattanooga National Cemetery. A north arrow and a 10-mile scale bar sit in the southwest corner. Place names are offset from their dots so the cemetery name, the city, and Missionary Ridge do not share a line.

## Outputs

- `2026/images/day-11.png` — gallery sheet, 11×17 in
- `2026/images/day-11-decibels.png` — same sheet, one-shot exposure in decibels
- `2026/day-11.html` — local interactive toggles, not linked from the gallery
- `2026/11_sound/audibility-*.png` — transparent washes for the page
- `2026/11_sound/bounds.json` — extent, distances, source points
- `2026/11_sound/places.geojson` — park units, cemetery, city, sources
- `data/raw/day11-3dep.tif` — USGS 3DEP cache (gitignored)
- `data/raw/day11_chch_boundary.geojson` — NPS boundary cache (gitignored)
- `data/processed/day11_audibility.npz` — coarse reach grids (gitignored)

Distances use a local equirectangular scale in EPSG:4326 at the map center. That is accurate enough for this proxy. It is not a survey.

## Sources

- NPS Land Resources Division boundary, Chickamauga and Chattanooga National Military Park (`UNIT_CODE` CHCH)
- USGS 3DEP ImageServer
- OpenStreetMap: Chattanooga National Cemetery and the Chattanooga place node
- Esri World Imagery on the sheet, draped on the hillshade; Esri World Topo Map on the interactive page

Chattanooga National Cemetery was established by Gen. George H. Thomas on December 25, 1863, for the Union dead of the battles around the city. It became a national cemetery in 1867.

## Daily record

```text
Date: 2026-11-11
Theme: Senses: Sound
Title: Where the guns were heard
Concept: Terrain-shadowed audible reach of Chickamauga, Lookout Mountain, and Missionary Ridge over modern Chattanooga
Data sources: NPS CHCH boundary; USGS 3DEP; OpenStreetMap cemetery and city; Esri World Imagery
Software/tools: Python (numpy, matplotlib, shapely), Leaflet
Analysis: Distance fade to 15 miles, times an exponential ridge penalty. Not a decibel model.
Cartographic technique: Imagery draped on a 3DEP hillshade, three washes, 10-mile ring, north arrow, scale bar
Time spent: Not tracked
What worked:
What I would change:
Post URL:
```
