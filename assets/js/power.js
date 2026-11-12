(function () {
  const DATA_URL = new URL("12_power/frames.json", window.location.href);
  const map = L.map("power-map", {
    zoomControl: false,
    attributionControl: false,
    scrollWheelZoom: true,
  });
  L.control.zoom({ position: "topright" }).addTo(map);

  const dateEl = document.getElementById("power-date");
  const statsEl = document.getElementById("power-stats");
  const deckEl = document.getElementById("power-deck");
  const creditEl = document.getElementById("power-credit");
  const slider = document.getElementById("power-slider");
  const playButton = document.getElementById("power-play");
  const spark = document.getElementById("power-spark");

  let frames = [];
  let gainedLayer = null;
  let retakenLayer = null;
  let timer = null;

  function formatKm(value) {
    const rounded = Math.round(value);
    const sign = rounded > 0 ? "+" : "";
    return sign + rounded.toLocaleString("en-US") + " km²";
  }

  function styleFor(kind) {
    if (kind === "ukraine") {
      return { color: "#241F1A", weight: 1.2, fillColor: "#E4DDD2", fillOpacity: 1 };
    }
    if (kind === "claim") {
      return { color: "#241F1A", weight: 1, fillColor: "#C6A15A", fillOpacity: 0.95 };
    }
    if (kind === "held") {
      return { color: "#241F1A", weight: 0, fillColor: "#9A8F82", fillOpacity: 0.96, stroke: false };
    }
    if (kind === "gain") {
      return { color: "#241F1A", weight: 0.4, fillColor: "#A15C38", fillOpacity: 0.95 };
    }
    return { color: "#241F1A", weight: 0.4, fillColor: "#3E6B58", fillOpacity: 0.95 };
  }

  function showFrame(index) {
    const frame = frames[index];
    if (!frame) {
      return;
    }
    if (gainedLayer) {
      map.removeLayer(gainedLayer);
      gainedLayer = null;
    }
    if (retakenLayer) {
      map.removeLayer(retakenLayer);
      retakenLayer = null;
    }
    if (frame.gained) {
      gainedLayer = L.geoJSON(frame.gained, { style: styleFor("gain") }).addTo(map);
    }
    if (frame.retaken) {
      retakenLayer = L.geoJSON(frame.retaken, { style: styleFor("retaken") }).addTo(map);
    }
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
    const nets = frames.map((frame) => frame.gained_km2 - frame.retaken_km2);
    const min = Math.min(0, ...nets);
    const max = Math.max(0, ...nets);
    const span = max - min || 1;
    const xAt = (index) => (index / (frames.length - 1)) * (width - 8) + 4;
    const yAt = (value) => 4 + ((max - value) / span) * (height - 10);
    ctx.beginPath();
    ctx.strokeStyle = "rgba(36, 31, 26, 0.35)";
    ctx.moveTo(4, yAt(0));
    ctx.lineTo(width - 4, yAt(0));
    ctx.stroke();
    ctx.beginPath();
    ctx.strokeStyle = "#241F1A";
    ctx.lineWidth = 1.4;
    nets.forEach((value, index) => {
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
    }, 800);
  });

  slider.addEventListener("input", function () {
    stop();
    showFrame(Number(slider.value));
  });

  window.addEventListener("resize", function () {
    drawSpark(Number(slider.value));
  });

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
      L.geoJSON(data.ukraine, { style: styleFor("ukraine") }).addTo(map);
      L.geoJSON({
        type: "FeatureCollection",
        features: (data.claim || []).map(function (item) {
          return { type: "Feature", properties: { name: item.name }, geometry: item.geometry };
        }),
      }, { style: styleFor("claim") }).addTo(map);
      if (data.held) {
        L.geoJSON(data.held, { style: styleFor("held") }).addTo(map);
      }
      (data.cities || []).forEach(function (city) {
        const marker = L.circleMarker([city.lat, city.lon], {
          radius: 3,
          color: "#241F1A",
          weight: 1,
          fillColor: "#F3F0EA",
          fillOpacity: 1,
        }).addTo(map);
        marker.bindTooltip(city.name, {
          permanent: Boolean(city.label),
          direction: "right",
          className: "power-city",
          offset: [6, 0],
        });
      });
      const ukraineLayer = L.geoJSON(data.ukraine);
      map.fitBounds(ukraineLayer.getBounds(), {
        paddingTopLeft: [28, 150],
        paddingBottomRight: [28, 160],
      });
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
        "The time map needs 2026/12_power/frames.json. From the repository root, run python scripts/build_day12_power.py.";
      creditEl.textContent = "Source assessments: DeepStateMap.live.";
    });
})();
