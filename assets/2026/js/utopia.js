/* Day 8 — Tugalo Undammed swipe (now left ↔ utopia right). */
(function () {
  const DEFAULT_BOUNDS = [
    [34.700, -83.408],
    [34.766, -83.312]
  ];
  const DAM = [34.71396, -83.35183];

  const embed = new URLSearchParams(window.location.search).has("embed");
  if (embed) {
    document.body.classList.add("utopia-page--embed");
  }

  // Base (full): utopia. Clip (left): now.
  const utopiaMap = L.map("utopia-utopia-map", {
    zoomControl: false,
    attributionControl: true,
    minZoom: 11,
    maxZoom: 18
  });
  L.control.zoom({ position: "bottomright" }).addTo(utopiaMap);

  const nowMap = L.map("utopia-now-map", {
    attributionControl: false,
    zoomControl: false,
    dragging: false,
    keyboard: false,
    scrollWheelZoom: false,
    doubleClickZoom: false,
    boxZoom: false,
    touchZoom: false,
    minZoom: 11,
    maxZoom: 18
  });

  let bounds = DEFAULT_BOUNDS;
  let dam = DAM;

  function syncNowMap() {
    nowMap.setView(utopiaMap.getCenter(), utopiaMap.getZoom(), { animate: false });
  }

  function setSwipe(value) {
    document.getElementById("utopia-clip").style.width = `${value}%`;
    document.getElementById("utopia-divider").style.left = `${value}%`;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;"
    }[ch]));
  }

  function addPlace(map, place) {
    const icon = L.divIcon({
      className: "utopia-place",
      html: `<span>${escapeHtml(place.name)}</span>`,
      iconSize: [0, 0],
      iconAnchor: [0, 0]
    });
    L.marker([place.lat, place.lon], { icon, interactive: false, keyboard: false }).addTo(map);
  }

  function addPlaces(places) {
    places.forEach((place) => {
      if (!place || !place.name || !Number.isFinite(place.lat) || !Number.isFinite(place.lon)) return;
      if (place.side === "now" || place.side === "both") addPlace(nowMap, place);
      if (place.side === "utopia" || place.side === "both") addPlace(utopiaMap, place);
    });
  }

  function placeDam() {
    const icon = L.divIcon({
      className: "utopia-dam-icon",
      html: '<div style="width:10px;height:10px;border:2px solid #ffe66d;background:#d99a5b;border-radius:2px;"></div>',
      iconSize: [10, 10],
      iconAnchor: [5, 5]
    });
    // The dam exists only on the "now" side. Utopia is the river without it.
    L.marker(dam, { icon, interactive: false, keyboard: false }).addTo(nowMap);
  }

  let userMoved = false;

  function coverBounds(frameBounds) {
    // Fit the whole bowl. Side space stays the page color instead of cropping the arms.
    utopiaMap.fitBounds(frameBounds, { padding: [18, 18], animate: false });
  }

  function initOverlays(frameBounds) {
    bounds = frameBounds;
    L.imageOverlay("images/day-08-utopia.png", bounds, { interactive: false }).addTo(utopiaMap);
    L.imageOverlay("images/day-08-now.png", bounds, { interactive: false }).addTo(nowMap);
    coverBounds(bounds);
    placeDam();
    syncNowMap();
  }

  utopiaMap.on("dragstart", () => {
    userMoved = true;
  });
  utopiaMap.on("move zoom", syncNowMap);

  const header = document.getElementById("utopia-header");
  const toggle = document.getElementById("utopia-toggle");
  if (header && toggle) {
    const narrow = window.matchMedia("(max-width: 700px)");
    const setCollapsed = (collapsed) => {
      header.classList.toggle("is-collapsed", collapsed);
      toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
      toggle.textContent = collapsed ? "Show" : "Hide";
    };
    setCollapsed(narrow.matches && !embed);
    toggle.addEventListener("click", () => {
      setCollapsed(!header.classList.contains("is-collapsed"));
    });
  }

  const slider = document.getElementById("utopia-slider");
  slider.addEventListener("input", () => setSwipe(Number(slider.value)));
  setSwipe(Number(slider.value));

  window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "cts-embed-visible" && event.data.visible) {
      utopiaMap.invalidateSize();
      nowMap.invalidateSize();
      if (!userMoved) coverBounds(bounds);
      syncNowMap();
    }
  });

  window.addEventListener("resize", () => {
    utopiaMap.invalidateSize();
    nowMap.invalidateSize();
    if (!userMoved) coverBounds(bounds);
    syncNowMap();
  });

  fetch("images/day-08-bounds.json")
    .then((r) => (r.ok ? r.json() : null))
    .then((data) => {
      if (data && data.bounds) bounds = data.bounds;
      if (data && data.dam) dam = [data.dam.lat, data.dam.lon];
      initOverlays(bounds);
      if (data && Array.isArray(data.places)) addPlaces(data.places);
    })
    .catch(() => initOverlays(bounds));
})();
