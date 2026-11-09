# 30-Day Map Challenge 2026 — Master Plan

**Challenge:** #30DayMapChallenge 2026  
**Dates:** November 1–30, 2026  
**Tools:** ArcGIS Pro, Python, AGOL, GeoLibre, Sketchfab, Blender, Cesium, kepler.gl, JavaScript, CSS, HTML  
**Geographic emphasis:** Tennessee, Southeast US, forestry, water, landscape, infrastructure, planetary  
**Planning approach:** Favor original, visually strong maps that also let me experiment with cartography, analysis, and new tools.

> The official 2026 themes are listed by the 30DayMapChallenge site. The challenge is tool-agnostic, allows maps to be prepared in advance, and encourages creativity and learning rather than competition. Day 10 is specifically intended for an AI-only workflow.  
> Source: https://30daymapchallenge.com/2026/

## Expected Effort Scale

| Expected effort | Meaning |
|---|---|
| **Low** | Roughly 10–60 minutes; straightforward GIS/cartographic work |
| **Moderate** | Roughly 1–2 hours; some analysis, data preparation, or design iteration |
| **High** | Roughly 2–4 hours; substantial analysis, research, or cartographic refinement |

---

## 30 Days of Maps

| Day | Date | Official Theme | Primary Concept | Expected Effort |
|---:|---|---|---|---|
| 1 | Nov 1 | Points | Cave locations on Mars Astro Tharsis | Moderate |
| 2 | Nov 2 | Lines | Cumberland Trail and Contour lines | Moderate |
| 3 | Nov 3 | Polygons | Descending watersheds, from HUC2 down to HUC12 | Low |
| 4 | Nov 4 | Clusters | Tennessee InFORM fire-incident hotspot timelapse | High |
| 5 | Nov 5 | Senses: Sight | View from the Cherokee Fire Tower | High |
| 6 | Nov 6 | Vintage | Chattanooga then & now: historic topo swipe map | Moderate |
| 7 | Nov 7 | 10 minute map | Pixel animation of 2016 Chimney Tops 2 (Sevier Co.), built in ≤10 minutes with on-screen build stamp | Moderate |
| 8 | Nov 8 | Utopia | Tallulah / Tugalo undammed — Lake Tugalo drained | High |
| 9 | Nov 9 | Urban-rural | Wildland-Urban Interface in Tennessee | Moderate |
| 10 | Nov 10 | Prompting only | AI creates a fictional place/world from scratch, purely via prompting | Moderate |
| 11 | Nov 11 | Senses: Sound | Interstate high-sound corridors through Chattanooga | Moderate |
| 12 | Nov 12 | Power | Incan/Aztec controlled areas throughout time | Moderate |
| 13 | Nov 13 | Interactions | Emerald Ash Borer spread along Tennessee's interstate corridors | High |
| 14 | Nov 14 | Borgesian map | Map of a single tree | Low |
| 15 | Nov 15 | Inside out | North Chickamauga Creek Gorge: inverted terrain + inverted forest/developed figure-ground | Moderate |
| 16 | Nov 16 | Collaborative map | Declassified CIA map of Konar Valley, Afghanistan | Moderate |
| 17 | Nov 17 | Light & dark | Sri Chinmoy Self-Transcendence Race | Moderate |
| 18 | Nov 18 | NULL | 1994 Marathon des Sables, Mauro Prosperi gets blown 291km off course | Moderate |
| 19 | Nov 19 | Senses: Smell | Distribution of Ponderosa Pine | Moderate |
| 20 | Nov 20 | Hexagons | Wildfire Potential Hazard | Moderate |
| 21 | Nov 21 | OpenStreetMap | Per capita choropleth of countries that contribute to OSM | Moderate |
| 22 | Nov 22 | Projections | A new projection built for Day 10's fictional world | Moderate |
| 23 | Nov 23 | Senses: Taste | Tennessee agriculture/food distribution to globe | Moderate |
| 24 | Nov 24 | Network | Flow of crypto funds throughout the world | High |
| 25 | Nov 25 | Is this a map? | Make a map in a non-mapping software (pandas dataframe, Notion, etc.) | High |
| 26 | Nov 26 | Water | Watershed of North Chick Creek Gorge | High |
| 27 | Nov 27 | New tool | something made in Sketchfab | High |
| 28 | Nov 28 | Senses: Feeling | 3D hydro model of recent flooding in Nepal | High |
| 29 | Nov 29 | Raster | Wildfire Suppression Difficulty Index | Moderate |
| 30 | Nov 30 | Pen & paper | Hand-drawn with my left hand | Low |

---

# Daily Plan

## Day 1 — Points
**Date:** November 1  
**Concept:** Mars Caves
**Tools:** ArcGIS Pro; Python; JavaScript

### Map ideas
- **Caves on Mars** — cave point locations on Mars Astro Tharsis

### Hyperlink
- [USGS Mars Caves](https://www.usgs.gov/news/caves-mars)

### Data Source
- Mars Global Cave Candidate Catalog (MGC3)

**Expected effort:** **Moderate**

---

## Day 2 — Lines
**Date:** November 2  
**Concept:** Cumberland Trail Contours
**Tools:** ArcGIS Pro

### Map ideas
- **Cumberland Contours** - contour lines surrounding Cumber land Trail system in eastern Tennessee

### Hyperlink
- [USGS Preliminary Contours](https://www.usgs.gov/coastal-changes-and-impacts/contour-preliminary-contour-data)
- [TREC](https://experience.arcgis.com/experience/0ef2687be56940408d73ced2dfc170b6)

### Data Source
- Tennessee State Parks trail GIS data (TREC)
- USGS preliminary contours

**Expected effort:** **Low**

---

## Day 3 — Polygons
**Date:** November 3  
**Concept:** Tennessee Watersheds, HUC2 to HUC12
**Tool:** ArcGIS Pro

### Map ideas
- A nested polygon map descending from HUC2 region down through HUC12 subwatersheds with layered hillshade.

### Hyperlink
- [USGS Watershed Boundary Dataset](https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/Hydrography/WBD/National/GDB/)

### Data Source
- USGS Watershed Boundary Dataset (WBD), HUC2 through HUC12

**Expected effort:** **Low**

---

## Day 4 — Clusters
**Date:** November 4  
**Concept:** Tennessee fire incident hotspots (InFORM timelapse)
**Tools:** MapLibre GL JS; NIFC InFORM Fire Occurrence feature service

### Map ideas
1. A sliding-window heatmap of InFORM wildfire and prescribed-fire ignitions in Tennessee.
2. A kernel-density view of where incident locations cluster, animated through time.
3. Toggle between 2021–present (more complete reporting) and the full 1992–present record.

### Data source
- [InFORM Fire Occurrence Public](https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/InFORM_FireOccurrence_Public/FeatureServer) (NIFC / IRWIN), layer 0 Incidents
- Filter: wildfire (`WF`) and prescribed fire (`RX`) with a Tennessee point of origin
- Interactive map: `2026/day-04.html`

**Expected effort:** **High**

---

## Day 5 — Senses: Sight
**Date:** November 5  
**Concept:** View from the Pinnacle Mountain Fire Tower
**Tools:** Three.js, OrbitControls

The observer is Pinnacle Mountain Fire Tower on Buffalo Mountain, Cherokee National Forest, at 36.21712°N, 82.37060°W. An earlier coordinate, 36.20845°N 82.38204°W, sits about 1.4 km downslope of the lookout.

### Map ideas
- A 3D pull-back and orbit from the fire tower's platform with viewshed draped on terrain.

### Data source
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)

**Expected effort:** **High**

---

## Day 6 — Vintage
**Date:** November 6  
**Concept:** Chattanooga Then & Now — Historic Topo Swipe Map
**Tools:** Leaflet, USGS Historical Topographic Map Collection, Esri World Street Map

### Map ideas
- Swipe between a scanned 1940 USGS Chattanooga topographic sheet and a modern streets-and-places basemap.
- Keep the historic sheet geographically aligned, so roads, water, and ridges can be compared directly.
- Use a simple draggable divider that works in both the gallery embed and the full-page map.

Working notes: `2026/06_vintage/NOTES.md`.

### Data source
- [topoView](https://ngmdb.usgs.gov/topoview/viewer/)
- [Esri Streets](https://www.arcgis.com/home/item.html?id=e833fc01f447451f93ec0dfdfe12eed7#overview)

**Expected effort:** **Moderate**

---

## Day 7 — 10 Minute Map
**Date:** November 7  
**Concept:** Pixel Chimney Tops 2 Animation (Sevier County, 2016)  
**Tools:** HTML5 canvas / vanilla JS (`2026/day-07.html`)

### Map ideas
- A coarse **pixel-grid** animation of the 2016 Great Smoky Mountains / Chimney Tops 2 complex in Sevier County.
- Seed ignitions from NIFC InFORM (Chimney Tops, Chimney Tops 2, Cobbly Nob); stylized cellular spread with a Nov 28 blow-up toward Gatlinburg.

### Rule
Set a timer for **10 minutes** and stop. Do not polish afterward. The stamped build time is the proof. Pixel style keeps rendering cheap inside the timebox.

Working notes: `2026/07_10_minute/NOTES.md`.

### Data source
- [InFORM Fire Occurrence Public](https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/InFORM_FireOccurrence_Public/FeatureServer) (NIFC / IRWIN), layer 0 Incidents

**Expected effort:** **Moderate** (hard cap: 10 minutes of build time)

---

## Day 8 — Utopia
**Date:** November 8  
**Concept:** Tugalo Undammed — Lake Tugalo drained, Tallulah–Chattooga confluence restored  
**Focus point:** Georgia Power Tugalo plant `34.71396, -83.35183`  
**Tools:** Python (`py3dep` / rasterio) for utopia DEM; Leaflet (or MapLibre) swipe embed — same family as Day 6

### Map ideas
- **Now vs utopia swipe:** left = present Lake Tugalo + dam; right = reservoir removed and free-flowing rivers restored.

**How to build the utopia terrain**
1. Pull 3DEP DEM + hillshade for a bbox around Lake Tugalo / Tugalo Dam.
2. Mask the reservoir waterbody (NHD/OSM/GA hydro).
3. **Carve a restored valley** under the pool: interpolate a thalweg from upstream Tallulah + Chattooga inlets down to the dam toe (use published pre-dam long-profile cues where helpful — e.g. Wenger 2022 on lower Chattooga before Tugalo), then blend side-slopes from the surrounding DEM so the “drained” surface looks like a gorge, not a flat hole.
4. Draw free-flowing centerlines (Tallulah, Chattooga → Tugaloo) on the utopia side; keep dam + blue pool on the now side.
5. Soft labels: Tugalo Dam, Lake Tugalo, Tallulah R., Chattooga R., GA / SC if the frame needs it.
6. Title that states the wish plainly — e.g. “Utopia: Tugalo Undammed.”

### Data source
- USGS 3DEP DEM / hillshade  
- Reservoir footprint (NHD Waterbody, OSM, or Georgia Power/FERC project materials)   

Working notes: `2026/08_utopia/NOTES.md`.

**Expected effort:** **High**

---

## Day 9 — Urban-rural
**Date:** November 9  
**Concept:** **Tennessee's Wildland-Urban Interface**

### Map ideas
1. A statewide WUI classification map (interface, intermix, non-WUI).
2. WUI growth/change over time, if historical data is available.
3. WUI overlaid with wildfire risk or forest cover.

### Recommended direction
Use the standard WUI classification (interface vs. intermix) rather than a generic urban/rural gradient — this connects directly to forestry and wildfire-risk work.

### Potential data
- USFS / SILVIS Wildland-Urban Interface datasets

**Expected effort:** **Moderate**

---

## Day 10 — Prompting Only
**Date:** November 10  
**Concept:** **AI Creates a Fictional World From Scratch**

### Experiment
Use AI from start to finish, purely through prompting, to invent an entirely fictional place — or an entire fictional world — with no real-world data involved. Document the prompt chain alongside the result.

### Possible challenge
Prompt an AI to generate the geography, coastlines, terrain, place names, and political boundaries of a world that doesn't exist, then execute whatever workflow it proposes (scripted procedural generation, a drawn/rendered map, etc.) with minimal manual intervention.

### Recommended direction
Treat this as a two-day arc: the fictional world built here becomes the basis for Day 22's custom map projection, so keep whatever geographic data or geometry comes out of this day (coordinate system, extent, coastline geometry) in a reusable form.

### Technical opportunity
- Procedural/fictional terrain or coastline generation via AI-authored code
- A defined (even if informal) coordinate reference frame for the fictional world, to carry into Day 22

**Expected effort:** **Moderate**

---

## Day 11 — Senses: Sound
**Date:** November 11  
**Concept:** **High-Sound Interstate Corridors in Chattanooga**

### Map ideas
1. Interstate corridors through Chattanooga styled or ranked by estimated traffic noise.
2. Buffer zones around interstates showing noise falloff distance.
3. Overlay noise corridors with neighborhoods or land use to show exposure.

### Recommended direction
Focus specifically on Chattanooga's interstate network (I-24 / I-75 / I-59) and model or symbolize relative noise intensity along those corridors, rather than a generic statewide soundscape.

### Potential data
- FHWA traffic volume data
- TDOT interstate network
- Noise modeling approximations (distance/volume-based proxy if no modeled noise data exists)

**Expected effort:** **Moderate**

---

## Day 12 — Power
**Date:** November 12  
**Concept:** **Incan and Aztec Territorial Power Over Time**

### Map ideas
1. Small multiples or an animated sequence showing Incan empire extent over time.
2. The same treatment for Aztec-controlled territory.
3. A side-by-side comparison of both empires at their peak extents.

### Recommended direction
This is a historical-boundary mapping exercise, not an infrastructure map. Focus on sourcing credible historical extent data and showing change over time clearly through small multiples or animation.

### Potential data
- Published historical GIS boundary compilations for Incan and Aztec territorial extent

**Expected effort:** **Moderate**

---

## Day 13 — Interactions
**Date:** November 13  
**Concept:** **Emerald Ash Borer Spread Along Tennessee's Interstate Corridors**

### Map ideas
1. Emerald Ash Borer (EAB) detection locations over time, layered against Tennessee's interstate network.
2. A spread-over-time animation or small multiples showing infestation following transportation corridors outward from initial detection points.
3. Proximity analysis: distance from interstate/highway vs. EAB detection density.

### Recommended direction
Make the map about the **relationship** between an invasive forest pest and the infrastructure that spreads it — EAB moves largely via firewood and nursery stock transported along major roads, so the interstate network isn't just a basemap layer, it's the mechanism being mapped.

### Technical opportunity
- USDA APHIS / Forest Service EAB detection records
- TDOT interstate/highway network
- Proximity and spread-over-time analysis

**Expected effort:** **High**

---

## Day 14 — Borgesian Map
**Date:** November 14  
**Concept:** **The Map of a Single Tree**

### Map ideas
1. An extremely detailed "map" of one individual tree — branches, canopy extent, root zone — as if it were a landscape.
2. Treat the tree's structure (trunk, limbs, canopy) with map conventions: contours, labels, scale.
3. A conceptual piece where tree anatomy is rendered using cartographic symbology (elevation = height, "watersheds" = branch structure).

### Recommended direction
Pick one real or representative tree and go absurdly deep — treat its canopy and branch structure the way you would treat terrain, applying genuine cartographic techniques (contour-like lines, hierarchy, labeling) to a non-geographic subject.

### Design concept
The point is Borges' map-as-territory idea taken literally at the smallest possible scale: a single tree treated with the full apparatus of a detailed topographic map.

**Expected effort:** **Low**

---

## Day 15 — Inside Out
**Date:** November 15  
**Concept:** **North Chickamauga Creek Gorge, Inverted**

### Map ideas
1. Invert the gorge's elevation model so the gorge walls read as peaks and the ridgelines read as a valley.
2. A companion figure/ground inversion: render developed land as the visible "shape" and forest as the void, instead of the usual other way around.
3. Pair the two inversions (terrain and land-cover) side by side as a diptych for the day.

### Recommended direction
Build two inversions of the same place rather than one: an inverted terrain relief of the gorge itself, and an inverted forest-vs-developed figure/ground treatment of the surrounding land cover. Together they make "inside out" a method, not just a visual trick, and set up Day 26's right-side-up treatment of the same gorge as a quiet callback.

### Technical opportunity
- DEM of North Chickamauga Creek Gorge, elevation-inverted
- Land cover classification (forest vs. developed/non-forest) rendered as an inverted figure/ground composition

**Expected effort:** **Moderate**

---

## Day 16 — Collaborative Map
**Date:** November 16  
**Concept:** **Reworking a Declassified CIA Map of Konar Valley**

### Map ideas
1. Source a declassified CIA map of the Konar Valley, Afghanistan, and reinterpret or redraw it with modern cartographic technique.
2. Georeference the historical map and overlay modern data for comparison.
3. Collaborate with someone else by splitting the work: one person handles georeferencing/sourcing, the other handles redesign.

### Recommended direction
"Collaborative" here can mean collaborating across time with the original cartographer — source the declassified map, georeference it, and produce a modern reinterpretation or direct comparison.

### Potential data
- CIA / declassified map archives (e.g., University of Texas Perry-Castañeda Library historical map collection)

**Expected effort:** **Moderate**

---

## Day 17 — Light & Dark
**Date:** November 17  
**Concept:** **Sri Chinmoy Self-Transcendence Race**

### Map ideas
1. Map the race's short city-block loop course, run continuously day and night for over 50 days straight, with a light/dark treatment showing runner activity across the full day-night cycle.
2. A time-of-day ring or spiral visualization of lap activity around the loop, distinguishing daylight hours from night hours.
3. Pair the tiny physical course with the enormous cumulative distance (3,100 miles) covered by looping it thousands of times, day and night without stopping, as the "light & dark" contrast.

### Recommended direction
The race's defining feature is that it runs continuously through day and night for weeks at a time — use that literal day/night cycle, not a generic hillshade or lighting treatment, as the organizing idea for the map.

**Expected effort:** **Moderate**

---

## Day 18 — NULL
**Date:** November 18  
**Concept:** **1994 Marathon des Sables: Mauro Prosperi's 291km Off Course**

### Map ideas
1. The known race route of the 1994 Marathon des Sables alongside Mauro Prosperi's last known position before he vanished into a sandstorm.
2. A map showing the gap between where he was last tracked and where he was eventually found — roughly 291km away in Algeria — with the days in between rendered as a literal unknown/NULL region rather than a reconstructed line.
3. Treat the missing week of his actual path as the map's subject: known start, known end, true path NULL.

### Hyperlink
https://www.bbc.com/news/magazine-30046426 

### Recommended direction
Tie this directly to the NULL theme: his real position was genuinely unknown for over a week. Resist the urge to fully reconstruct his path — the honest map is the one that shows the known points and leaves the gap in between empty.

**Expected effort:** **Moderate**

---

## Day 19 — Senses: Smell
**Date:** November 19  
**Concept:** **Distribution of Ponderosa Pine**

### Map ideas
1. A range map of Ponderosa Pine across its natural distribution.
2. A Ponderosa Pine density/abundance surface.
3. Pair the distribution map with a note on its distinctive vanilla/butterscotch bark scent as the "smell" connection.

### Recommended direction
Make this a straightforward, well-executed species distribution map. The "smell" theme is carried by Ponderosa Pine's famously scented bark, so let the map focus on range and density.

### Potential data
- USFS FIA / USGS tree species range data

**Expected effort:** **Moderate**

---

## Day 20 — Hexagons
**Date:** November 20  
**Concept:** **Wildfire Potential Hazard in Hexagons**

### Map ideas
1. Wildfire Hazard Potential (WHP) data aggregated into a hex grid.
2. A hexbin comparison of hazard level across regions.
3. A hexagon map blending hazard score with forest cover or WUI.

### Recommended direction
Use the USFS Wildfire Hazard Potential dataset directly, aggregated to hexagons, so the hex pattern reflects a real, meaningful hazard gradient.

### Potential data
- USFS Wildfire Hazard Potential (WHP) raster

**Expected effort:** **Moderate**

---

## Day 21 — OpenStreetMap
**Date:** November 21  
**Concept:** **Who Contributes to OpenStreetMap, Per Capita**

### Map ideas
1. A world choropleth of OSM contributors or edits per capita by country.
2. Compare raw contributor counts vs. per-capita rates.
3. Highlight outlier countries with unusually high or low per-capita contribution.

### Recommended direction
Pull OSM contributor/edit statistics normalized by country population, and build a global choropleth rather than a local Tennessee map.

### Potential data
- OpenStreetMap contributor statistics
- World Bank population data

**Expected effort:** **Moderate**

---

## Day 22 — Projections
**Date:** November 22  
**Concept:** **A New Projection for Day 10's Fictional World**

### Map ideas
1. Derive and implement an original map projection (a mathematical transformation of coordinates) built specifically for the fictional world created on Day 10.
2. Render that world using the new projection and compare its distortion to standard real-world projections applied to the same geometry.
3. Document the math and design intent behind the projection alongside the map, closing the two-day arc that started with Day 10's AI-generated world.

### Recommended direction
This is the most technical day of the month — actually define a projection's transformation equations (even a novel variant or hybrid of existing ones), fitted to the fictional world's own shape and extent rather than to Earth. Reusing Day 10's invented geography means the projection's distortion characteristics are being designed for a world nobody has ever had to project before.

### Technical opportunity
- Custom projection math (e.g., via a Python/PROJ pipeline or a pyproj custom CRS) fit to Day 10's fictional coordinate frame
- Distortion comparison (Tissot's indicatrix) against the new projection

**Expected effort:** **Moderate**

---

## Day 23 — Senses: Taste
**Date:** November 23  
**Concept:** **Tennessee Food Exports to the World**

### Map ideas
1. A flow map of Tennessee agricultural exports to global destinations.
2. A choropleth of countries receiving Tennessee commodities.
3. Combine a Tennessee-side production map with a world-side destination map.

### Recommended direction
Build on the agriculture angle but push it outward — show where Tennessee-grown food actually goes globally, using flow lines or a paired origin/destination map.

### Potential data
- USDA / Tennessee Department of Agriculture export statistics
- USA Trade Online

**Expected effort:** **Moderate**

---

## Day 24 — Network
**Date:** November 24  
**Concept:** **Global Crypto Fund Flows**

### Map ideas
1. A network/flow map of cryptocurrency transaction volume between countries or exchanges.
2. A node-link diagram sized by transaction volume, with arcs showing flow direction.
3. Highlight major hubs (exchanges, mining regions) as network nodes.

### Recommended direction
This is a global network map, not a Tennessee-specific one. Focus on clean node-link/flow-map design since the data — and the audience interest — is inherently about global movement.

### Potential data
- Blockchain analytics providers (e.g., public Chainalysis reports)
- On-chain flow data, if accessible

**Expected effort:** **High**

---

## Day 25 — Is This a Map?
**Date:** November 25  
**Concept:** **A Map Made Without Mapping Software**

### Map ideas
1. Render a recognizable map purely as a styled pandas DataFrame (ASCII/HTML table as "map").
2. Build a spatial layout inside Notion, Excel, or another non-GIS tool.
3. Use conditional formatting or grid layout to represent geography without any GIS engine.

### Recommended direction
Pick one non-mapping tool — pandas DataFrame output, a spreadsheet grid, or Notion — and constrain yourself to it entirely. The challenge is making it still read as a map despite having no cartographic engine behind it.

**Expected effort:** **High**

---

## Day 26 — Water
**Date:** November 26  
**Concept:** **North Chickamauga Creek Gorge Watershed**

### Map ideas
1. A detailed watershed delineation for North Chickamauga Creek Gorge.
2. Flow accumulation and stream order within the gorge watershed.
3. Pair the watershed map with terrain/hillshade to show the gorge's relief.

### Recommended direction
Make this the month's signature hydrology map — a tightly focused, highly polished watershed map of North Chickamauga Creek Gorge with your strongest hillshade/basemap treatment.

### Potential data
- USGS NHD / 3DHP hydrography
- DEM for the gorge area

**Expected effort:** **High**

---

## Day 27 — New Tool
**Date:** November 27  
**Concept:** **A 3D Model in Sketchfab**

### Map ideas
1. Build and publish a 3D terrain or landscape model in Sketchfab.
2. Convert a DEM or a 3D scene export into a Sketchfab-hosted interactive model.
3. Pair the Sketchfab model with a short write-up of the workflow (e.g., ArcGIS Pro to Sketchfab).

### Recommended direction
Commit to Sketchfab specifically as the new tool. Export a 3D terrain/landscape model (e.g., from ArcGIS Pro or Blender) and publish it as an interactive Sketchfab embed.

**Expected effort:** **High**

---

## Day 28 — Senses: Feeling
**Date:** November 28  
**Concept:** **3D Hydro Model of Recent Nepal Flooding**

### Map ideas
1. A 3D visualization of flood extent/depth from a recent Nepal flooding event.
2. An animated or interactive 3D hydro model showing water rise over terrain.
3. Pair the 3D model with before/after imagery or flood extent data.

### Recommended direction
Source recent flood extent data for Nepal and build a 3D hydrological model over terrain. The emotional weight comes from the real event, not a generic "feeling" concept.

### Technical opportunity
- Flood extent data (e.g., Copernicus EMS, satellite-derived)
- DEM of the affected Nepal region
- 3D scene/animation to show water depth and rise

**Expected effort:** **High**

---

## Day 29 — Raster
**Date:** November 29  
**Concept:** **Wildfire Suppression Difficulty Index**

### Map ideas
1. A raster composite of terrain, access, and fuel factors forming a Suppression Difficulty Index.
2. Render the index as a painterly raster surface rather than a conventional hazard map.
3. Compare the index raster against known fire incident locations.

### Recommended direction
Build or source a Suppression Difficulty Index raster (terrain slope, road access, fuel type) and treat the raster itself as the visual subject, pushed toward an artistic rendering rather than a standard hazard map style.

### Potential data
- USFS Suppression Difficulty Index (where available)
- Slope/terrain, road network, fuel model data

**Expected effort:** **Moderate**

---

## Day 30 — Pen & Paper
**Date:** November 30  
**Concept:** **Hand-Drawn Tennessee, Left-Handed**

### Map ideas
1. Hand-draw a Tennessee map (state outline, rivers, cities) using your non-dominant (left) hand.
2. Pick a simple, forgiving subject given the added difficulty of left-hand drawing.
3. Photograph or scan the result as the final deliverable.

### Recommended direction
Keep the subject simple specifically because the left-hand constraint is the point — don't try to compensate for the handicap with a more complex subject.

**Expected effort:** **Low**

---

# Recommended Preparation Before November 1

The official challenge allows maps to be prepared in advance, even though the intended spirit is still to publish according to the daily theme. citehttps://30daymapchallenge.com/https://30daymapchallenge.com/2026/

## Prepare these first

### 1. Build a reusable ArcGIS Pro project
Create a project or template containing:
- Tennessee state boundary
- County boundaries
- Major rivers
- Major cities
- DEM / hillshade
- A neutral basemap
- Standard map layouts
- Your preferred fonts and text hierarchy
- Export presets

### 2. Keep the year folder organized
Repo layout under `2026/` (see `2026/README.md`):

```text
2026/
├── 30-Day-Map-Challenge-2026-Plan.md
├── images/                 # gallery finals: day-NN.png|jpg|jpeg
├── day-NN.html             # optional interactive embeds (year root)
├── 00_reference/
├── 01_points/
├── 02_lines/
├── 03_polygons/
├── 04_clusters/
├── 05_sight/
├── 06_vintage/
├── 07_10_minute/
├── 08_utopia/
├── 09_urban_rural/
├── 10_prompting_only/
├── …
└── 30_pen_paper/
```

Working notes and day-specific deps live in `NN_theme/`. Finished rasters go only in `images/`. GIS downloads stay in gitignored `data/raw/` and `data/processed/`.

### 3. Pre-identify the high-effort maps
The maps most worth preparing early are:

- **Day 5 — Sight**
- **Day 7 — 10 Minute Map**
- **Day 8 — Utopia**
- **Day 13 — Interactions**
- **Day 24 — Network**
- **Day 25 — Is This a Map?**
- **Day 26 — Water**
- **Day 27 — New tool**
- **Day 28 — Feeling**

### 4. Keep a small daily record
For each map, record:

```text
Date:
Theme:
Title:
Concept:
Data sources:
Software/tools:
Analysis:
Cartographic technique:
Time spent:
What worked:
What I would change:
Post URL:
```

This will make it much easier to produce a final recap of the challenge.

---

# Suggested Visual Strategy for the Month

Rather than making every map look identical, use a **consistent personal cartographic identity**.

### Keep consistent
- Typography
- Export dimensions
- General title placement
- Metadata / source attribution style
- Overall level of polish

### Allow to vary
- Color palettes
- Projection
- Basemap treatment
- Analytical technique
- Map orientation
- Degree of abstraction

The strongest maps should be the ones where the **visual design directly reinforces the theme**, rather than simply decorating a conventional GIS map.

---

# Priority Maps

If the month becomes difficult to sustain, prioritize these maps as likely portfolio-quality pieces:

1. **Day 5 — Sight:** 3D animated view from the Cherokee fire tower
2. **Day 6 — Vintage:** Historic USGS Chattanooga topo + modern hillshade (py3dep)
3. **Day 14 — Borgesian:** The map of a single tree
4. **Day 17 — Light & Dark:** Tennessee bird migration, day vs. night
5. **Day 22 — Projections:** A newly designed map projection
6. **Day 26 — Water:** North Chickamauga Creek Gorge watershed
7. **Day 28 — Feeling:** 3D hydro model of recent Nepal flooding
8. **Day 29 — Raster:** Wildfire Suppression Difficulty Index

The remaining maps can provide experimentation, lighter workload, or opportunities to learn new techniques.

---

# Challenge Goal

The goal for this month should not simply be **30 maps**. A stronger goal is:

> **30 opportunities to explore different ways of seeing Tennessee through GIS and cartography.**

The month should leave a useful record of:
- stronger cartographic design,
- new GIS techniques,
- new tools,
- creative mapping approaches,
- reusable workflows,
- and several maps worth keeping as portfolio examples.
