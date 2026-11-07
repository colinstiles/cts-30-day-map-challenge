/* Day 8 — Tugalo Undammed swipe (now left ↔ utopia right). */
(function () {
  const DEFAULT_BOUNDS = [
    [34.698, -83.415],
    [34.778, -83.318]
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
    maxZoom: 16
  });
  L.control.zoom({ position: "bottomleft" }).addTo(utopiaMap);

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
    maxZoom: 16
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

  function placeDam() {
    const icon = L.divIcon({
      className: "utopia-dam-icon",
      html: '<div style="width:10px;height:10px;border:2px solid #ffe66d;background:#d99a5b;border-radius:2px;"></div>',
      iconSize: [10, 10],
      iconAnchor: [5, 5]
    });
    L.marker(dam, { icon, interactive: false }).addTo(utopiaMap);
    L.marker(dam, { icon, interactive: false }).addTo(nowMap);
  }

  function initOverlays(frameBounds) {
    bounds = frameBounds;
    L.imageOverlay("images/day-08-utopia.png", bounds, { interactive: false }).addTo(utopiaMap);
    L.imageOverlay("images/day-08-now.png", bounds, { interactive: false }).addTo(nowMap);
    utopiaMap.fitBounds(bounds, { padding: [28, 28] });
    placeDam();
    syncNowMap();
  }

  utopiaMap.on("move zoom", syncNowMap);

  const slider = document.getElementById("utopia-slider");
  slider.addEventListener("input", () => setSwipe(Number(slider.value)));
  setSwipe(Number(slider.value));

  window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "cts-embed-visible" && event.data.visible) {
      utopiaMap.invalidateSize();
      nowMap.invalidateSize();
      syncNowMap();
    }
  });

  window.addEventListener("resize", () => {
    utopiaMap.invalidateSize();
    nowMap.invalidateSize();
    syncNowMap();
  });

  fetch("images/day-08-bounds.json")
    .then((r) => (r.ok ? r.json() : null))
    .then((data) => {
      if (data && data.bounds) bounds = data.bounds;
      if (data && data.dam) dam = [data.dam.lat, data.dam.lon];
      initOverlays(bounds);
    })
    .catch(() => initOverlays(bounds));
})();
