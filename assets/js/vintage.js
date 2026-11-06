(function () {
  const HISTORIC_BOUNDS = [
    [34.98426929962519, -85.38568633457902],
    [35.13561539536915, -85.23806340419927]
  ];

  const modernMap = L.map("modern-map", {
    zoomControl: false,
    attributionControl: true,
    minZoom: 10,
    maxZoom: 17
  });

  L.control.zoom({ position: "bottomleft" }).addTo(modernMap);

  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}", {
    attribution: "Tiles &copy; Esri",
    maxZoom: 19
  }).addTo(modernMap);

  const historicMap = L.map("historic-map", {
    attributionControl: false,
    zoomControl: false,
    dragging: false,
    keyboard: false,
    scrollWheelZoom: false,
    doubleClickZoom: false,
    boxZoom: false,
    touchZoom: false,
    minZoom: 10,
    maxZoom: 17
  });

  L.imageOverlay("images/day-06-historic.png", HISTORIC_BOUNDS, {
    interactive: false
  }).addTo(historicMap);

  modernMap.fitBounds(HISTORIC_BOUNDS, { padding: [24, 24] });

  function syncHistoricMap() {
    historicMap.setView(modernMap.getCenter(), modernMap.getZoom(), { animate: false });
  }

  modernMap.on("move zoom", syncHistoricMap);
  syncHistoricMap();

  const slider = document.getElementById("vintage-slider");
  const divider = document.getElementById("vintage-divider");
  const historicClip = document.getElementById("historic-clip");

  function setSwipe(value) {
    historicClip.style.width = `${value}%`;
    divider.style.left = `${value}%`;
  }

  slider.addEventListener("input", () => setSwipe(Number(slider.value)));
  setSwipe(Number(slider.value));

  if (new URLSearchParams(window.location.search).has("embed")) {
    document.body.classList.add("vintage-page--embed");
  }

  window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "cts-embed-visible" && event.data.visible) {
      modernMap.invalidateSize();
      historicMap.invalidateSize();
      syncHistoricMap();
    }
  });

  window.addEventListener("resize", () => {
    modernMap.invalidateSize();
    historicMap.invalidateSize();
    syncHistoricMap();
  });
}());
