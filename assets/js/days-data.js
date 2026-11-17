// Data for the 30 Day Map Challenge gallery.
// Add a new year by appending an entry to CHALLENGE_YEARS with its 30 days,
// then drop finished exports into <year>/images/day-NN.<ext> as they're made.
// Optional `image` overrides that filename for one day.
const CHALLENGE_YEARS = {
  2026: {
    label: "2026",
    planUrl: "2026/30-Day-Map-Challenge-2026-Plan.md",
    imageDir: "2026/images",
    days: [
      { day: 1, date: "Nov 1", theme: "Points", concept: "Mars Caves", tool: "ArcGIS Pro, Python, JavaScript" },
      { day: 2, date: "Nov 2", theme: "Lines", concept: "Cumberland Trail Contours", tool: "ArcGIS Pro" },
      { day: 3, date: "Nov 3", theme: "Polygons", concept: "North Chickamauga Watersheds", tool: "ArcGIS Pro" },
      { day: 4, date: "Nov 4", theme: "Clusters", concept: "Tennessee Fire Incident Hotspots", tool: "MapLibre, InFORM", embed: "2026/day-04.html" },
      { day: 5, date: "Nov 5", theme: "Senses: Sight", concept: "View from the Cherokee Fire Tower", tool: "Three.js, USGS 3DEP", embed: "2026/day-05.html" },
      { day: 6, date: "Nov 6", theme: "Vintage", concept: "Chattanooga Then & Now", tool: "Leaflet, USGS HTMC, Esri World Street Map", embed: "2026/day-06.html" },
      { day: 7, date: "Nov 7", theme: "10 Minute Map", concept: "Chimney Tops 2 Pixel Fire (Sevier Co. 2016)", tool: "HTML canvas", embed: "2026/day-07.html" },
      { day: 8, date: "Nov 8", theme: "Utopia", concept: "Hidden Rapids of the Tallulah River", tool: "Python, Leaflet, 3DEP", embed: "2026/day-08.html" },
      { day: 9, date: "Nov 9", theme: "Urban-Rural", concept: "WUI Structures in Hamilton County", tool: "Python, USGS WUI, FEMA" },
      { day: 10, date: "Nov 10", theme: "Prompting Only", concept: "Vael: The Crescent Sea", tool: "Cursor, Grok, JavaScript", embed: "2026/day-10.html" },
      { day: 11, date: "Nov 11", theme: "Senses: Sound", concept: "Cannons of the Chattanooga Campaign", tool: "Python", image: "2026/images/day-11-decibels.png" },
      { day: 12, date: "Nov 12", theme: "Power", concept: "Year 5 for the Struggle over Ukraine", tool: "ArcGIS Pro", page: "2026/day-12.html" },
      { day: 13, date: "Nov 13", theme: "Interactions", concept: "Movements of People and Borders from European Conflicts", tool: "MapLibre", embed: "2026/day-13.html" },
      { day: 14, date: "Nov 14", theme: "Borgesian Map", concept: "1:1 Scale of an Oak Leaf", tool: "JavaScript", embed: "2026/day-14.html" },
      { day: 15, date: "Nov 15", theme: "Inside Out", concept: "Inverted Elevation of North Chickamauga Creek Gorge", tool: "forge3d, matplotlib" },
      { day: 16, date: "Nov 16", theme: "Collaborative Map", concept: "Afghanistan's Konar Valley, CIA 2001", tool: "Cesium", embed: "2026/day-16.html" },
      { day: 17, date: "Nov 17", theme: "Light & Dark", concept: "Self-Transcendence 3100 Mile Race", tool: "JavaScript, OpenStreetMap", embed: "2026/day-17.html" },
      { day: 18, date: "Nov 18", theme: "NULL", concept: "1994 Null route along the Marathon des Sables, Morroco and Algeria", tool: "ArcGIS Pro" },
      { day: 19, date: "Nov 19", theme: "Senses: Smell", concept: "Distribution of Ponderosa Pine's Intoxicating Scent", tool: "ArcGIS Pro, FIA BIGMAP" },
      { day: 20, date: "Nov 20", theme: "Hexagons", concept: "Tennessee Wildfire Hazard Potential", tool: "ArcGIS Pro, Python", embed: "2026/day-20.png" },
      { day: 21, date: "Nov 21", theme: "OpenStreetMap", concept: "Who Maps OpenStreetMap, Per Capita", tool: "Python, ohsomeNow" },
      { day: 22, date: "Nov 22", theme: "Projections", concept: "TBD", tool: "Tool TBD" },
      { day: 23, date: "Nov 23", theme: "Senses: Taste", concept: "TBD", tool: "Tool TBD" },
      { day: 24, date: "Nov 24", theme: "Network", concept: "TBD", tool: "Tool TBD" },
      { day: 25, date: "Nov 25", theme: "Is this a map?", concept: "TBD", tool: "Tool TBD" },
      { day: 26, date: "Nov 26", theme: "Water", concept: "TBD", tool: "Tool TBD" },
      { day: 27, date: "Nov 27", theme: "New Tool", concept: "TBD", tool: "Sketchfab" },
      { day: 28, date: "Nov 28", theme: "Senses: Feeling", concept: "TBD", tool: "Tool TBD" },
      { day: 29, date: "Nov 29", theme: "Raster", concept: "TBD", tool: "Tool TBD" },
      { day: 30, date: "Nov 30", theme: "Pen & Paper", concept: "TBD", tool: "Tool TBD" }
    ]
  }
};
