/* Tennessee InFORM fire-occurrence timelapse for Day 4 (Clusters).
   Queries NIFC InFORM live, then animates a MapLibre heatmap over time. */
(function () {
  "use strict";

  var SERVICE_URL =
    "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/InFORM_FireOccurrence_Public/FeatureServer/0/query";
  var PAGE_SIZE = 2000;
  var CACHE_KEY = "cts-inform-tn-fires-v1";
  var CACHE_TTL_MS = 12 * 60 * 60 * 1000;
  var DAY_MS = 86400000;
  var COMPLETE_YEAR = 2021;
  var PLAY_MS = 70;
  var EMBED_PLAY_MS = 180;
  var STEP_DAYS = 7;
  var RECENT_DAYS = 14;
  var TN = { west: -90.55, south: 34.82, east: -81.4, north: 36.82 };

  var embed = new URLSearchParams(window.location.search).get("embed") === "1";
  var map;
  var features = [];
  var playing = false;
  var rafId = 0;
  var lastTick = 0;
  var currentT = 0;
  var minT = 0;
  var maxT = 0;
  var rangeMinT = 0;
  var windowDays = 90;
  var typeFilter = "ALL";
  var era = "recent";
  var speed = embed ? 0.5 : 1;
  var parentVisible = true;

  var els = {};

  function $(id) {
    return document.getElementById(id);
  }

  function formatDate(ms) {
    return new Date(ms).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      timeZone: "America/New_York"
    });
  }

  function typeLabel(code) {
    return code === "RX" ? "Prescribed fire" : "Wildfire";
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function acresOf(attrs) {
    var finalAcres = attrs.FinalAcres;
    var size = attrs.IncidentSize;
    if (finalAcres != null && finalAcres > 0) {
      return finalAcres;
    }
    return size == null ? 0 : size;
  }

  function readCache() {
    try {
      var raw = sessionStorage.getItem(CACHE_KEY);
      if (!raw) {
        return null;
      }
      var cached = JSON.parse(raw);
      if (Date.now() - cached.saved > CACHE_TTL_MS || !cached.features) {
        return null;
      }
      return cached.features;
    } catch (err) {
      return null;
    }
  }

  function writeCache(rows) {
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify({ saved: Date.now(), features: rows }));
    } catch (err) {
      /* quota or private mode — live data still works */
    }
  }

  async function fetchPage(offset) {
    var params = new URLSearchParams({
      where: "POOState='US-TN' AND FireDiscoveryDateTime IS NOT NULL",
      outFields: "IncidentName,FireDiscoveryDateTime,IncidentTypeCategory,FinalAcres,IncidentSize,POOCounty",
      outSR: "4326",
      f: "json",
      resultRecordCount: String(PAGE_SIZE),
      resultOffset: String(offset),
      orderByFields: "FireDiscoveryDateTime"
    });
    var response = await fetch(SERVICE_URL + "?" + params.toString());
    if (!response.ok) {
      throw new Error("InFORM query failed (" + response.status + ")");
    }
    return response.json();
  }

  async function loadFires() {
    var cached = readCache();
    if (cached && cached.length) {
      return cached;
    }
    var rows = [];
    var offset = 0;
    while (true) {
      var page = await fetchPage(offset);
      var batch = page.features || [];
      for (var i = 0; i < batch.length; i += 1) {
        var rec = batch[i];
        var geom = rec.geometry;
        var attrs = rec.attributes || {};
        if (!geom || attrs.FireDiscoveryDateTime == null) {
          continue;
        }
        rows.push({
          type: "Feature",
          geometry: { type: "Point", coordinates: [geom.x, geom.y] },
          properties: {
            t: attrs.FireDiscoveryDateTime,
            n: attrs.IncidentName || "Unnamed incident",
            k: attrs.IncidentTypeCategory || "WF",
            a: acresOf(attrs),
            c: attrs.POOCounty || ""
          }
        });
      }
      if (!page.exceededTransferLimit || batch.length === 0) {
        break;
      }
      offset += PAGE_SIZE;
    }
    writeCache(rows);
    return rows;
  }

  function collection() {
    return { type: "FeatureCollection", features: features };
  }

  function styleSpec() {
    return {
      version: 8,
      sources: {
        esri: {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          ],
          tileSize: 256,
          attribution: "Tiles © Esri"
        }
      },
      layers: [
        { id: "bg", type: "background", paint: { "background-color": "#15150F" } },
        { id: "esri", type: "raster", source: "esri", paint: { "raster-opacity": 0.88 } }
      ]
    };
  }

  function heatColor(kind) {
    if (kind === "RX") {
      return [
        "interpolate",
        ["linear"],
        ["heatmap-density"],
        0,
        "rgba(0,0,0,0)",
        0.15,
        "rgba(40, 70, 40, 0.15)",
        0.35,
        "rgba(90, 140, 70, 0.45)",
        0.55,
        "#9CBB74",
        0.8,
        "#D9E8B8",
        1,
        "#F2EFE4"
      ];
    }
    return [
      "interpolate",
      ["linear"],
      ["heatmap-density"],
      0,
      "rgba(0,0,0,0)",
      0.12,
      "rgba(80, 20, 8, 0.2)",
      0.3,
      "rgba(180, 55, 12, 0.55)",
      0.5,
      "#E85D04",
      0.72,
      "#FFB703",
      1,
      "#FFF6E0"
    ];
  }

  function addFireLayers() {
    map.addSource("fires", { type: "geojson", data: collection() });

    ["WF", "RX"].forEach(function (kind) {
      var heatId = "heat-" + kind;
      var dotId = "dots-" + kind;
      var recentId = "recent-" + kind;
      map.addLayer({
        id: heatId,
        type: "heatmap",
        source: "fires",
        filter: ["==", ["get", "k"], "__none__"],
        paint: {
          "heatmap-weight": 1,
          "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 5, 0.55, 9, 1.35],
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 5, 16, 9, 34],
          "heatmap-opacity": 0.92,
          "heatmap-color": heatColor(kind)
        }
      });
      if (embed) {
        return;
      }
      map.addLayer({
        id: dotId,
        type: "circle",
        source: "fires",
        filter: ["==", ["get", "k"], "__none__"],
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 1.6, 10, 4.5],
          "circle-color": kind === "RX" ? "#9CBB74" : "#E85D04",
          "circle-opacity": 0.55,
          "circle-stroke-width": 0
        }
      });
      map.addLayer({
        id: recentId,
        type: "circle",
        source: "fires",
        filter: ["==", ["get", "k"], "__none__"],
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 3.2, 10, 7],
          "circle-color": kind === "RX" ? "#E8F5C8" : "#FFB703",
          "circle-opacity": 0.95,
          "circle-blur": 0.15,
          "circle-stroke-color": "#15150F",
          "circle-stroke-width": 0.6
        }
      });
    });
  }

  function windowStart() {
    if (windowDays <= 0) {
      return rangeMinT;
    }
    return Math.max(rangeMinT, currentT - windowDays * DAY_MS);
  }

  function matchesType(kind) {
    return typeFilter === "ALL" || typeFilter === kind;
  }

  function timeFilter(kind, start, end) {
    if (!matchesType(kind)) {
      return ["==", ["get", "k"], "__none__"];
    }
    return ["all", ["==", ["get", "k"], kind], [">=", ["get", "t"], start], ["<=", ["get", "t"], end]];
  }

  function countVisible(start, end) {
    var n = 0;
    for (var i = 0; i < features.length; i += 1) {
      var p = features[i].properties;
      if (p.t < start || p.t > end) {
        continue;
      }
      if (!matchesType(p.k)) {
        continue;
      }
      n += 1;
    }
    return n;
  }

  function applyTime() {
    var start = windowStart();
    var recentStart = Math.max(start, currentT - RECENT_DAYS * DAY_MS);
    ["WF", "RX"].forEach(function (kind) {
      map.setFilter("heat-" + kind, timeFilter(kind, start, currentT));
      if (!embed) {
        map.setFilter("dots-" + kind, timeFilter(kind, start, currentT));
        map.setFilter("recent-" + kind, timeFilter(kind, recentStart, currentT));
      }
    });

    if (embed) {
      els.date.textContent = formatDate(currentT);
      return;
    }

    var n = countVisible(start, currentT);
    var windowText =
      windowDays <= 0 ? "cumulative" : windowDays + "-day window";
    els.date.innerHTML =
      formatDate(currentT) +
      "<small>" +
      n.toLocaleString("en-US") +
      " incidents · " +
      windowText +
      "</small>";
    els.slider.value = String(currentT);
    drawHistogram();
  }

  function setEra(next) {
    era = next;
    var times = features.map(function (f) {
      return f.properties.t;
    });
    minT = Math.min.apply(null, times);
    maxT = Math.max.apply(null, times);
    if (era === "recent") {
      rangeMinT = new Date(Date.UTC(COMPLETE_YEAR, 0, 1)).getTime();
      if (rangeMinT < minT) {
        rangeMinT = minT;
      }
    } else {
      rangeMinT = minT;
    }
    currentT = rangeMinT;
    els.slider.min = String(rangeMinT);
    els.slider.max = String(maxT);
    els.slider.step = String(DAY_MS);
    applyTime();
  }

  function monthKey(date) {
    return date.getUTCFullYear() + "-" + String(date.getUTCMonth() + 1).padStart(2, "0");
  }

  function histogramKeys(useYear) {
    var keys = [];
    var start = new Date(rangeMinT);
    var end = new Date(maxT);
    if (useYear) {
      for (var year = start.getUTCFullYear(); year <= end.getUTCFullYear(); year += 1) {
        keys.push(String(year));
      }
      return keys;
    }
    var year = start.getUTCFullYear();
    var month = start.getUTCMonth();
    var endYear = end.getUTCFullYear();
    var endMonth = end.getUTCMonth();
    while (year < endYear || (year === endYear && month <= endMonth)) {
      keys.push(year + "-" + String(month + 1).padStart(2, "0"));
      month += 1;
      if (month > 11) {
        month = 0;
        year += 1;
      }
    }
    return keys;
  }

  function drawHistogram() {
    var canvas = els.histogram;
    if (!canvas || embed) {
      return;
    }
    var width = canvas.clientWidth;
    var height = canvas.clientHeight;
    if (width < 8 || height < 8) {
      return;
    }
    var dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    var ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    var useYear = era === "all";
    var keys = histogramKeys(useYear);
    var bins = {};
    keys.forEach(function (key) {
      bins[key] = 0;
    });
    features.forEach(function (f) {
      var t = f.properties.t;
      if (t < rangeMinT || t > maxT || !matchesType(f.properties.k)) {
        return;
      }
      var d = new Date(t);
      var key = useYear ? String(d.getUTCFullYear()) : monthKey(d);
      if (bins[key] != null) {
        bins[key] += 1;
      }
    });
    var maxBin = 1;
    keys.forEach(function (key) {
      if (bins[key] > maxBin) {
        maxBin = bins[key];
      }
    });
    var gap = 1;
    var barW = keys.length ? (width - gap * (keys.length - 1)) / keys.length : width;
    keys.forEach(function (key, i) {
      var h = (bins[key] / maxBin) * (height - 2);
      var x = i * (barW + gap);
      ctx.fillStyle = i / keys.length <= (currentT - rangeMinT) / (maxT - rangeMinT) ? "#D99A5B" : "#3A3B2D";
      ctx.fillRect(x, height - h, Math.max(barW, 1), h);
    });
    var playX = ((currentT - rangeMinT) / Math.max(1, maxT - rangeMinT)) * width;
    ctx.fillStyle = "#F2EFE4";
    ctx.fillRect(playX, 0, 1.5, height);
  }

  function seekFromHistogram(event) {
    var rect = els.histogram.getBoundingClientRect();
    var x = (event.clientX - rect.left) / rect.width;
    currentT = rangeMinT + Math.min(1, Math.max(0, x)) * (maxT - rangeMinT);
    applyTime();
  }

  function tickInterval() {
    return embed ? EMBED_PLAY_MS : PLAY_MS;
  }

  function stepMs() {
    return STEP_DAYS * DAY_MS * speed * (tickInterval() / PLAY_MS);
  }

  function clearPlayTimer() {
    if (!rafId) {
      return;
    }
    if (embed) {
      window.clearTimeout(rafId);
    } else {
      window.cancelAnimationFrame(rafId);
    }
    rafId = 0;
  }

  function playLoop(now) {
    if (!playing) {
      return;
    }
    if (embed) {
      currentT += stepMs();
      if (currentT > maxT) {
        currentT = rangeMinT;
      }
      applyTime();
      rafId = window.setTimeout(function () {
        playLoop();
      }, EMBED_PLAY_MS);
      return;
    }
    if (now - lastTick >= PLAY_MS) {
      lastTick = now;
      currentT += stepMs();
      if (currentT > maxT) {
        currentT = rangeMinT;
      }
      applyTime();
    }
    rafId = window.requestAnimationFrame(playLoop);
  }

  function setPlaying(next) {
    clearPlayTimer();
    playing = next;
    if (els.play) {
      els.play.textContent = playing ? "Pause" : "Play";
      els.play.setAttribute("aria-pressed", playing ? "true" : "false");
    }
    if (playing) {
      lastTick = 0;
      if (embed) {
        rafId = window.setTimeout(function () {
          playLoop();
        }, EMBED_PLAY_MS);
      } else {
        rafId = window.requestAnimationFrame(playLoop);
      }
    }
  }

  function bindPopups() {
    if (embed) {
      return;
    }
    ["dots-WF", "dots-RX", "recent-WF", "recent-RX"].forEach(function (id) {
      map.on("click", id, function (event) {
        var f = event.features && event.features[0];
        if (!f) {
          return;
        }
        var p = f.properties;
        var acres = p.a ? Number(p.a).toLocaleString("en-US", { maximumFractionDigits: 1 }) : "—";
        new maplibregl.Popup({ closeButton: false, offset: 8 })
          .setLngLat(event.lngLat)
          .setHTML(
            "<strong>" +
              escapeHtml(p.n) +
              "</strong><br>" +
              typeLabel(p.k) +
              (p.c ? " · " + escapeHtml(p.c) + " County" : "") +
              "<br>" +
              formatDate(p.t) +
              "<br>" +
              acres +
              " acres"
          )
          .addTo(map);
      });
      map.on("mouseenter", id, function () {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", id, function () {
        map.getCanvas().style.cursor = "";
      });
    });
  }

  function initMap() {
    if (typeof maplibregl === "undefined") {
      throw new Error("MapLibre failed to load from the CDN.");
    }
    var mapOptions = {
      container: "map",
      style: styleSpec(),
      center: [-86.1, 35.85],
      zoom: embed ? 5.7 : 6.15,
      maxBounds: [
        [TN.west - 3.5, TN.south - 2],
        [TN.east + 3.5, TN.north + 2]
      ],
      attributionControl: !embed,
      interactive: !embed,
      fadeDuration: embed ? 0 : 300,
      scrollZoom: !embed
    };
    if (embed) {
      mapOptions.pixelRatio = 1;
    }
    map = new maplibregl.Map(mapOptions);
    if (!embed) {
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    }
    map.fitBounds(
      [
        [TN.west, TN.south],
        [TN.east, TN.north]
      ],
      { padding: embed ? 16 : 48, duration: 0 }
    );
    return new Promise(function (resolve) {
      map.on("load", function () {
        map.resize();
        resolve();
      });
    });
  }

  function bindUi() {
    window.addEventListener("message", function (event) {
      if (!event.data || event.data.type !== "cts-embed-visible") {
        return;
      }
      parentVisible = Boolean(event.data.visible);
      setPlaying(parentVisible && !document.hidden);
    });
    if (embed) {
      document.addEventListener("visibilitychange", function () {
        setPlaying(parentVisible && !document.hidden);
      });
      return;
    }
    els.play.addEventListener("click", function () {
      setPlaying(!playing);
    });
    els.slider.addEventListener("input", function () {
      setPlaying(false);
      currentT = Number(els.slider.value);
      applyTime();
    });
    els.window.addEventListener("change", function () {
      windowDays = Number(els.window.value);
      applyTime();
    });
    if (els.speed) {
      els.speed.addEventListener("change", function () {
        speed = Number(els.speed.value) || 1;
      });
    }
    if (els.type) {
      els.type.addEventListener("change", function () {
        typeFilter = els.type.value;
        applyTime();
      });
    }
    if (els.era) {
      els.era.addEventListener("change", function () {
        setPlaying(false);
        setEra(els.era.value);
      });
    }
    if (els.histogram) {
      els.histogram.addEventListener("click", function (event) {
        setPlaying(false);
        seekFromHistogram(event);
      });
    }
    window.addEventListener("keydown", function (event) {
      if (event.target && /^(INPUT|SELECT|TEXTAREA)$/.test(event.target.tagName)) {
        return;
      }
      if (event.code === "Space") {
        event.preventDefault();
        setPlaying(!playing);
      } else if (event.code === "ArrowRight") {
        currentT = Math.min(maxT, currentT + stepMs());
        applyTime();
      } else if (event.code === "ArrowLeft") {
        currentT = Math.max(rangeMinT, currentT - stepMs());
        applyTime();
      }
    });
    window.addEventListener("resize", function () {
      if (map) {
        map.resize();
      }
      drawHistogram();
    });
  }

  async function init() {
    if (embed) {
      document.body.classList.add("fires-embed");
    }
    els.date = $("fires-date");
    els.status = $("fires-status");
    els.play = $("fires-play");
    els.slider = $("fires-slider");
    els.window = $("fires-window");
    els.speed = $("fires-speed");
    els.type = $("fires-type");
    els.era = $("fires-era");
    els.histogram = $("fires-histogram");
    els.credit = $("fires-credit");

    try {
      await initMap();
      els.status.textContent = "Loading InFORM fire incidents for Tennessee…";
      features = await loadFires();
      if (!features.length) {
        throw new Error("No Tennessee incidents returned.");
      }
      addFireLayers();
      bindPopups();
      bindUi();
      setEra(era);
      els.status.hidden = true;
      if (els.credit) {
        els.credit.innerHTML =
          "NIFC InFORM fire occurrence, point of origin in Tennessee (POOState = US-TN). " +
          features.length.toLocaleString("en-US") +
          " wildfire and prescribed incidents, " +
          formatDate(minT) +
          " – " +
          formatDate(maxT) +
          ". Reporting is much more complete after 2020, so later years show more incidents. " +
          '<a href="https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/InFORM_FireOccurrence_Public/FeatureServer" target="_blank" rel="noopener noreferrer">Data service</a>.';
      }
      setPlaying(true);
    } catch (err) {
      els.status.hidden = false;
      els.status.textContent =
        "Could not load InFORM incidents. Check the ArcGIS Online connection" +
        " (Zscaler may need to trust this request) and refresh. " +
        (err && err.message ? err.message : "");
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
