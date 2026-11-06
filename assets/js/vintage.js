(function () {
  const HISTORIC_BOUNDS = [
    [34.98426929962519, -85.38568633457902],
    [35.13561539536915, -85.23806340419927]
  ];

  const map = L.map("vintage-map", {
    zoomControl: true,
    attributionControl: true,
    minZoom: 10,
    maxZoom: 17
  });

  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}", {
    attribution: "Tiles &copy; Esri",
    maxZoom: 19
  }).addTo(map);

  const historicPane = map.createPane("historic-topo");
  historicPane.style.zIndex = 450;
  historicPane.style.pointerEvents = "none";

  L.imageOverlay("images/day-06-historic.png", HISTORIC_BOUNDS, {
    pane: "historic-topo",
    interactive: false
  }).addTo(map);

  map.fitBounds(HISTORIC_BOUNDS, { padding: [24, 24] });

  const slider = document.getElementById("vintage-slider");
  const divider = document.getElementById("vintage-divider");

  function setSwipe(value) {
    historicPane.style.clipPath = `inset(0 ${100 - value}% 0 0)`;
    divider.style.left = `${value}%`;
  }

  slider.addEventListener("input", () => setSwipe(Number(slider.value)));
  setSwipe(Number(slider.value));

  if (new URLSearchParams(window.location.search).has("embed")) {
    document.body.classList.add("vintage-page--embed");
  }

  window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "cts-embed-visible" && event.data.visible) {
      map.invalidateSize();
    }
  });
}());
