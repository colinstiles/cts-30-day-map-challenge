// Day 11 interactive map. The washes are a terrain-shadowed reach proxy
// baked by scripts/build_day11_sound.py. They are not decibel contours.

const BATTLES = ["chickamauga", "lookout", "missionary"];
const COLORS = {
  chickamauga: "#E2A04A",
  lookout: "#7EB0C4",
  missionary: "#D2644A",
};

const params = new URLSearchParams(window.location.search);
if (params.get("embed") === "1") {
  document.body.classList.add("is-embed");
}

const map = L.map("sound-map", {
  zoomControl: true,
  attributionControl: true,
  minZoom: 9,
  maxZoom: 16,
}).setView([35.01, -85.31], 11);

L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
  {
    attribution:
      'Basemap &copy; Esri, USGS, NOAA. Reach proxy: USGS 3DEP, NPS boundary, OpenStreetMap.',
    maxZoom: 16,
  }
).addTo(map);

const overlays = {};
const markers = {};
let ring = null;

function milesLabel(miles) {
  return `${miles.toFixed(1)} miles`;
}

async function loadMap() {
  const [bounds, places] = await Promise.all([
    fetch("11_sound/bounds.json").then((response) => response.json()),
    fetch("11_sound/places.geojson").then((response) => response.json()),
  ]);

  const imageBounds = [
    [bounds.south, bounds.west],
    [bounds.north, bounds.east],
  ];
  BATTLES.forEach((id) => {
    overlays[id] = L.imageOverlay(`11_sound/audibility-${id}.png`, imageBounds, {
      opacity: 0.92,
      interactive: false,
    }).addTo(map);
  });

  L.geoJSON(places, {
    filter: (feature) => feature.properties.kind === "park",
    style: {
      color: "#f3efe4",
      weight: 1,
      opacity: 0.7,
      fillOpacity: 0,
    },
  }).addTo(map);

  L.geoJSON(places, {
    filter: (feature) => feature.properties.kind === "cemetery",
    style: {
      color: "#f4f1e6",
      weight: 2,
      fillColor: "#f4f1e6",
      fillOpacity: 0.85,
    },
  })
    .bindTooltip("Chattanooga National Cemetery", { sticky: true })
    .addTo(map);

  const chick = bounds.sources.find((source) => source.id === "chickamauga");
  ring = L.circle([chick.lat, chick.lon], {
    radius: bounds.heardMiles * 1609.344,
    color: "#f3efe4",
    weight: 1.25,
    dashArray: "2 6",
    fill: false,
    interactive: false,
  }).addTo(map);

  bounds.sources.forEach((source) => {
    const marker = L.circleMarker([source.lat, source.lon], {
      radius: 6,
      color: "#14140f",
      weight: 1,
      fillColor: COLORS[source.id],
      fillOpacity: 1,
    })
      .bindTooltip(`${source.name}<br>${source.date}`, { direction: "top" })
      .addTo(map);
    markers[source.id] = marker;
  });

  // Frame the guns and the 10-mile reference, not the empty margin of the raster.
  const frame = L.latLngBounds(bounds.sources.map((source) => [source.lat, source.lon]));
  frame.extend([chick.lat + bounds.heardMiles / 69, chick.lon]);
  frame.extend([chick.lat - bounds.heardMiles / 69, chick.lon]);
  frame.extend([chick.lat, chick.lon + bounds.heardMiles / 55]);
  frame.extend([chick.lat, chick.lon - bounds.heardMiles / 55]);
  map.fitBounds(frame, { padding: [36, 36] });

  const lead = document.getElementById("sound-lead");
  lead.textContent =
    `Downtown is ${milesLabel(bounds.chickamaugaToCityMiles)} from the Chickamauga field; ` +
    `the cemetery is ${milesLabel(bounds.chickamaugaToCemeteryMiles)}. ` +
    `Open ground fades out at ${bounds.openMiles} miles.`;
  document.getElementById("sound-credit").textContent =
    `A ridge about ${bounds.barrierScaleM} m above the path leaves about a third of the proxy. ` +
    "Not a decibel model. USGS 3DEP, NPS, OpenStreetMap.";

  document.querySelectorAll(".sound-controls button[data-battle]").forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.dataset.battle;
      const on = button.getAttribute("aria-pressed") !== "true";
      button.setAttribute("aria-pressed", on ? "true" : "false");
      if (on) {
        overlays[id].addTo(map);
        markers[id].addTo(map);
      } else {
        map.removeLayer(overlays[id]);
        map.removeLayer(markers[id]);
      }
    });
  });

  document.getElementById("sound-ring").addEventListener("click", (event) => {
    const button = event.currentTarget;
    const on = button.getAttribute("aria-pressed") !== "true";
    button.setAttribute("aria-pressed", on ? "true" : "false");
    if (on) {
      ring.addTo(map);
    } else {
      map.removeLayer(ring);
    }
  });
}

loadMap().catch((error) => {
  document.getElementById("sound-credit").textContent = "The reach layer did not load.";
  console.error(error);
});
