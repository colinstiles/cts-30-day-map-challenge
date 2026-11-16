// Day 16. The 2001 CIA block of the Konar, on Esri World Elevation.
(function () {
  const TERRAIN_URL = "https://elevation3d.arcgis.com/arcgis/rest/services/WorldElevation3D/Terrain3D/ImageServer";
  const IMAGERY_URL = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer";
  const HILLSHADE_URL = "https://services.arcgisonline.com/arcgis/rest/services/Elevation/World_Hillshade/MapServer";

  // Footprint of the printed sheet: Kabol and Lowgar in the near corner,
  // Peshawar to the east, the high country of Nurestan and Badakhshan at the far edge.
  const BLOCK = Cesium.Rectangle.fromDegrees(68.5, 33.7, 72.15, 36.25);

  // Heading is the direction the camera looks. Pitch is below the horizon.
  const VIEWS = {
    sheet: { lon: 70.35, lat: 34.85, heading: 28, pitch: -36, range: 255000 },
    valley: { lon: 71.08, lat: 34.92, heading: 16, pitch: -28, range: 68000 }
  };

  // Towns use published coordinates. Region labels sit in the province, off the town.
  const PLACES = [
    { name: "Kabol", lon: 69.1658, lat: 34.5328, kind: "town" },
    { name: "Jalalabad", lon: 70.4478, lat: 34.4342, kind: "town" },
    { name: "Asadabad", lon: 71.1528, lat: 34.8742, kind: "town" },
    { name: "Mehtar Lam", lon: 70.2089, lat: 34.6683, kind: "town" },
    { name: "Peshawar", lon: 71.5781, lat: 34.0153, kind: "town" },
    { name: "Konar", lon: 71.0, lat: 35.08, kind: "region" },
    { name: "Nurestan", lon: 70.72, lat: 35.35, kind: "region" },
    { name: "Nangarhar", lon: 70.7, lat: 34.16, kind: "region" },
    { name: "Laghman", lon: 70.02, lat: 34.8, kind: "region" },
    { name: "Badakhshan", lon: 70.65, lat: 35.95, kind: "region" }
  ];

  const statusEl = document.getElementById("konar-status");
  const compassEl = document.getElementById("konar-compass");
  const sheetButton = document.getElementById("konar-sheet");
  const valleyButton = document.getElementById("konar-valley");
  const satelliteButton = document.getElementById("konar-satellite");
  const reliefButton = document.getElementById("konar-relief");
  const labelsButton = document.getElementById("konar-labels");
  const boundariesButton = document.getElementById("konar-boundaries");
  const roadsButton = document.getElementById("konar-roads");
  const exagRange = document.getElementById("konar-exag-range");
  const exagValue = document.getElementById("konar-exag-value");
  const scaleEl = document.getElementById("konar-scale");
  const legendEl = document.getElementById("konar-legend");
  const scaleBar = document.getElementById("konar-scale-bar");
  const scaleLabel = document.getElementById("konar-scale-label");

  const SCALE_STEPS = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000];
  const SCALE_PX = 140;

  const embed = document.body.classList.contains("konar-embed");
  let viewer = null;
  let labelsOn = !embed;
  const labels = [];
  let surface = "satellite";
  let allowed = true;

  function say(text) {
    if (!text) {
      statusEl.hidden = true;
      statusEl.textContent = "";
      return;
    }
    statusEl.hidden = false;
    statusEl.textContent = text;
  }

  function fail(text) {
    say(text);
  }

  if (!window.Cesium) {
    fail("Cesium did not load.");
    return;
  }

  function press(button, on) {
    button.setAttribute("aria-pressed", on ? "true" : "false");
  }

  function destination(view) {
    const heading = Cesium.Math.toRadians(view.heading);
    const depression = Cesium.Math.toRadians(-view.pitch);
    const horiz = view.range * Math.cos(depression);
    const height = view.range * Math.sin(depression);
    const back = heading + Math.PI;
    const target = Cesium.Cartesian3.fromDegrees(view.lon, view.lat, 1600);
    const frame = Cesium.Transforms.eastNorthUpToFixedFrame(target);
    return Cesium.Matrix4.multiplyByPoint(
      frame,
      new Cesium.Cartesian3(horiz * Math.sin(back), horiz * Math.cos(back), height),
      new Cesium.Cartesian3()
    );
  }

  function showView(name, duration) {
    if (!viewer) {
      return;
    }
    const view = VIEWS[name];
    const options = {
      destination: destination(view),
      orientation: {
        heading: Cesium.Math.toRadians(view.heading),
        pitch: Cesium.Math.toRadians(view.pitch),
        roll: 0
      }
    };
    if (duration > 0) {
      viewer.camera.flyTo(Object.assign({ duration: duration }, options));
    } else {
      viewer.camera.setView(options);
    }
    press(sheetButton, name === "sheet");
    press(valleyButton, name === "valley");
  }

  function setExaggeration(value) {
    const factor = Number(value);
    viewer.scene.verticalExaggeration = factor;
    viewer.scene.verticalExaggerationRelativeHeight = 900;
    exagValue.textContent = factor.toFixed(1) + "×";
    viewer.scene.requestRender();
  }

  function applyLoop() {
    if (!viewer) {
      return;
    }
    const run = allowed && !document.hidden;
    viewer.useDefaultRenderLoop = run;
    if (run) {
      viewer.resize();
      viewer.scene.requestRender();
    }
  }

  async function addSatellite() {
    viewer.imageryLayers.removeAll();
    viewer.imageryLayers.add(Cesium.ImageryLayer.fromProviderAsync(
      Cesium.ArcGisMapServerImageryProvider.fromUrl(IMAGERY_URL)
    ));
    viewer.scene.globe.enableLighting = false;
    viewer.scene.light = new Cesium.SunLight();
    surface = "satellite";
    press(satelliteButton, true);
    press(reliefButton, false);
    viewer.scene.requestRender();
  }

  function showRelief() {
    viewer.imageryLayers.removeAll();
    viewer.imageryLayers.add(Cesium.ImageryLayer.fromProviderAsync(
      Cesium.ArcGisMapServerImageryProvider.fromUrl(HILLSHADE_URL)
    ));
    viewer.scene.globe.enableLighting = false;
    surface = "relief";
    press(satelliteButton, false);
    press(reliefButton, true);
    viewer.scene.requestRender();
  }

  function placeLabel(place) {
    const town = place.kind === "town";
    return viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(place.lon, place.lat),
      point: town ? {
        pixelSize: 10,
        color: Cesium.Color.fromCssColorString("#D99A5B"),
        outlineColor: Cesium.Color.fromCssColorString("#15150F"),
        outlineWidth: 1,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      } : undefined,
      label: {
        text: place.name,
        font: town ? "700 22px Lato, sans-serif" : "700 20px Lato, sans-serif",
        fillColor: Cesium.Color.fromCssColorString("#1C1A14"),
        showBackground: true,
        backgroundColor: Cesium.Color.fromCssColorString("#F4EFE2").withAlpha(0.92),
        backgroundPadding: new Cesium.Cartesian2(8, 5),
        style: Cesium.LabelStyle.FILL,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, town ? -12 : 0),
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scaleByDistance: new Cesium.NearFarScalar(40000, 1.1, 480000, 0.9)
      },
      show: labelsOn
    });
  }

  function setLabels(on) {
    if (!viewer) {
      return;
    }
    labelsOn = on;
    press(labelsButton, on);
    labels.forEach((entity) => {
      entity.show = on;
    });
    viewer.scene.requestRender();
  }

  function lineStyle(name, kind) {
    if (name === "boundaries") {
      return kind === "international"
        ? { width: 3, color: "#E24B32" }
        : { width: 2, color: "#F0A08A" };
    }
    return kind === "primary"
      ? { width: 2, color: "#F0C14A" }
      : { width: 3.5, color: "#F0C14A" };
  }

  function groundLines(feature) {
    const geometry = feature.geometry;
    if (!geometry) {
      return [];
    }
    if (geometry.type === "LineString") {
      return [geometry.coordinates];
    }
    if (geometry.type === "MultiLineString") {
      return geometry.coordinates;
    }
    return [];
  }

  const overlays = {
    boundaries: {
      url: "16_collaborative/boundaries.geojson",
      button: boundariesButton,
      primitive: null,
      promise: null,
      fail: "Boundaries did not load."
    },
    roads: {
      url: "16_collaborative/roads.geojson",
      button: roadsButton,
      primitive: null,
      promise: null,
      fail: "Roads did not load."
    }
  };

  function boundaryPositions(cartos, kind) {
    const factor = viewer.scene.verticalExaggeration || 1;
    const relative = viewer.scene.verticalExaggerationRelativeHeight || 0;
    const lift = kind === "international" ? 90 : 50;
    return cartos.map((carto) => {
      const height = Number.isFinite(carto.height) ? carto.height : relative;
      const exaggerated = relative + (height - relative) * factor + lift;
      return Cesium.Cartesian3.fromRadians(carto.longitude, carto.latitude, exaggerated);
    });
  }

  async function buildBoundaries(data) {
    const lines = [];
    data.features.forEach((feature) => {
      const kind = feature.properties.kind;
      groundLines(feature).forEach((line) => {
        if (line.length < 2) {
          return;
        }
        lines.push({
          kind: kind,
          cartos: line.map((pair) => Cesium.Cartographic.fromDegrees(pair[0], pair[1]))
        });
      });
    });
    const sample = lines.flatMap((line) => line.cartos);
    try {
      await Promise.race([
        Cesium.sampleTerrain(viewer.terrainProvider, 10, sample),
        new Promise(function (_, reject) {
          window.setTimeout(function () {
            reject(new Error("timeout"));
          }, 12000);
        })
      ]);
    } catch (error) {
      sample.forEach((carto) => {
        if (!Number.isFinite(carto.height)) {
          const globeHeight = viewer.scene.globe.getHeight(carto);
          carto.height = Number.isFinite(globeHeight) ? globeHeight : 1800;
        }
      });
    }
    const entities = lines.map((line) => {
      const style = lineStyle("boundaries", line.kind);
      const color = Cesium.Color.fromCssColorString(style.color);
      return viewer.entities.add({
        polyline: {
          positions: new Cesium.CallbackProperty(function () {
            return boundaryPositions(line.cartos, line.kind);
          }, false),
          width: style.width + 1.5,
          material: color,
          depthFailMaterial: color,
          arcType: Cesium.ArcType.NONE,
          clampToGround: false
        },
        show: false
      });
    });
    overlays.boundaries.lines = lines;
    overlays.boundaries.entities = entities;
  }

  function buildOverlay(name, data) {
    const instances = [];
    data.features.forEach((feature) => {
      const style = lineStyle(name, feature.properties.kind);
      const color = Cesium.ColorGeometryInstanceAttribute.fromColor(
        Cesium.Color.fromCssColorString(style.color)
      );
      groundLines(feature).forEach((line) => {
        if (line.length < 2) {
          return;
        }
        const flat = [];
        line.forEach((pair) => {
          flat.push(pair[0], pair[1]);
        });
        instances.push(new Cesium.GeometryInstance({
          geometry: new Cesium.GroundPolylineGeometry({
            positions: Cesium.Cartesian3.fromDegreesArray(flat),
            width: style.width
          }),
          attributes: { color: color }
        }));
      });
    });
    const primitive = new Cesium.GroundPolylinePrimitive({
      geometryInstances: instances,
      appearance: new Cesium.PolylineColorAppearance(),
      asynchronous: true
    });
    primitive.show = false;
    viewer.scene.groundPrimitives.add(primitive);
    return primitive;
  }

  async function setOverlay(name, on) {
    if (!viewer) {
      return;
    }
    const overlay = overlays[name];
    press(overlay.button, on);
    if (name === "boundaries" && !on) {
      legendEl.hidden = true;
    }
    if (!on) {
      if (overlay.primitive) {
        overlay.primitive.show = false;
      }
      if (overlay.entities) {
        overlay.entities.forEach((entity) => {
          entity.show = false;
        });
      }
      viewer.scene.requestRender();
      return;
    }
    if (!overlay.primitive && !overlay.entities) {
      if (!overlay.promise) {
        overlay.promise = fetch(overlay.url).then((response) => {
          if (!response.ok) {
            throw new Error(overlay.fail);
          }
          return response.json();
        }).then((data) => {
          if (name === "boundaries") {
            return buildBoundaries(data);
          }
          overlay.primitive = buildOverlay(name, data);
          return overlay.primitive;
        });
      }
      try {
        say("Loading " + name + "…");
        await overlay.promise;
        say("");
        if (overlay.button.getAttribute("aria-pressed") !== "true") {
          if (overlay.primitive) {
            overlay.primitive.show = false;
          }
          if (overlay.entities) {
            overlay.entities.forEach((entity) => {
              entity.show = false;
            });
          }
          return;
        }
      } catch (error) {
        overlay.promise = null;
        press(overlay.button, false);
        if (name === "boundaries") {
          legendEl.hidden = true;
        }
        fail(overlay.fail);
        return;
      }
    }
    if (overlay.primitive) {
      overlay.primitive.show = true;
    }
    if (overlay.entities) {
      overlay.entities.forEach((entity) => {
        entity.show = true;
      });
    }
    if (name === "boundaries" && overlay.button.getAttribute("aria-pressed") === "true") {
      legendEl.hidden = false;
    }
    viewer.scene.requestRender();
  }

  function groundAt(x, y) {
    const ray = viewer.camera.getPickRay(new Cesium.Cartesian2(x, y));
    if (!ray) {
      return undefined;
    }
    return viewer.scene.globe.pick(ray, viewer.scene);
  }

  function updateScale() {
    if (!viewer) {
      return;
    }
    const canvas = viewer.scene.canvas;
    const y = Math.max(48, canvas.clientHeight - (embed ? 52 : 156));
    const x = embed ? 12 : 16;
    const left = groundAt(x, y);
    const right = groundAt(x + SCALE_PX, y);
    if (!left || !right) {
      scaleEl.hidden = true;
      return;
    }
    const meters = Cesium.Cartesian3.distance(left, right);
    if (!isFinite(meters) || meters <= 0) {
      scaleEl.hidden = true;
      return;
    }
    const metersPerPx = meters / SCALE_PX;
    let chosen = SCALE_STEPS[0];
    SCALE_STEPS.forEach((step) => {
      if (step / metersPerPx <= SCALE_PX) {
        chosen = step;
      }
    });
    scaleBar.style.width = Math.max(28, chosen / metersPerPx).toFixed(1) + "px";
    scaleLabel.textContent = chosen >= 1000 ? (chosen / 1000) + " km" : chosen + " m";
    scaleEl.hidden = false;
  }

  async function start() {
    say("Loading terrain…");
    let terrainProvider;
    try {
      terrainProvider = await Cesium.ArcGISTiledElevationTerrainProvider.fromUrl(TERRAIN_URL);
      viewer = new Cesium.Viewer("konar-view", {
        animation: false,
        timeline: false,
        baseLayerPicker: false,
        geocoder: false,
        homeButton: false,
        sceneModePicker: false,
        navigationHelpButton: false,
        fullscreenButton: false,
        infoBox: false,
        selectionIndicator: false,
        skyBox: false,
        skyAtmosphere: false,
        baseLayer: false,
        terrainProvider: terrainProvider,
        contextOptions: {
          webgl: { alpha: false }
        }
      });
    } catch (error) {
      fail("Terrain did not load. The elevation service may be blocked on this network.");
      return;
    }

    viewer.scene.globe.cartographicLimitRectangle = BLOCK;
    viewer.scene.globe.showSkirts = true;
    viewer.scene.globe.depthTestAgainstTerrain = true;
    viewer.scene.globe.showGroundAtmosphere = false;
    viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#d7c4a4");
    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#15150F");
    viewer.scene.fog.enabled = false;
    if (viewer.scene.sun) {
      viewer.scene.sun.show = false;
    }
    if (viewer.scene.moon) {
      viewer.scene.moon.show = false;
    }
    viewer.scene.globe.maximumScreenSpaceError = 2;
    viewer.scene.screenSpaceCameraController.minimumZoomDistance = 4000;
    viewer.scene.screenSpaceCameraController.maximumZoomDistance = 900000;
    viewer.scene.screenSpaceCameraController.enableCollisionDetection = true;
    setExaggeration(exagRange.value);

    viewer.scene.postRender.addEventListener(() => {
      const degrees = -Cesium.Math.toDegrees(viewer.camera.heading);
      compassEl.style.transform = "rotate(" + degrees.toFixed(2) + "deg)";
    });

    let pending = 0;
    viewer.scene.globe.tileLoadProgressEvent.addEventListener((remaining) => {
      pending = remaining;
      if (remaining === 0) {
        if (statusEl.textContent === "Loading terrain…") {
          say("");
        }
        updateScale();
      }
    });

    PLACES.forEach((place) => {
      labels.push(placeLabel(place));
    });
    viewer.camera.percentageChanged = 0.01;
    viewer.camera.changed.addEventListener(updateScale);
    viewer.camera.moveEnd.addEventListener(updateScale);
    await addSatellite();
    showView(new URLSearchParams(location.search).get("view") === "valley" ? "valley" : "sheet", 0);

    window.setTimeout(() => {
      if (pending > 0 && statusEl.textContent === "Loading terrain…") {
        say("");
      }
    }, 8000);
  }

  sheetButton.addEventListener("click", () => showView("sheet", embed ? 0 : 1.6));
  valleyButton.addEventListener("click", () => showView("valley", embed ? 0 : 1.6));
  satelliteButton.addEventListener("click", () => {
    if (surface !== "satellite") {
      addSatellite();
    }
  });
  reliefButton.addEventListener("click", () => {
    if (surface !== "relief") {
      showRelief();
    }
  });
  labelsButton.addEventListener("click", () => setLabels(!labelsOn));
  boundariesButton.addEventListener("click", () => {
    const on = boundariesButton.getAttribute("aria-pressed") !== "true";
    setOverlay("boundaries", on);
  });
  roadsButton.addEventListener("click", () => {
    const on = roadsButton.getAttribute("aria-pressed") !== "true";
    setOverlay("roads", on);
  });
  exagRange.addEventListener("input", () => setExaggeration(exagRange.value));

  window.addEventListener("message", (event) => {
    if (!event.data || event.data.type !== "cts-embed-visible") {
      return;
    }
    allowed = Boolean(event.data.visible);
    applyLoop();
  });
  document.addEventListener("visibilitychange", applyLoop);
  window.addEventListener("resize", () => {
    if (viewer) {
      viewer.resize();
      updateScale();
    }
  });

  window.addEventListener("keydown", (event) => {
    if (embed || event.altKey || event.metaKey || event.ctrlKey) {
      return;
    }
    const tag = event.target && event.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA") {
      return;
    }
    if (event.key === "1") {
      showView("sheet", 1.2);
    } else if (event.key === "2") {
      showView("valley", 1.2);
    } else if (event.key === "l" || event.key === "L" || event.key === "n" || event.key === "N") {
      setLabels(!labelsOn);
    } else if (event.key === "b" || event.key === "B") {
      boundariesButton.click();
    } else if (event.key === "r" || event.key === "R") {
      roadsButton.click();
    }
  });

  start().catch((error) => {
    fail(error && error.message ? error.message : "The map did not finish loading.");
  });
})();
