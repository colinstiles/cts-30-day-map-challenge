# Day 13 — Interactions

**Date:** November 13, 2026
**Theme:** Interactions
**Working title:** What the wars moved
**Tools:** MapLibre
**Basemap script:** `scripts/build_day13_basemap.py`

## Setup

From the repository root:

```text
python scripts/build_day13_basemap.py
```

The script reads Esri’s public World Basemap v2 style and writes `2026/13_interactions/human-geography-dark.json`. It keeps land, water, cities, roads, railways, and boundaries, and recolors them dark. The named ArcGIS Human Geography Dark style needs a token, so the page does not call that service. Re-run the script only to refresh the style. The frames themselves are `2026/13_interactions/episodes.json`.

Behind Zscaler, trust the local corporate certificate if the style download fails. Do not disable TLS for a routine run.

The page is `2026/day-13.html`. The gallery embeds it.

## What the frames do

Day 12 measured one war: the claim, the hold, and the ground that changed hands in Year 5. This map sets that war in a longer sequence. Each frame is an interaction of three things: where the fighting was, who was forced to move, and which border moved. The frame is cropped to that conflict, and the conflict’s name and years sit on the map.

The basemap is a present-day reference: dark land, water, cities, roads, and boundaries, from Portugal and Ireland to western Russia, Anatolia, and Cyprus. It includes states that did not exist in 1900. Esri draws Crimea with Russia. The line on the 2014 frame is this page’s mark for administration since 2014, and the claim against the hold stays on the Day 12 map.

- A **dashed line** is the border that the shift replaces.
- A **solid line** is the border that replaces it. Ochre is the Day 12 claim color, used where the new line is still widely unrecognized: the 1974 line on Cyprus, and the line across the neck of Crimea since 2014.
- **Teal arrows** are flight and expulsion. Width is the order of magnitude, on a square-root scale, so twelve million stays on the page beside a few hundred thousand. Marks travel the finished route, and a larger movement carries more of them.

Deportation and genocide stay off the arrow layer. The 1939–1945 frame says so. The arrows in the following frame are flight and expulsion.

The Ukraine frame draws the refugee total and the internal displacement, and it draws Crimea as de facto administration since 2014. It does not redraw the front. The four claimed oblasts, and the difference between claim and hold, stay on the Day 12 map.

The frames are the movements large enough to compare across the century, and the lines that moved with them. The century also holds the Irish partition, the Greek Civil War, and the Prague Spring.

The lines are simplified traces, not a cadastral survey. The Oder–Neisse line, the 1919 Franco-German border, the 1945 Polish border, and the 1944 Finnish border follow Natural Earth 50m. The 1871, 1937, 1921, inner German, 1974, and Crimean lines are drawn through the published turning points of those borders. When a frame opens, the old line and the new line draw on and flash together. Fighting extents are described in the frame text and are not painted.

## Dates

The slider is a sequence, not a year per step.

- 1912–1913 Balkan Wars
- 1914–1918 the continental war, and the Belgian flight
- 1918–1923 Alsace-Lorraine and the Lausanne exchange
- 1939 La Retirada
- 1939–1945 the second continental war
- 1944–1950 the postwar transfers and expulsions
- 1949–1961 the inner German border, before the Wall
- 1956 Budapest
- 1974 Cyprus
- 1991–1999 Yugoslavia and Kosovo
- 2014–2026 Ukraine, continuing Day 12

## Sources

Basemap: Esri World Basemap v2 vector tiles, restyled in `human-geography-dark.json`. Sources: Esri, TomTom, Garmin, FAO, NOAA, USGS, © OpenStreetMap contributors, and the GIS User Community. `europe.geojson` is an unused Natural Earth clip kept beside the frames. The ochre line is the administration of Crimea since 2014.

Magnitudes are published orders of magnitude. The page says “about” on purpose.

- Balkan Muslim flight, 1912–1914: hundreds of thousands. The arrow uses 400,000.
- Belgian flight, 1914: about 1.5 million, most of whom returned.
- Lausanne exchange, 1923: about 1.2 million Greek Orthodox people to Greece, and about 400,000 Muslims to Turkey.
- La Retirada, early 1939: nearly 500,000 people into France.
- German flight and expulsion, 1944–1950: about 12 million, from the provinces east of the Oder–Neisse line and from the rest of eastern Europe.
- Poles resettled from the annexed east: about 1.5 million.
- Finnish ceded districts: about 420,000 people, most of them from Karelia.
- Istrian-Dalmatian exodus: about 250,000, inside a published range that reaches about 350,000.
- German Democratic Republic to the Federal Republic, 1949 to August 1961: about 2.7 million.
- Hungary, 1956: about 200,000. UNHCR’s historical figure.
- Cyprus, 1974: about 160,000 Greek Cypriots moved south and about 45,000 Turkish Cypriots moved north.
- Bosnia and Herzegovina: about 2.2 million people displaced. The figure used by UNHCR.
- Kosovo, spring 1999: more than 800,000 refugees. UNHCR. Most returned the same year.
- Ukraine: UNHCR’s Europe briefing to the 77th Executive Committee (October 2026) records 5.7 million refugees from Ukraine worldwide by mid-2026, about 5.2 million of them in Europe. IOM counted 3.7 million internally displaced at the end of 2025, as cited in UNHCR’s Europe situation note for that year.

Assessed control inside Ukraine is Day 12, from DeepStateMap assessments. This page links that map and does not copy its weekly polygons.
