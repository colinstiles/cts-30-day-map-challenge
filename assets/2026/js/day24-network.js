(function () {
  const EMBED = document.body.classList.contains("d24-embed");
  const ASSETS = [
    { id: "BTC", name: "Bitcoin", color: "#F0C14D", offset: -16 },
    { id: "ETH", name: "Ether", color: "#C4B5FD", offset: -5.5 },
    { id: "USDC", name: "USDC", color: "#7DD3FC", offset: 5.5 },
    { id: "USDT", name: "Tether", color: "#5EE0A0", offset: 16 },
  ];
  const ASSET = Object.fromEntries(ASSETS.map((asset) => [asset.id, asset]));
  const PLACES = {
    US: { name: "United States", lon: -98.5, lat: 39.5 },
    CA: { name: "Canada", lon: -106.0, lat: 56.0 },
    GB: { name: "United Kingdom", lon: -1.5, lat: 53.5 },
    DE: { name: "Germany", lon: 10.4, lat: 51.1 },
    TR: { name: "Türkiye", lon: 35.2, lat: 39.0 },
    RU: { name: "Russia", lon: 48.0, lat: 58.0 },
    IN: { name: "India", lon: 79.0, lat: 22.5 },
    ID: { name: "Indonesia", lon: 113.0, lat: -2.0 },
  };
  // Table 1. Billion dollars, and the paper's share of that asset.
  const CORRIDORS = [
    ["GB", "US", "BTC", 9.89, 1.7],
    ["US", "GB", "BTC", 9.28, 1.6],
    ["CA", "US", "BTC", 4.94, 0.8],
    ["DE", "US", "BTC", 4.89, 0.8],
    ["US", "CA", "BTC", 4.87, 0.8],
    ["US", "GB", "ETH", 2.23, 1.0],
    ["GB", "US", "ETH", 2.09, 0.9],
    ["US", "ID", "ETH", 1.3, 0.6],
    ["US", "TR", "ETH", 1.27, 0.6],
    ["RU", "US", "ETH", 1.26, 0.6],
    ["US", "GB", "USDC", 6.33, 1.9],
    ["GB", "US", "USDC", 6.23, 1.8],
    ["IN", "US", "USDC", 4.21, 1.2],
    ["US", "IN", "USDC", 4.18, 1.2],
    ["ID", "US", "USDC", 3.85, 1.1],
    ["US", "TR", "USDT", 5.89, 0.5],
    ["US", "RU", "USDT", 5.47, 0.5],
    ["TR", "US", "USDT", 5.24, 0.5],
    ["RU", "US", "USDT", 5.0, 0.4],
    ["GB", "US", "USDT", 4.79, 0.4],
  ].map(([origin, dest, asset, billion, share]) => ({
    id: origin + "-" + dest + "-" + asset,
    origin,
    dest,
    asset,
    billion,
    share,
  }));
  const HUBS = {
    US: "USA",
    CA: "CAN",
    GB: "GBR",
    DE: "DEU",
    TR: "TUR",
    RU: "RUS",
    IN: "IND",
    ID: "IDN",
  };

  const enabled = new Set(ASSETS.map((asset) => asset.id));
  let selected = null;
  let hotId = null;
  let corridors = emptyCollection();
  let beads = emptyCollection();
  let hubs = emptyCollection();
  let map;
  let popup;

  const listEl = document.getElementById("d24-list");
  const filtersEl = document.getElementById("d24-filters");
  const clearEl = document.getElementById("d24-clear");
  const noteEl = document.getElementById("d24-note");

  function emptyCollection() {
    return { type: "FeatureCollection", features: [] };
  }

  function toVector(lon, lat) {
    const lambda = lon * Math.PI / 180;
    const phi = lat * Math.PI / 180;
    return [
      Math.cos(phi) * Math.cos(lambda),
      Math.cos(phi) * Math.sin(lambda),
      Math.sin(phi),
    ];
  }

  function fromVector(vector) {
    const [x, y, z] = vector;
    return [
      Math.atan2(y, x) * 180 / Math.PI,
      Math.atan2(z, Math.hypot(x, y)) * 180 / Math.PI,
    ];
  }

  function greatCircle(origin, dest) {
    const start = toVector(origin.lon, origin.lat);
    const end = toVector(dest.lon, dest.lat);
    const dot = Math.min(1, Math.max(-1, start[0] * end[0] + start[1] * end[1] + start[2] * end[2]));
    const omega = Math.acos(dot);
    const steps = 64;
    const coords = [];
    for (let index = 0; index <= steps; index += 1) {
      const t = index / steps;
      if (omega < 1e-6) {
        coords.push([origin.lon, origin.lat]);
        continue;
      }
      const left = Math.sin((1 - t) * omega) / Math.sin(omega);
      const right = Math.sin(t * omega) / Math.sin(omega);
      coords.push(fromVector([
        left * start[0] + right * end[0],
        left * start[1] + right * end[1],
        left * start[2] + right * end[2],
      ]));
    }
    return splitDateline(coords);
  }

  function splitDateline(coords) {
    const parts = [[coords[0]]];
    for (let index = 1; index < coords.length; index += 1) {
      const prev = coords[index - 1];
      const next = coords[index];
      if (Math.abs(next[0] - prev[0]) <= 180) {
        parts[parts.length - 1].push(next);
        continue;
      }
      let from = prev[0];
      let to = next[0];
      if (from - to > 180) {
        to += 360;
      } else if (to - from > 180) {
        from += 360;
      }
      const edge = from > 0 ? 180 : -180;
      const span = to - from || 1;
      const t = (edge - from) / span;
      const lat = prev[1] + (next[1] - prev[1]) * t;
      parts[parts.length - 1].push([Math.sign(prev[0]) * 180, lat]);
      parts.push([[Math.sign(next[0]) * 180, lat], next]);
    }
    return parts.filter((part) => part.length > 1);
  }

  function buildFlows() {
    const outbound = {};
    Object.keys(PLACES).forEach((iso) => {
      outbound[iso] = 0;
    });
    corridors = emptyCollection();
    beads = emptyCollection();
    CORRIDORS.forEach((row) => {
      outbound[row.origin] += row.billion;
      const lines = greatCircle(PLACES[row.origin], PLACES[row.dest]);
      corridors.features.push({
        type: "Feature",
        id: row.id,
        properties: row,
        geometry: { type: "MultiLineString", coordinates: lines },
      });
      const flat = lines.flat();
      const bead = flat[Math.min(flat.length - 1, Math.round(flat.length * 0.72))];
      beads.features.push({
        type: "Feature",
        id: row.id,
        properties: row,
        geometry: { type: "Point", coordinates: bead },
      });
    });
    hubs = {
      type: "FeatureCollection",
      features: Object.entries(PLACES).map(([iso, place]) => ({
        type: "Feature",
        id: iso,
        properties: { iso, name: place.name, sent: outbound[iso] },
        geometry: { type: "Point", coordinates: [place.lon, place.lat] },
      })),
    };
  }

  function assetFilter() {
    return ["in", ["get", "asset"], ["literal", [...enabled]]];
  }

  function offsetExpression() {
    if (enabled.size < 2) {
      return 0;
    }
    const match = ["match", ["get", "asset"]];
    ASSETS.forEach((asset) => {
      match.push(asset.id, asset.offset);
    });
    match.push(0);
    return match;
  }

  function applyFilters() {
    if (!map.getLayer("corridors")) {
      return;
    }
    const filter = assetFilter();
    map.setFilter("corridors", filter);
    map.setFilter("beads", filter);
    map.setPaintProperty("corridors", "line-offset", offsetExpression());
    renderList();
    paintStates();
  }

  function visibleRows() {
    return CORRIDORS
      .filter((row) => enabled.has(row.asset))
      .filter((row) => !selected || row.origin === selected || row.dest === selected)
      .sort((a, b) => b.billion - a.billion);
  }

  function renderList() {
    listEl.replaceChildren();
    visibleRows().forEach((row) => {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.id = row.id;
      button.style.borderLeftColor = ASSET[row.asset].color;
      if (row.id === hotId) {
        button.classList.add("is-hot");
      }
      const route = document.createElement("span");
      route.className = "d24-route";
      route.textContent = PLACES[row.origin].name + " → " + PLACES[row.dest].name;
      const asset = document.createElement("span");
      asset.className = "d24-asset";
      asset.textContent = ASSET[row.asset].name + " · " + row.share + "% of it";
      route.appendChild(asset);
      const amount = document.createElement("span");
      amount.className = "d24-amount";
      amount.textContent = row.billion.toFixed(2);
      button.append(route, amount);
      button.addEventListener("mouseenter", () => setHot(row.id));
      button.addEventListener("mouseleave", () => setHot(null));
      button.addEventListener("click", () => focusCorridor(row));
      item.appendChild(button);
      listEl.appendChild(item);
    });
  }

  function paintStates() {
    const shown = new Set(visibleRows().map((row) => row.id));
    CORRIDORS.forEach((row) => {
      const state = {
        hot: row.id === hotId,
        muted: Boolean(hotId) && row.id !== hotId,
        hide: !shown.has(row.id) && Boolean(selected),
      };
      ["corridors", "beads"].forEach((source) => {
        map.setFeatureState({ source, id: row.id }, state);
      });
    });
  }

  function setHot(id) {
    hotId = id;
    if (map.getSource("corridors")) {
      paintStates();
    }
    listEl.querySelectorAll("button").forEach((button) => {
      button.classList.toggle("is-hot", button.dataset.id === id);
    });
  }

  function selectCountry(iso) {
    selected = selected === iso ? null : iso;
    clearEl.hidden = !selected;
    if (selected) {
      const place = PLACES[selected];
      map.easeTo({
        center: [place.lon, place.lat],
        zoom: Math.max(map.getZoom(), 2.2),
        duration: motion(),
      });
    } else {
      fitAll();
    }
    setHot(null);
    renderList();
    note();
  }

  function shortBounds(origin, dest) {
    let west = origin.lon;
    let east = dest.lon;
    if (east < west) {
      const swap = west;
      west = east;
      east = swap;
    }
    const south = Math.min(origin.lat, dest.lat);
    const north = Math.max(origin.lat, dest.lat);
    if (east - west > 180) {
      return new maplibregl.LngLatBounds([east, south], [west + 360, north]);
    }
    return new maplibregl.LngLatBounds([west, south], [east, north]);
  }

  function focusCorridor(row) {
    map.fitBounds(shortBounds(PLACES[row.origin], PLACES[row.dest]), {
      padding: panelPadding(48),
      maxZoom: 3.4,
      duration: motion(),
    });
    setHot(row.id);
  }

  function motion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 700;
  }

  function panelPadding(extra) {
    if (EMBED) {
      return 28;
    }
    const narrow = window.innerWidth <= 720;
    if (narrow) {
      return { top: 24, right: 24, bottom: window.innerHeight * 0.48, left: 24 };
    }
    return { top: 36, right: 36, bottom: 36, left: 390 + (extra || 0) };
  }

  function fitAll() {
    map.fitBounds([[-150, -28], [150, 78]], { padding: panelPadding(), duration: motion() });
  }

  function note() {
    if (selected) {
      noteEl.textContent = PLACES[selected].name + " is limited to the corridors drawn from or to it. The circle is still the sum of corridors leaving the country.";
      return;
    }
    noteEl.textContent = "Width is billion dollars. A circle sums the corridors leaving that country, not its full outflow. Türkiye and Russia send more Tether than any one of these lines. Vietnam and Korea have no top-five corridor.";
  }

  function popupHtml(row) {
    const root = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = PLACES[row.origin].name + " → " + PLACES[row.dest].name;
    const detail = document.createElement("span");
    detail.textContent = ASSET[row.asset].name + " · " + row.billion.toFixed(2) + " billion dollars · " + row.share + "%";
    root.append(title, detail);
    return root;
  }

  function bindFilters() {
    ASSETS.forEach((asset) => {
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("aria-pressed", "true");
      const swatch = document.createElement("span");
      swatch.className = "d24-swatch";
      swatch.style.background = asset.color;
      button.append(swatch, document.createTextNode(asset.name));
      button.addEventListener("click", () => {
        if (enabled.has(asset.id) && enabled.size === 1) {
          return;
        }
        if (enabled.has(asset.id)) {
          enabled.delete(asset.id);
        } else {
          enabled.add(asset.id);
        }
        button.setAttribute("aria-pressed", String(enabled.has(asset.id)));
        applyFilters();
      });
      filtersEl.appendChild(button);
    });
    clearEl.addEventListener("click", () => selectCountry(selected));
  }

  function addMapLayers(world) {
    map.addSource("countries", { type: "geojson", data: world });
    map.addSource("corridors", { type: "geojson", data: corridors, promoteId: "id" });
    map.addSource("beads", { type: "geojson", data: beads, promoteId: "id" });
    map.addSource("hubs", { type: "geojson", data: hubs });
    map.addLayer({
      id: "land",
      type: "fill",
      source: "countries",
      paint: { "fill-color": "#3a3834", "fill-opacity": 1 },
    });
    map.addLayer({
      id: "hub-land",
      type: "fill",
      source: "countries",
      filter: ["in", ["get", "iso3"], ["literal", Object.values(HUBS)]],
      paint: { "fill-color": "#6e5840" },
    });
    map.addLayer({
      id: "corridors",
      type: "line",
      source: "corridors",
      paint: {
        "line-color": ["match", ["get", "asset"], "BTC", "#F0C14D", "ETH", "#C4B5FD", "USDC", "#7DD3FC", "USDT", "#5EE0A0", "#f6f1e4"],
        "line-width": ["interpolate", ["linear"], ["get", "billion"], 1.2, 1.6, 9.89, 7.5],
        "line-opacity": [
          "case",
          ["boolean", ["feature-state", "hide"], false], 0.08,
          ["boolean", ["feature-state", "hot"], false], 1,
          ["boolean", ["feature-state", "muted"], false], 0.2,
          0.9,
        ],
        "line-offset": offsetExpression(),
      },
      layout: { "line-cap": "round", "line-join": "round" },
    });
    map.addLayer({
      id: "beads",
      type: "circle",
      source: "beads",
      paint: {
        "circle-radius": 3.2,
        "circle-color": ["match", ["get", "asset"], "BTC", "#F0C14D", "ETH", "#C4B5FD", "USDC", "#7DD3FC", "USDT", "#5EE0A0", "#f6f1e4"],
        "circle-opacity": [
          "case",
          ["boolean", ["feature-state", "hide"], false], 0,
          ["boolean", ["feature-state", "muted"], false], 0.15,
          0.95,
        ],
      },
    });
    map.addLayer({
      id: "hubs",
      type: "circle",
      source: "hubs",
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["get", "sent"], 3.8, 5, 40.8, 15],
        "circle-color": "#f6f1e4",
        "circle-stroke-color": "#141210",
        "circle-stroke-width": 1,
      },
    });

    if (EMBED) {
      return;
    }
    const anchors = {
      US: "bottom",
      CA: "bottom",
      GB: "left",
      DE: "right",
      TR: "right",
      RU: "left",
      IN: "top",
      ID: "bottom",
    };
    Object.entries(PLACES).forEach(([iso, place]) => {
      const label = document.createElement("button");
      label.type = "button";
      label.className = "d24-label";
      label.textContent = place.name;
      label.addEventListener("click", (event) => {
        event.stopPropagation();
        selectCountry(iso);
      });
      new maplibregl.Marker({ element: label, anchor: anchors[iso] })
        .setLngLat([place.lon, place.lat])
        .addTo(map);
    });
    map.on("mousemove", "corridors", (event) => {
      map.getCanvas().style.cursor = "pointer";
      const row = event.features[0].properties;
      setHot(row.id);
      popup.setLngLat(event.lngLat).setDOMContent(popupHtml(row)).addTo(map);
    });
    map.on("mouseleave", "corridors", () => {
      map.getCanvas().style.cursor = "";
      setHot(null);
      popup.remove();
    });
    map.on("click", "hubs", (event) => {
      selectCountry(event.features[0].properties.iso);
    });
    map.on("mouseenter", "hubs", () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "hubs", () => {
      map.getCanvas().style.cursor = "";
    });
    map.on("click", (event) => {
      const hits = map.queryRenderedFeatures(event.point, { layers: ["hubs", "corridors"] });
      if (hits.length === 0 && selected) {
        selectCountry(selected);
      }
    });
  }

  function boot(world) {
    map = new maplibregl.Map({
      container: "d24-map",
      style: {
        version: 8,
        sources: {},
        layers: [{ id: "paper", type: "background", paint: { "background-color": "#141210" } }],
      },
      bounds: [[-150, -28], [150, 78]],
      fitBoundsOptions: { padding: panelPadding() },
      attributionControl: !EMBED,
      interactive: !EMBED,
      renderWorldCopies: false,
      dragRotate: false,
      pitchWithRotate: false,
    });
    if (!EMBED) {
      map.addControl(new maplibregl.AttributionControl({
        customAttribution: "Natural Earth · BIS Working Paper 1265",
      }), "bottom-right");
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "d24-popup", offset: 10 });
    }
    map.on("load", () => {
      addMapLayers(world || emptyCollection());
      renderList();
      note();
    });
  }

  bindFilters();
  buildFlows();
  renderList();
  note();
  fetch(new URL("world.geojson", window.location.href).href)
    .then((response) => {
      if (!response.ok) {
        throw new Error(String(response.status));
      }
      return response.json();
    })
    .then((world) => boot(world))
    .catch(() => boot(null));
})();
