(function () {
  const embed = document.body.classList.contains("ix-embed");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const pageUrl = new URL(".", window.location.href);

  const deckEl = document.getElementById("ix-deck");
  const detailEl = document.getElementById("ix-detail");
  const yearsEl = document.getElementById("ix-years");
  const nameEl = document.getElementById("ix-name");
  const creditEl = document.getElementById("ix-credit");
  const titleEl = document.getElementById("ix-title");
  const day12El = document.getElementById("ix-day12");
  const slider = document.getElementById("ix-slider");
  const playButton = document.getElementById("ix-play");
  const prevButton = document.getElementById("ix-prev");
  const nextButton = document.getElementById("ix-next");

  const map = new maplibregl.Map({
    container: "ix-map",
    attributionControl: false,
    style: new URL("13_interactions/human-geography-dark.json", pageUrl).href,
    bounds: [[-12, 34], [46, 71]],
    fitBoundsOptions: { padding: padding() },
    maxZoom: 12,
  });

  if (!embed) {
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  }

  let episodes = [];
  let index = 0;
  let timer = null;
  let parentVisible = !embed;
  let scene = null;
  let settled = true;
  let revealStart = 0;
  let flashStart = 0;
  let flowRaf = 0;
  const markers = [];
  const DRAW_MS = 1100;
  const FLOW_MS = 2600;
  const FLASH_MS = 3600;

  function padding() {
    if (embed) {
      return { top: 52, bottom: 40, left: 14, right: 14 };
    }
    if (window.innerWidth < 720) {
      return { top: 120, bottom: 168, left: 14, right: 14 };
    }
    return { top: 24, bottom: 150, left: 440, right: 28 };
  }

  function widthFor(people) {
    if (!people) {
      return 2;
    }
    return Math.min(12, 1.15 + Math.sqrt(people / 120000));
  }

  function arc(from, to, bend) {
    const dx = to[0] - from[0];
    const dy = to[1] - from[1];
    const len = Math.hypot(dx, dy) || 1;
    const offset = bend == null ? 1.2 : bend;
    const cx = (from[0] + to[0]) / 2 + (-dy / len) * offset;
    const cy = (from[1] + to[1]) / 2 + (dx / len) * offset;
    const points = [];
    const steps = 28;
    for (let i = 0; i <= steps; i += 1) {
      const t = i / steps;
      const u = 1 - t;
      points.push([
        u * u * from[0] + 2 * u * t * cx + t * t * to[0],
        u * u * from[1] + 2 * u * t * cy + t * t * to[1],
      ]);
    }
    return points;
  }

  function collection(features) {
    return { type: "FeatureCollection", features: features };
  }

  function asFeatures(items, mapFeature) {
    return collection((items || []).map(mapFeature));
  }

  function empty() {
    return collection([]);
  }

  function easeOut(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function trimCoords(coords, t) {
    if (!coords || coords.length < 2) {
      return coords || [];
    }
    if (t >= 1) {
      return coords;
    }
    const span = coords.length - 1;
    const x = Math.max(0, t) * span;
    const i = Math.min(span - 1, Math.floor(x));
    const f = x - i;
    const out = coords.slice(0, i + 1);
    const start = coords[i];
    const end = coords[i + 1];
    out.push([start[0] + (end[0] - start[0]) * f, start[1] + (end[1] - start[1]) * f]);
    return out;
  }

  function pointAlong(coords, t) {
    const span = coords.length - 1;
    const x = Math.max(0, Math.min(1, t)) * span;
    const i = Math.min(span - 1, Math.floor(x));
    const f = x - i;
    const start = coords[i];
    const end = coords[i + 1];
    return [start[0] + (end[0] - start[0]) * f, start[1] + (end[1] - start[1]) * f];
  }

  function beadCount(people) {
    if (!people) {
      return 2;
    }
    return Math.max(2, Math.min(7, Math.round(Math.sqrt(people / 180000))));
  }

  function motionOn() {
    return !reduceMotion && !document.hidden && (!embed || parentVisible);
  }

  function addLabel(lngLat, text, className, store, anchor) {
    if (!lngLat || !text) {
      return;
    }
    const el = document.createElement("div");
    el.className = className;
    el.textContent = text;
    const marker = new maplibregl.Marker({ element: el, anchor: anchor || "bottom" })
      .setLngLat(lngLat)
      .addTo(map);
    store.push(marker);
  }

  function clearLabels() {
    while (markers.length) {
      markers.pop().remove();
    }
  }

  function paragraph(text, className) {
    const p = document.createElement("p");
    if (className) {
      p.className = className;
    }
    p.textContent = text;
    return p;
  }

  function heading(text) {
    const h = document.createElement("h2");
    h.textContent = text;
    return h;
  }

  function fillDetail(episode) {
    detailEl.replaceChildren();
    if (episode.moves && episode.moves.length) {
      detailEl.appendChild(heading("People"));
      episode.moves.forEach(function (move) {
        detailEl.appendChild(paragraph(move.text));
      });
    }
    const borderLines = (episode.borders || []).map(function (border) {
      return border.detail;
    }).filter(Boolean);
    if (borderLines.length) {
      detailEl.appendChild(heading("Borders"));
      borderLines.forEach(function (note) {
        detailEl.appendChild(paragraph(note));
      });
    }
    (episode.notes || []).forEach(function (note) {
      detailEl.appendChild(paragraph(note));
    });
    if (episode.link) {
      const link = document.createElement("a");
      link.href = episode.link.href;
      link.textContent = episode.link.label;
      const p = document.createElement("p");
      p.appendChild(link);
      detailEl.appendChild(p);
    }
    if (episode.source) {
      detailEl.appendChild(paragraph(episode.source, "ix-source"));
    }
  }

  function show(nextIndex, animate) {
    const episode = episodes[nextIndex];
    if (!episode || !map.getSource("moves")) {
      return;
    }
    index = nextIndex;
    scene = {
      segments: borderSegments(episode.borders || []),
      moves: (episode.moves || []).map(function (move) {
        return {
          coords: arc(move.from, move.to, move.bend),
          width: widthFor(move.people),
          people: move.people,
          to: move.to,
        };
      }),
    };
    settled = false;
    revealStart = motionOn() ? performance.now() : performance.now() - DRAW_MS;
    flashStart = revealStart + DRAW_MS;

    map.getSource("border-lines").setData(empty());
    map.getSource("moves").setData(empty());
    map.getSource("beads").setData(empty());
    map.getSource("move-ends").setData(empty());
    map.setPaintProperty("border-halo", "line-opacity", 0);

    clearLabels();
    scene.segments.forEach(function (segment) {
      addLabel(segment.at, segment.label, "ix-label", markers);
    });
    paint(performance.now());
    kick();

    yearsEl.textContent = episode.years;
    nameEl.textContent = episode.title;
    deckEl.textContent = episode.deck;
    if (embed) {
      titleEl.textContent = episode.title;
    }
    fillDetail(episode);
    slider.value = String(index);
    slider.setAttribute("aria-valuetext", episode.years + ", " + episode.title);

    if (episode.link) {
      day12El.hidden = false;
      day12El.href = episode.link.href;
      day12El.textContent = "Day 12 →";
    } else {
      day12El.hidden = true;
    }

    const [[west, south], [east, north]] = episode.bounds;
    const dx = (east - west) * 0.08;
    const dy = (north - south) * 0.06;
    map.fitBounds([[west - dx, south - dy], [east + dx, north + dy]], {
      padding: padding(),
      duration: animate && !reduceMotion ? 1100 : 0,
      maxZoom: episode.maxZoom || 5.2,
    });
  }

  function borderSegments(borders) {
    const segments = [];
    borders.forEach(function (border) {
      if (border.old && border.old.coordinates) {
        segments.push({
          role: "old",
          kind: border.kind,
          coords: border.old.coordinates,
          label: border.old.label,
          at: border.old.at,
        });
      }
      if (border.new && border.new.coordinates) {
        segments.push({
          role: "new",
          kind: border.kind,
          coords: border.new.coordinates,
          label: border.new.label,
          at: border.new.at,
        });
      }
    });
    return segments;
  }

  function lineFeatures(eased) {
    const features = [];
    scene.segments.forEach(function (segment) {
      const grown = trimCoords(segment.coords, eased);
      if (grown.length < 2) {
        return;
      }
      features.push({
        type: "Feature",
        properties: { role: segment.role, kind: segment.kind },
        geometry: { type: "LineString", coordinates: grown },
      });
    });
    return collection(features);
  }

  function flashLevel(now) {
    if (reduceMotion || !scene.segments.length) {
      return 0;
    }
    const elapsed = now - flashStart;
    if (elapsed < 0 || elapsed > FLASH_MS) {
      return 0;
    }
    const phase = (elapsed / FLASH_MS) * 3;
    return Math.pow(Math.sin((phase % 1) * Math.PI), 1.15);
  }

  function updateTracks(eased) {
    const tracks = [];
    scene.moves.forEach(function (move) {
      const grown = trimCoords(move.coords, eased);
      if (grown.length < 2) {
        return;
      }
      tracks.push({
        type: "Feature",
        properties: { width: move.width },
        geometry: { type: "LineString", coordinates: grown },
      });
    });
    map.getSource("moves").setData(collection(tracks));
    if (eased >= 1) {
      map.getSource("move-ends").setData(collection(scene.moves.map(function (move) {
        return {
          type: "Feature",
          properties: {},
          geometry: { type: "Point", coordinates: move.to },
        };
      })));
    }
  }

  function updateBeads(now) {
    const phase = (now % FLOW_MS) / FLOW_MS;
    const beads = [];
    scene.moves.forEach(function (move) {
      const count = beadCount(move.people);
      const radius = Math.max(2.4, move.width * 0.5);
      for (let i = 0; i < count; i += 1) {
        beads.push({
          type: "Feature",
          properties: { radius: radius },
          geometry: {
            type: "Point",
            coordinates: pointAlong(move.coords, (phase + i / count) % 1),
          },
        });
      }
    });
    map.getSource("beads").setData(collection(beads));
  }

  function paint(now) {
    if (!scene || !map.getSource("moves")) {
      return;
    }
    const raw = reduceMotion ? 1 : Math.min(1, (now - revealStart) / DRAW_MS);
    const eased = easeOut(raw);
    if (!settled) {
      map.getSource("border-lines").setData(lineFeatures(eased));
      updateTracks(eased);
      if (eased >= 1) {
        settled = true;
        flashStart = now;
      }
    }
    if (settled) {
      const flash = flashLevel(now);
      map.setPaintProperty("border-halo", "line-opacity", flash);
      map.setPaintProperty("border-halo", "line-width", 7 + flash * 10);
    }
    if (settled && scene.moves.length && motionOn()) {
      updateBeads(now);
    }
  }

  function tick(now) {
    flowRaf = 0;
    paint(now);
    const drawing = !settled;
    const flowing = scene && scene.moves.length > 0;
    const flashing = settled && scene && scene.segments.length > 0 && (now - flashStart) <= FLASH_MS;
    if (motionOn() && (drawing || flowing || flashing)) {
      flowRaf = requestAnimationFrame(tick);
    }
  }

  function kick() {
    if (motionOn() && scene && !flowRaf) {
      flowRaf = requestAnimationFrame(tick);
    }
  }

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    playButton.textContent = "Play";
    playButton.setAttribute("aria-pressed", "false");
  }

  function play() {
    stop();
    timer = setInterval(function () {
      show((index + 1) % episodes.length, true);
    }, embed ? 5200 : 6800);
    playButton.textContent = "Pause";
    playButton.setAttribute("aria-pressed", "true");
  }

  function setPlaying(shouldPlay) {
    if (shouldPlay) {
      play();
    } else {
      stop();
    }
  }

  function addLayers() {
    map.addSource("border-lines", { type: "geojson", data: empty() });
    map.addSource("moves", { type: "geojson", data: empty() });
    map.addSource("beads", { type: "geojson", data: empty() });
    map.addSource("move-ends", { type: "geojson", data: empty() });

    map.addLayer({
      id: "border-halo",
      type: "line",
      source: "border-lines",
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": [
          "case",
          ["==", ["get", "role"], "old"], "#F7F4EE",
          ["==", ["get", "kind"], "defacto"], "#F6E2A8",
          "#FFD0B8",
        ],
        "line-width": 5,
        "line-opacity": 0,
        "line-blur": 1.2,
      },
    });
    map.addLayer({
      id: "border-old",
      type: "line",
      source: "border-lines",
      filter: ["==", ["get", "role"], "old"],
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#E7E2D8",
        "line-width": 1.8,
        "line-dasharray": [1.5, 1.1],
      },
    });
    map.addLayer({
      id: "border-new",
      type: "line",
      source: "border-lines",
      filter: ["==", ["get", "role"], "new"],
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": ["match", ["get", "kind"], "defacto", "#E7C56A", "#F0A07A"],
        "line-width": 2.6,
      },
    });
    map.addLayer({
      id: "moves",
      type: "line",
      source: "moves",
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#7EC8C3",
        "line-width": ["get", "width"],
        "line-opacity": 0.72,
      },
    });
    map.addLayer({
      id: "beads",
      type: "circle",
      source: "beads",
      paint: {
        "circle-radius": ["get", "radius"],
        "circle-color": "#E7FFFB",
        "circle-opacity": 0.95,
        "circle-stroke-color": "#14171c",
        "circle-stroke-width": 1,
      },
    });
    map.addLayer({
      id: "move-ends",
      type: "circle",
      source: "move-ends",
      paint: {
        "circle-radius": 3.4,
        "circle-color": "#7EC8C3",
        "circle-stroke-color": "#14171c",
        "circle-stroke-width": 1,
      },
    });
  }

  map.on("load", function () {
    addLayers();
    fetch(new URL("13_interactions/episodes.json", pageUrl)).then(function (response) {
      if (!response.ok) {
        throw new Error("frames");
      }
      return response.json();
    }).then(function (payload) {
      episodes = payload.episodes;
      slider.max = String(episodes.length - 1);
      creditEl.appendChild(document.createTextNode("Basemap: Esri, TomTom, Garmin, FAO, NOAA, USGS, © OpenStreetMap contributors, and the GIS User Community. "));
      const notes = document.createElement("a");
      notes.href = "13_interactions/NOTES.md";
      notes.textContent = "Notes and sources";
      creditEl.appendChild(notes);
      creditEl.appendChild(document.createTextNode(". Transfers and arrows are simplified."));
      show(0, false);
      if (embed && !reduceMotion) {
        setPlaying(parentVisible);
      }
    }).catch(function () {
      deckEl.textContent = "The frames did not load.";
    });
  });

  playButton.addEventListener("click", function () {
    setPlaying(playButton.getAttribute("aria-pressed") !== "true");
  });
  prevButton.addEventListener("click", function () {
    if (!episodes.length) {
      return;
    }
    stop();
    show((index - 1 + episodes.length) % episodes.length, true);
  });
  nextButton.addEventListener("click", function () {
    if (!episodes.length) {
      return;
    }
    stop();
    show((index + 1) % episodes.length, true);
  });
  slider.addEventListener("input", function () {
    stop();
    show(Number(slider.value), true);
  });

  window.addEventListener("keydown", function (event) {
    if (embed || event.altKey || event.metaKey || event.ctrlKey) {
      return;
    }
    const tag = event.target && event.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA") {
      return;
    }
    if (event.key === "ArrowRight") {
      nextButton.click();
    } else if (event.key === "ArrowLeft") {
      prevButton.click();
    } else if (event.key === " ") {
      event.preventDefault();
      playButton.click();
    }
  });

  window.addEventListener("message", function (event) {
    if (!event.data || event.data.type !== "cts-embed-visible") {
      return;
    }
    parentVisible = Boolean(event.data.visible);
    if (embed && !reduceMotion) {
      setPlaying(parentVisible && !document.hidden);
    }
    kick();
  });

  document.addEventListener("visibilitychange", function () {
    kick();
  });

  window.addEventListener("resize", function () {
    map.resize();
  });
})();
