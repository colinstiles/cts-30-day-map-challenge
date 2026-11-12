(function () {
  const DATA_URL = new URL("12_power/frames.json", window.location.href);
  const dateEl = document.getElementById("power-date");
  const statsEl = document.getElementById("power-stats");
  const deckEl = document.getElementById("power-deck");
  const creditEl = document.getElementById("power-credit");
  const slider = document.getElementById("power-slider");
  const playButton = document.getElementById("power-play");
  const spark = document.getElementById("power-spark");
  const legendHeld = document.getElementById("legend-held");

  const map = new maplibregl.Map({
    container: "power-map",
    attributionControl: false,
    style: {
      version: 8,
      sources: {},
      layers: [
        {
          id: "paper",
          type: "background",
          paint: { "background-color": "#F3F0EA" },
        },
      ],
    },
    bounds: [[22.1, 44.2], [40.3, 52.4]],
    fitBoundsOptions: { padding: { top: 150, bottom: 170, left: 28, right: 28 } },
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

  let frames = [];
  let timer = null;
  const markers = [];

  function formatKm(value) {
    const rounded = Math.round(value);
    const sign = rounded > 0 ? "+" : "";
    return sign + rounded.toLocaleString("en-US") + " km²";
  }

  function asFeature(geometry) {
    if (!geometry) {
      return { type: "FeatureCollection", features: [] };
    }
    return { type: "Feature", properties: {}, geometry: geometry };
  }

  function showFrame(index) {
    const frame = frames[index];
    if (!frame || !map.getSource("gained")) {
      return;
    }
    map.getSource("gained").setData(asFeature(frame.gained));
    map.getSource("retaken").setData(asFeature(frame.retaken));
    dateEl.textContent = frame.date;
    const net = frame.gained_km2 - frame.retaken_km2;
    statsEl.textContent =
      "Gained " + formatKm(frame.gained_km2).replace("+", "") +
      " · Retaken " + formatKm(frame.retaken_km2).replace("+", "") +
      " · Net " + formatKm(net);
    drawSpark(index);
  }

  function drawSpark(activeIndex) {
    const ctx = spark.getContext("2d");
    const width = spark.clientWidth || 300;
    const height = 42;
    const ratio = window.devicePixelRatio || 1;
    spark.width = Math.round(width * ratio);
    spark.height = Math.round(height * ratio);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    if (frames.length < 2) {
      return;
    }
    const nets = frames.map(function (frame) {
      return frame.gained_km2 - frame.retaken_km2;
    });
    const min = Math.min(0, ...nets);
    const max = Math.max(0, ...nets);
    const span = max - min || 1;
    const xAt = function (index) {
      return (index / (frames.length - 1)) * (width - 8) + 4;
    };
    const yAt = function (value) {
      return 4 + ((max - value) / span) * (height - 10);
    };
    ctx.beginPath();
    ctx.strokeStyle = "rgba(36, 31, 26, 0.35)";
    ctx.moveTo(4, yAt(0));
    ctx.lineTo(width - 4, yAt(0));
    ctx.stroke();
    ctx.beginPath();
    ctx.strokeStyle = "#241F1A";
    ctx.lineWidth = 1.4;
    nets.forEach(function (value, index) {
      const x = xAt(index);
      const y = yAt(value);
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
    ctx.fillStyle = "#A15C38";
    ctx.beginPath();
    ctx.arc(xAt(activeIndex), yAt(nets[activeIndex]), 3.2, 0, Math.PI * 2);
    ctx.fill();
  }

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    playButton.textContent = "Play";
    playButton.setAttribute("aria-pressed", "false");
  }

  playButton.addEventListener("click", function () {
    if (timer) {
      stop();
      return;
    }
    playButton.textContent = "Pause";
    playButton.setAttribute("aria-pressed", "true");
    timer = setInterval(function () {
      const next = Number(slider.value) + 1;
      if (next >= frames.length) {
        stop();
        return;
      }
      slider.value = String(next);
      showFrame(next);
    }, 700);
  });

  slider.addEventListener("input", function () {
    stop();
    showFrame(Number(slider.value));
  });

  window.addEventListener("resize", function () {
    map.resize();
    drawSpark(Number(slider.value));
  });

  function addLayers(data) {
    const claim = {
      type: "FeatureCollection",
      features: (data.claim || [])
        .filter(function (item) {
          return item.geometry;
        })
        .map(function (item) {
          return {
            type: "Feature",
            properties: { name: item.name },
            geometry: item.geometry,
          };
        }),
    };
    const sources = {
      ukraine: asFeature(data.ukraine),
      claim: claim,
      held: asFeature(data.held),
      retaken: { type: "FeatureCollection", features: [] },
      gained: { type: "FeatureCollection", features: [] },
    };
    Object.keys(sources).forEach(function (id) {
      map.addSource(id, { type: "geojson", data: sources[id] });
    });
    map.addLayer({
      id: "ukraine-fill",
      type: "fill",
      source: "ukraine",
      paint: { "fill-color": "#E4DDD2" },
    });
    map.addLayer({
      id: "claim-fill",
      type: "fill",
      source: "claim",
      paint: { "fill-color": "#C6A15A", "fill-opacity": 0.95 },
    });
    map.addLayer({
      id: "held-fill",
      type: "fill",
      source: "held",
      paint: { "fill-color": "#9A8F82", "fill-opacity": 0.96 },
    });
    map.addLayer({
      id: "retaken-fill",
      type: "fill",
      source: "retaken",
      paint: { "fill-color": "#3E6B58", "fill-opacity": 0.95 },
    });
    map.addLayer({
      id: "gained-fill",
      type: "fill",
      source: "gained",
      paint: { "fill-color": "#A15C38", "fill-opacity": 0.95 },
    });
    map.addLayer({
      id: "ukraine-line",
      type: "line",
      source: "ukraine",
      paint: { "line-color": "#241F1A", "line-width": 1.1 },
    });
    map.addLayer({
      id: "claim-line",
      type: "line",
      source: "claim",
      paint: { "line-color": "#241F1A", "line-width": 0.8 },
    });

    (data.cities || []).forEach(function (city) {
      const el = document.createElement("div");
      el.className = "power-marker";
      if (city.label) {
        const label = document.createElement("span");
        label.textContent = city.name;
        el.appendChild(label);
      }
      markers.push(new maplibregl.Marker({ element: el }).setLngLat([city.lon, city.lat]).addTo(map));
    });
  }

  map.on("load", function () {
    fetch(DATA_URL)
      .then(function (response) {
        if (!response.ok) {
          throw new Error("missing frames");
        }
        return response.json();
      })
      .then(function (data) {
        frames = data.frames || [];
        if (!frames.length) {
          throw new Error("empty frames");
        }
        addLayers(data);
        if (legendHeld) {
          legendHeld.textContent = "Held on " + data.baseline;
        }
        slider.max = String(frames.length - 1);
        slider.value = String(frames.length - 1);
        const oblasts = (data.oblasts || [])
          .map(function (row) {
            return row.name + " " + row.held_pct.toFixed(0) + "%";
          })
          .join(" · ");
        deckEl.textContent =
          "From " + data.baseline + " to " + data.end +
          ". Ochre still showing is claimed and not held. " +
          oblasts;
        creditEl.innerHTML =
          "Assessed control © <a href=\"https://deepstatemap.live/\" target=\"_blank\" rel=\"noopener noreferrer\">DeepStateMap.live</a>. " +
          "Outlines: geoBoundaries, CC BY 4.0. An assessment, not a survey. " +
          "Changes thinner than " + data.opening_m + " m are left off.";
        showFrame(frames.length - 1);
      })
      .catch(function () {
        deckEl.textContent =
          "The time map needs 2026/12_power/frames.json. From the repository root, run python3 scripts/build_day12_power.py --weekly-map.";
        creditEl.textContent = "Source assessments: DeepStateMap.live.";
      });
  });
})();
