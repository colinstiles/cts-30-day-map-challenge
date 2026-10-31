# 30-Day Map Challenge 2026 — Master Plan

**Challenge:** #30DayMapChallenge 2026  
**Dates:** November 1–30, 2026  
**Tools:** ArcGIS Pro, Python, AGOL, GeoLibre, Sketchfab, Blender, Cesium  
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

## 30-Day Plan at a Glance

| Day | Date | Official Theme | Primary Concept | Expected Effort |
|---:|---|---|---|---|
| 1 | Nov 1 | Points | Cave locations on Mars Astro Tharsis (USGS data) | Moderate |
| 2 | Nov 2 | Lines | Contours and Cumber Trail lines | Moderate |
| 3 | Nov 3 | Polygons | Descending watersheds, from HUC2 down to HUC12 | Low |
| 4 | Nov 4 | Clusters | Historical wildfire incidents in Southern Group; heatmap or bins | Moderate |
| 5 | Nov 5 | Senses: Sight | 3D interactive animation view from Cherokee Forest Service firetower at (82.3820370°W 36.2084546°N) | High |
| 6 | Nov 6 | Vintage | Historic Tennessee topo map with hillshade | Moderate |
| 7 | Nov 7 | 10 minute map | 10 minute interactive animation made in 10 minutes | High |
| 8 | Nov 8 | Utopia | Ideal forest coverage in Tennessee | High |
| 9 | Nov 9 | Urban-rural | Wildland-Urban Interface in Tennessee | Moderate |
| 10 | Nov 10 | Prompting only | AI-generated mapping workflow | Moderate |
| 11 | Nov 11 | Senses: Sound | Interstate high-sound corridors through Chattanooga | Moderate |
| 12 | Nov 12 | Power | Incan/Aztec controlled areas throughout time | Moderate |
| 13 | Nov 13 | Interactions | Forest-development interactions | High |
| 14 | Nov 14 | Borgesian map | One watershed mapped to absurd detail | High |
| 15 | Nov 15 | Inside out | Inverted terrain / landscape | Moderate |
| 16 | Nov 16 | Collaborative map | Declassified CIA map of Konar Valley, Afghanistan | Moderate |
| 17 | Nov 17 | Light & dark | Dramatic terrain and hillshade | Moderate |
| 18 | Nov 18 | NULL | Map the missing data | Moderate |
| 19 | Nov 19 | Senses: Smell | Forest / smoke / land-use odors | Moderate |
| 20 | Nov 20 | Hexagons | Wildfire Potential Hazard | Moderate |
| 21 | Nov 21 | OpenStreetMap | Per capita choropleth of countries that contribute to OSM | Moderate |
| 22 | Nov 22 | Projections | Tennessee through multiple projections | Moderate |
| 23 | Nov 23 | Senses: Taste | Tennessee agriculture / food distribution to globe | Moderate |
| 24 | Nov 24 | Network | Forest-road or stream network | High |
| 25 | Nov 25 | Is this a map? | Abstract geographic visualization | High |
| 26 | Nov 26 | Water | Watershed of North Chick Creek Gorge | High |
| 27 | Nov 27 | New tool | something made in Sketchfab | High |
| 28 | Nov 28 | Senses: Feeling | 3D hydro model of recent flooding in Nepal | High |
| 29 | Nov 29 | Raster | Wildfire Suppression Difficulty Index | Moderate |
| 30 | Nov 30 | Pen & paper | Hand-drawn Tennessee map | Low |

---

# Daily Plan

## Day 1 — Points
**Date:** November 1  
**Concept:** **Mars Caves**
**Tool:** ArcGIS Pro; Python

### Map ideas
- **Caves on Mars** — cave point locations on Mars Astro Tharsis

### Hyperlink
https://www.usgs.gov/news/caves-mars

### Recommended direction
Use a curated set of Tennessee forestry-related places rather than simply plotting everything. The goal should be a polished opening map that establishes the visual language for the month.

### Potential data
- Mars Global Cave Candidate Catalog (MGC3)

**Expected effort:** **Moderate**

---

## Day 2 — Lines
**Date:** November 2  
**Concept:** **Tennessee's Stream Network**

### Map ideas
1. Stream network styled by **stream order**.
2. A hierarchical map showing **headwaters → major tributaries → Tennessee River system**.
3. A highly simplified statewide hydrographic map where line weight creates the visual hierarchy.

### Recommended direction
Build a cartographic stream-network map with almost no competing layers. Use line hierarchy, subtle terrain, and a restrained palette.

### Potential data
- NHD / 3DHP hydrography
- TDEC / Tennessee stream datasets
- DEM-derived stream network

**Expected effort:** **Moderate**

---

## Day 3 — Polygons
**Date:** November 3  
**Concept:** **Tennessee Forest Landscape**

### Map ideas
1. Forest cover or forest-type polygons.
2. Tennessee physiographic regions.
3. Ecological sections / ecoregions.
4. Protected lands as a polygon composition.

### Recommended direction
A forest-type or ecological-region map will connect directly to your professional work while giving you an opportunity to create a sophisticated polygon-focused design.

**Expected effort:** **Moderate**

---

## Day 4 — Clusters
**Date:** November 4  
**Concept:** **Where Forest Disturbance Clusters**

### Map ideas
1. Wildfire ignition clusters.
2. Storm-damage clusters.
3. Forest pest or invasive-species observations.
4. FIA disturbance observations aggregated into hotspots.

### Recommended direction
Use a real clustering method rather than simply making a point-density map. A statewide or regional hotspot map could be especially compelling.

**Expected effort:** **Moderate**

---

## Day 5 — Senses: Sight
**Date:** November 5  
**Concept:** **What Can a Tennessee Lookout See?**

### Map ideas
1. Viewshed from a fire tower.
2. Viewshed from a Tennessee mountain summit.
3. Visibility from a forest overlook.
4. A cumulative viewshed from several scenic locations.

### Recommended direction
A fire-tower viewshed is the strongest match to your forestry background. Pair the viewshed with a subtle DEM and terrain shading.

### Technical opportunity
- ArcGIS Pro Viewshed / Geodesic Viewshed
- DEM and landform context
- Optional horizon-distance analysis

**Expected effort:** **High**

---

## Day 6 — Vintage
**Date:** November 6  
**Concept:** **Tennessee Forestry, 1930s–1950s**

### Map ideas
1. Re-create the appearance of an old Tennessee topographic or forestry map.
2. Style a modern forest map like an early USGS sheet.
3. Use historical roads, counties, rivers, and forests to build a genuinely historical map.

### Recommended direction
Make this a cartographic exercise rather than simply placing a vintage basemap underneath modern data. Use period typography, paper texture, muted inks, and historical symbology.

**Expected effort:** **High**

---

## Day 7 — 10 Minute Map
**Date:** November 7  
**Concept:** **The Tennessee Map I Can Make in 10 Minutes**

### Map ideas
1. Tennessee counties with one simple quantitative variable.
2. Major rivers and cities.
3. Annual precipitation by county.
4. A simple elevation choropleth.

### Rule
Set a timer for **10 minutes** and stop. Do not polish afterward.

### Recommended direction
Use a dataset you already have. The value of this map is the constraint, not the complexity.

**Expected effort:** **Very Low**

---

## Day 8 — Utopia
**Date:** November 8  
**Concept:** **A Tennessee Where Everyone Has Access to Forests**

### Map ideas
1. Every community within 15/30 minutes of a public forest or park.
2. Proposed network of new forests or greenways connecting population centers.
3. Ideal statewide conservation corridors.
4. A hypothetical statewide forest-access system.

### Recommended direction
Make a map of something that **could exist**, not simply a map of something that already exists.

### Technical opportunity
- Network analysis
- Service areas
- Population data
- Existing public lands
- Hypothetical suitability analysis

**Expected effort:** **High**

---

## Day 9 — Urban-rural
**Date:** November 9  
**Concept:** **The Tennessee Urban-Rural Gradient**

### Map ideas
1. Population density transitioning from urban cores to rural areas.
2. Impervious surface vs. forest cover.
3. A continuous urban-rural index.
4. Map the landscape around Nashville, Memphis, Knoxville, and Chattanooga as a series of gradients.

### Recommended direction
Avoid a simple binary urban/rural classification. A continuous gradient would be more cartographically interesting.

**Expected effort:** **Moderate**

---

## Day 10 — Prompting Only
**Date:** November 10  
**Concept:** **AI Makes a Map**

### Experiment
Use AI from start to finish for the mapping workflow, ideally through a chat or command-line workflow, and document the result.

### Possible challenge
Ask AI to produce a complete map specification or script for a Tennessee subject such as:
- forest cover
- streams
- wildfire
- elevation
- county population

Then execute the generated workflow with minimal manual intervention.

### Recommended direction
Treat this as an experiment. The interesting output is both the map **and** what the workflow reveals about AI-generated cartography.

**Expected effort:** **Moderate**

---

## Day 11 — Senses: Sound
**Date:** November 11  
**Concept:** **Tennessee Soundscape**

### Map ideas
1. Transportation noise around major cities.
2. Natural soundscape: rivers, waterfalls, forests, birds, or protected areas.
3. A conceptual map of where Tennessee is loudest and quietest.
4. Distance from major noise sources.

### Recommended direction
A natural soundscape map would be more distinctive than a conventional noise-pollution map.

**Expected effort:** **Moderate**

---

## Day 12 — Power
**Date:** November 12  
**Concept:** **Tennessee's Power Network**

### Map ideas
1. Transmission lines and substations.
2. Electricity generation facilities.
3. Hydroelectric infrastructure.
4. A map of energy production and transmission density.

### Recommended direction
Use infrastructure as the literal interpretation, but make the visual hierarchy dramatic.

**Expected effort:** **Moderate**

---

## Day 13 — Interactions
**Date:** November 13  
**Concept:** **Where Forests Meet Development**

### Map ideas
1. Forest loss around expanding urban areas.
2. Roads interacting with forest fragmentation.
3. Development pressure near protected lands.
4. Streams interacting with development and agriculture.

### Recommended direction
Make the map about **relationships**, not just two datasets shown together.

### Technical opportunity
- Overlay analysis
- Fragmentation metrics
- Proximity analysis
- Spatial joins

**Expected effort:** **High**

---

## Day 14 — Borgesian Map
**Date:** November 14  
**Concept:** **A Map That Becomes the Territory**

### Map ideas
1. Map one small watershed at absurdly detailed scale.
2. Show every stream segment, road, culvert, contour, parcel, tree, building, and land-cover transition available.
3. Build a map that deliberately approaches the impossible ideal described by Borges.

### Recommended direction
Choose a **small Tennessee watershed** and go very deep rather than mapping the whole state.

### Design concept
The final map should feel almost excessive: dense, detailed, intricate, and slightly absurd.

**Expected effort:** **Very High**

---

## Day 15 — Inside Out
**Date:** November 15  
**Concept:** **Turn Tennessee's Landscape Inside Out**

### Map ideas
1. Invert an elevation model so valleys become peaks.
2. Reverse hillshade illumination.
3. Create an upside-down or inverted terrain visualization.
4. Show the negative space of watersheds instead of watersheds themselves.

### Recommended direction
Use a familiar landscape and make the cartographic logic subtly wrong.

**Expected effort:** **Moderate**

---

## Day 16 — Collaborative Map
**Date:** November 16  
**Concept:** **Tennessee Through Two GIS Perspectives**

### Collaboration options
1. Make a map with another GIS professional.
2. Ask a forester to choose the subject and you handle cartography.
3. Let a colleague choose the design while you provide the analysis.
4. Build a map where each contributor owns half of the workflow.

### Recommended direction
A division of labor will make the collaboration genuinely visible in the final product.

**Expected effort:** **Moderate**

---

## Day 17 — Light & Dark
**Date:** November 17  
**Concept:** **Tennessee in Light and Shadow**

### Map ideas
1. Dramatic hillshade over Appalachian terrain.
2. Terrain illuminated from an unusual direction.
3. Light pollution vs. dark-sky areas.
4. A mostly monochrome elevation map with extreme light/shadow treatment.

### Recommended direction
This is a strong opportunity to build on the natural-earth hillshade style you've been developing in ArcGIS Pro.

**Expected effort:** **Moderate**

---

## Day 18 — NULL
**Date:** November 18  
**Concept:** **Mapping What We Don't Know**

### Map ideas
1. Data gaps in a statewide dataset.
2. NULL / unknown attribute values.
3. Areas with no observations.
4. A map emphasizing the geography of missing data.

### Recommended direction
Do not treat NULL as a nuisance. Make the **absence of information** the subject of the map.

**Expected effort:** **Moderate**

---

## Day 19 — Senses: Smell
**Date:** November 19  
**Concept:** **What Does Tennessee Smell Like?**

### Map ideas
1. Forests and aromatic plants.
2. Wildfire smoke / burned landscapes.
3. Agricultural areas associated with recognizable odors.
4. Industrial / wastewater / landfill odor sources.
5. A playful seasonal scent map.

### Recommended direction
This is one of the best days to intentionally depart from conventional GIS and make something conceptual.

**Expected effort:** **Moderate**

---

## Day 20 — Hexagons
**Date:** November 20  
**Concept:** **A Hexagonal Tennessee**

### Map ideas
1. Population density in hexagons.
2. Forest cover by hexagon.
3. Wildfire occurrence by hexagon.
4. Water quality observations aggregated into hexagons.
5. FIA plot density or forest characteristics.

### Recommended direction
Choose a variable with enough spatial variation to make the hexagonal pattern visually meaningful.

**Expected effort:** **Moderate**

---

## Day 21 — OpenStreetMap
**Date:** November 21  
**Concept:** **Tennessee Built Environment from OpenStreetMap**

### Map ideas
1. Buildings in a selected Tennessee city.
2. Trails and paths in a forest area.
3. Bridges and waterways.
4. A map of all OSM features within one small Tennessee community.
5. OSM road density around public lands.

### Recommended direction
A **small-area, high-detail OSM map** will likely be more visually interesting than a statewide overview.

**Expected effort:** **Moderate**

---

## Day 22 — Projections
**Date:** November 22  
**Concept:** **Tennessee in Different Worlds**

### Map ideas
1. Show the same Tennessee map in 4–6 projections.
2. Compare area, shape, and distance distortions.
3. Use an unusual projection that makes Tennessee visually unexpected.
4. Create a gallery of projections using identical symbology.

### Recommended direction
Make this both educational and beautiful. Consistency between panels will make the projection differences immediately apparent.

**Expected effort:** **Moderate**

---

## Day 23 — Senses: Taste
**Date:** November 23  
**Concept:** **The Taste of Tennessee**

### Map ideas
1. Agricultural commodities by county.
2. Tennessee crops and specialty crops.
3. Barbecue / food traditions.
4. Orchards, wineries, breweries, farmers markets, or other food destinations.
5. A map showing where recognizable Tennessee foods originate.

### Recommended direction
A map connecting agriculture to place would provide a strong Tennessee-specific interpretation.

**Expected effort:** **Moderate**

---

## Day 24 — Network
**Date:** November 24  
**Concept:** **A Tennessee Network**

### Map ideas
1. Forest-road network.
2. Stream network with accumulated flow.
3. Wildlife movement corridors.
4. Transportation or evacuation routes.
5. A statewide network of public forests and connecting corridors.

### Recommended direction
A forest-road or stream network would be most aligned with your existing GIS work while still allowing advanced cartography.

**Expected effort:** **High**

---

## Day 25 — Is This a Map?
**Date:** November 25  
**Concept:** **Turn Geographic Data Into Art**

### Map ideas
1. Turn a stream network into an abstract artwork.
2. Use forest boundaries to create a geometric composition.
3. Generate a raster landscape from geographic relationships.
4. Convert a Tennessee dataset into a visually recognizable non-map object.
5. Create a map where geographic orientation is intentionally ambiguous.

### Recommended direction
Do not worry about conventional north arrows, scale bars, or labels. The question is whether the result still feels geographic.

**Expected effort:** **High**

---

## Day 26 — Water
**Date:** November 26  
**Concept:** **Tennessee's Watershed Story**

### Map ideas
1. Watershed hierarchy from tiny headwaters to major river basins.
2. Flow accumulation and stream order.
3. Water quality measurements by watershed.
4. Lakes, rivers, wetlands, and floodplains.
5. A natural-earth hydrology map with detailed terrain.

### Recommended direction
This is a major opportunity for a signature map. Build a polished hydrology-focused composition with your strongest hillshade/basemap treatment.

**Expected effort:** **High**

---

## Day 27 — New Tool
**Date:** November 27  
**Concept:** **Learn Something New**

### Candidate tools
- QGIS technique you've never used
- Mapbox Studio
- MapLibre
- kepler.gl
- Observable / JavaScript visualization
- Python cartography workflow
- A new ArcGIS Pro geoprocessing tool
- A new raster or 3D workflow

### Recommended direction
Choose something that you genuinely want to add to your GIS toolbox beyond the challenge.

**Expected effort:** **High**

---

## Day 28 — Senses: Feeling
**Date:** November 28  
**Concept:** **Map a Feeling**

### Possible feelings
- Isolation
- Calm
- Danger
- Nostalgia
- Wonder
- Tension
- Wildness
- Remoteness

### Map ideas
1. A remoteness map designed to evoke solitude.
2. A wilderness map designed to evoke awe.
3. A nighttime landscape designed to feel isolated.
4. A storm-impact map designed to feel chaotic.

### Recommended direction
Start with the intended emotional response, then choose data and visual language to support it.

**Expected effort:** **High**

---

## Day 29 — Raster
**Date:** November 29  
**Concept:** **Raster Landscape Art**

### Map ideas
1. DEM art using terrain-derived rasters.
2. Forest canopy height as an artistic surface.
3. Multispectral imagery rendered as an abstract landscape.
4. Wildfire severity as a raster composition.
5. Combine multiple raster variables into a painterly Tennessee landscape.

### Recommended direction
Make the raster itself the visual subject rather than simply using raster data as a background.

**Expected effort:** **Moderate**

---

## Day 30 — Pen & Paper
**Date:** November 30  
**Concept:** **Hand-Drawn Tennessee**

### Map ideas
1. Hand-draw the Tennessee River system.
2. Sketch a favorite watershed.
3. Draw a forest landscape from memory.
4. Make a deliberately imperfect map of Tennessee.
5. Draw the challenge's favorite map from the month again, by hand.

### Recommended direction
End the challenge with something intentionally simple and personal. No need to reproduce GIS-level precision.

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

### 2. Create a shared data folder
Suggested organization:

```text
30DayMapChallenge2026/
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
├── ...
└── 30_pen_paper/
```

### 3. Pre-identify the high-effort maps
The maps most worth preparing early are:

- **Day 5 — Sight**
- **Day 6 — Vintage**
- **Day 8 — Utopia**
- **Day 13 — Interactions**
- **Day 14 — Borgesian map**
- **Day 24 — Network**
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

1. **Day 5 — Sight:** Tennessee fire-tower viewshed
2. **Day 6 — Vintage:** Historical Tennessee forestry aesthetic
3. **Day 14 — Borgesian:** Extremely detailed watershed map
4. **Day 17 — Light & Dark:** Dramatic Tennessee terrain
5. **Day 22 — Projections:** Tennessee through multiple projections
6. **Day 26 — Water:** Signature Tennessee hydrology map
7. **Day 28 — Feeling:** An intentionally emotional landscape map
8. **Day 29 — Raster:** Artistic raster landscape

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
