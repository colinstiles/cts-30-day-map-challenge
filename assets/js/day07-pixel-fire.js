/* Day 7 — 10-minute map: pixel Chimney Tops 2 progression (Sevier County, TN).
   Coarse canvas grid only — no MapLibre — so it paints fast inside the timebox. */
(function () {
  "use strict";

  // Sevier County / east GSMNP window (WGS84)
  var BBOX = { west: -83.72, south: 35.60, east: -83.30, north: 35.90 };
  var COLS = 64;
  var ROWS = 40;
  var PIXEL = 10;

  // Cell footprint ≈ acres (bbox area / grid). Used for live burn callout.
  var ACRES_PER_CELL =
    ((BBOX.east - BBOX.west) * 90.5 * 1000) *
    ((BBOX.north - BBOX.south) * 111.0 * 1000) /
    4046.8564224 /
    (COLS * ROWS);

  // InFORM ignition seeds (Nov 2016 Sevier County query)
  var SEEDS = [
    { name: "Chimney Tops", t: Date.UTC(2016, 10, 13), lon: -83.4781, lat: 35.6286, acres: 0.3 },
    { name: "Chimney Tops 2", t: Date.UTC(2016, 10, 23), lon: -83.4778, lat: 35.6308, acres: 17140 },
    { name: "Cobbly Nob", t: Date.UTC(2016, 10, 28), lon: -83.3431, lat: 35.7700, acres: 767 }
  ];

  // Animation calendar (UTC noon stamps for stable labels)
  var FRAMES = [
    Date.UTC(2016, 10, 23),
    Date.UTC(2016, 10, 24),
    Date.UTC(2016, 10, 25),
    Date.UTC(2016, 10, 26),
    Date.UTC(2016, 10, 27),
    Date.UTC(2016, 10, 28), // blow-up into Gatlinburg
    Date.UTC(2016, 10, 29),
    Date.UTC(2016, 10, 30),
    Date.UTC(2016, 11, 1),
    Date.UTC(2016, 11, 3),
    Date.UTC(2016, 11, 5),
    Date.UTC(2016, 11, 9)
  ];

  // Rough city polygons (lon, lat rings) — schematic, not cadastral
  var CITIES = [
    {
      name: "Gatlinburg",
      ring: [
        [-83.528, 35.698],
        [-83.502, 35.696],
        [-83.488, 35.708],
        [-83.492, 35.724],
        [-83.505, 35.736],
        [-83.522, 35.732],
        [-83.536, 35.718],
        [-83.528, 35.698]
      ]
    },
    {
      name: "Pigeon Forge",
      ring: [
        [-83.578, 35.762],
        [-83.542, 35.760],
        [-83.532, 35.778],
        [-83.538, 35.808],
        [-83.562, 35.814],
        [-83.582, 35.792],
        [-83.578, 35.762]
      ]
    },
    {
      name: "Sevierville",
      ring: [
        [-83.590, 35.848],
        [-83.538, 35.846],
        [-83.528, 35.868],
        [-83.542, 35.892],
        [-83.578, 35.894],
        [-83.598, 35.872],
        [-83.590, 35.848]
      ]
    }
  ];

  var embed = new URLSearchParams(window.location.search).get("embed") === "1";
  if (embed) {
    document.body.classList.add("day07-embed");
  }

  var canvas;
  var ctx;
  var burned; // Float32Array: 0 empty, >0 intensity / age
  var elev; // Float32Array 0–1
  var urban; // Uint8Array 1 = inside city poly
  var cityEdge; // Uint8Array 1 = outline pixel
  var frame = 0;
  var playing = true;
  var lastTick = 0;
  var speed = embed ? 0.7 : 1;
  var parentVisible = true;
  var burnedAcres = 0;

  var els = {};

  function $(id) {
    return document.getElementById(id);
  }

  function lonLatToCell(lon, lat) {
    var c = Math.floor(((lon - BBOX.west) / (BBOX.east - BBOX.west)) * COLS);
    var r = Math.floor(((BBOX.north - lat) / (BBOX.north - BBOX.south)) * ROWS);
    return {
      c: Math.max(0, Math.min(COLS - 1, c)),
      r: Math.max(0, Math.min(ROWS - 1, r))
    };
  }

  function cellToLonLat(c, r) {
    return {
      lon: BBOX.west + ((c + 0.5) / COLS) * (BBOX.east - BBOX.west),
      lat: BBOX.north - ((r + 0.5) / ROWS) * (BBOX.north - BBOX.south)
    };
  }

  function idx(c, r) {
    return r * COLS + c;
  }

  function formatFireDate(ms) {
    return new Date(ms).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      timeZone: "UTC"
    });
  }

  function formatAcres(n) {
    if (n < 10) return n.toFixed(1);
    if (n < 100) return String(Math.round(n));
    return Math.round(n).toLocaleString("en-US");
  }

  function pointInRing(lon, lat, ring) {
    var inside = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var xi = ring[i][0];
      var yi = ring[i][1];
      var xj = ring[j][0];
      var yj = ring[j][1];
      var intersect =
        yi > lat !== yj > lat &&
        lon < ((xj - xi) * (lat - yi)) / (yj - yi + 0.0) + xi;
      if (intersect) inside = !inside;
    }
    return inside;
  }

  function plotLine(c0, r0, c1, r1, out) {
    var dc = Math.abs(c1 - c0);
    var dr = Math.abs(r1 - r0);
    var sc = c0 < c1 ? 1 : -1;
    var sr = r0 < r1 ? 1 : -1;
    var err = dc - dr;
    var c = c0;
    var r = r0;
    while (true) {
      if (c >= 0 && r >= 0 && c < COLS && r < ROWS) out[idx(c, r)] = 1;
      if (c === c1 && r === r1) break;
      var e2 = 2 * err;
      if (e2 > -dr) {
        err -= dr;
        c += sc;
      }
      if (e2 < dc) {
        err += dc;
        r += sr;
      }
    }
  }

  function buildTerrainAndCities() {
    elev = new Float32Array(COLS * ROWS);
    urban = new Uint8Array(COLS * ROWS);
    cityEdge = new Uint8Array(COLS * ROWS);

    for (var r = 0; r < ROWS; r++) {
      for (var c = 0; c < COLS; c++) {
        var x = c / COLS;
        var y = r / ROWS; // 0 = north, 1 = south (park)
        // Smokies massif rises south; ridge corrugation stays chunky at this resolution
        var ridges =
          Math.sin(x * 16 + y * 7) * 0.22 +
          Math.sin(x * 9 - y * 11) * 0.14 +
          Math.sin((x + y) * 21) * 0.06;
        var foothills = Math.sin(x * 5 + 1.2) * 0.08 * (1 - y);
        var massif = Math.pow(y, 1.15) * 0.78;
        var valley = (1 - y) * 0.22;
        // Soft west–east valley trench (Pigeon / West Prong corridor)
        var corridor = Math.exp(-Math.pow((x - 0.48) / 0.12, 2)) * (1 - y) * 0.12;
        var e = massif + ridges * (0.35 + massif) + foothills + valley - corridor;
        elev[idx(c, r)] = Math.max(0, Math.min(1, e));

        var ll = cellToLonLat(c, r);
        for (var ci = 0; ci < CITIES.length; ci++) {
          if (pointInRing(ll.lon, ll.lat, CITIES[ci].ring)) {
            urban[idx(c, r)] = 1;
            break;
          }
        }
      }
    }

    for (var city = 0; city < CITIES.length; city++) {
      var ring = CITIES[city].ring;
      for (var i = 0; i < ring.length - 1; i++) {
        var a = lonLatToCell(ring[i][0], ring[i][1]);
        var b = lonLatToCell(ring[i + 1][0], ring[i + 1][1]);
        plotLine(a.c, a.r, b.c, b.r, cityEdge);
      }
    }
  }

  function terrainColor(c, r) {
    var e = elev[idx(c, r)];
    var dither = ((c * 17 + r * 31) & 3) * 3;
    // Low: valley olive; mid: forest; high: cool ridge
    var rCh;
    var gCh;
    var bCh;
    if (e < 0.35) {
      var t = e / 0.35;
      rCh = 42 + t * 18 + dither;
      gCh = 48 + t * 28 + dither;
      bCh = 32 + t * 10;
    } else if (e < 0.7) {
      var t2 = (e - 0.35) / 0.35;
      rCh = 28 + t2 * 10 + dither * 0.5;
      gCh = 58 + t2 * 22 + dither;
      bCh = 36 + t2 * 8;
    } else {
      var t3 = (e - 0.7) / 0.3;
      rCh = 48 + t3 * 40 + dither;
      gCh = 70 + t3 * 25 + dither;
      bCh = 52 + t3 * 30;
    }
    if (urban[idx(c, r)]) {
      // Subtle built-up lift — keeps cities readable under fire
      rCh = Math.min(255, rCh + 28);
      gCh = Math.min(255, gCh + 22);
      bCh = Math.min(255, bCh + 18);
    }
    return (
      "rgb(" +
      Math.floor(Math.max(0, Math.min(255, rCh))) +
      "," +
      Math.floor(Math.max(0, Math.min(255, gCh))) +
      "," +
      Math.floor(Math.max(0, Math.min(255, bCh))) +
      ")"
    );
  }

  function fireColor(age, intensity) {
    var t = Math.min(1, age / 8);
    var i = Math.min(1, intensity);
    var r = Math.floor(255 - t * 120);
    var g = Math.floor(220 * (1 - t) * i + 30 * (1 - t));
    var b = Math.floor(40 * (1 - t));
    return "rgb(" + r + "," + g + "," + b + ")";
  }

  function resetBurn() {
    burned = new Float32Array(COLS * ROWS);
  }

  function ignite(lon, lat, strength) {
    var cell = lonLatToCell(lon, lat);
    var rad = strength > 1000 ? 2 : 1;
    for (var dr = -rad; dr <= rad; dr++) {
      for (var dc = -rad; dc <= rad; dc++) {
        var c = cell.c + dc;
        var r = cell.r + dr;
        if (c < 0 || r < 0 || c >= COLS || r >= ROWS) continue;
        burned[idx(c, r)] = Math.max(burned[idx(c, r)], 1 + strength / 20000);
      }
    }
  }

  var rngState = 1;

  function rng() {
    rngState ^= rngState << 13;
    rngState ^= rngState >>> 17;
    rngState ^= rngState << 5;
    return (rngState >>> 0) / 4294967296;
  }

  function spreadStep(windN, windE, vigor) {
    var next = burned.slice();
    for (var r = 0; r < ROWS; r++) {
      for (var c = 0; c < COLS; c++) {
        var v = burned[idx(c, r)];
        if (v <= 0) continue;
        next[idx(c, r)] = v + 0.15;
        // Prefer N / NE on blow-up; climb ridges a bit slower
        var slope = elev[idx(c, r)];
        var climbPenalty = slope > 0.65 ? 0.85 : 1;
        var dirs = [
          [0, -1, 0.55 + windN],
          [1, -1, 0.4 + windN * 0.5 + windE],
          [-1, -1, 0.35 + windN * 0.4],
          [1, 0, 0.25 + windE],
          [-1, 0, 0.2],
          [0, 1, 0.12],
          [1, 1, 0.1],
          [-1, 1, 0.08]
        ];
        for (var d = 0; d < dirs.length; d++) {
          var nc = c + dirs[d][0];
          var nr = r + dirs[d][1];
          if (nc < 0 || nr < 0 || nc >= COLS || nr >= ROWS) continue;
          if (rng() < dirs[d][2] * vigor * climbPenalty) {
            var ni = idx(nc, nr);
            if (next[ni] <= 0) next[ni] = 0.8;
            else next[ni] = Math.min(12, next[ni] + 0.2);
          }
        }
      }
    }
    burned = next;
  }

  function countBurnedAcres() {
    var n = 0;
    for (var i = 0; i < burned.length; i++) {
      if (burned[i] > 0) n++;
    }
    return n * ACRES_PER_CELL;
  }

  function simulateToFrame(fi) {
    resetBurn();
    rngState = 20161123 + fi * 997;
    var target = FRAMES[fi];
    for (var s = 0; s < SEEDS.length; s++) {
      if (SEEDS[s].t <= target) {
        ignite(SEEDS[s].lon, SEEDS[s].lat, SEEDS[s].acres || 1);
      }
    }
    for (var f = 0; f <= fi; f++) {
      var day = FRAMES[f];
      var blowup = day === Date.UTC(2016, 10, 28);
      var steps = blowup ? 14 : f === 0 ? 2 : 4;
      var windN = blowup ? 0.45 : 0.12;
      var windE = blowup ? 0.15 : 0.05;
      var vigor = blowup ? 1.35 : 0.55 + f * 0.04;
      for (var k = 0; k < steps; k++) {
        spreadStep(windN, windE, vigor);
      }
    }
    burnedAcres = countBurnedAcres();
  }

  function drawCityOverlays() {
    // Outline pixels on top so rings stay visible over burn
    for (var r = 0; r < ROWS; r++) {
      for (var c = 0; c < COLS; c++) {
        if (!cityEdge[idx(c, r)]) continue;
        ctx.fillStyle = burned[idx(c, r)] > 0 ? "#FFE8A3" : "#D8D2C0";
        ctx.fillRect(c * PIXEL, r * PIXEL, PIXEL, PIXEL);
      }
    }
    ctx.imageSmoothingEnabled = false;
    ctx.font = "bold 10px monospace";
    for (var p = 0; p < CITIES.length; p++) {
      var ring = CITIES[p].ring;
      var cx = 0;
      var cy = 0;
      for (var i = 0; i < ring.length - 1; i++) {
        cx += ring[i][0];
        cy += ring[i][1];
      }
      var n = ring.length - 1;
      var cell = lonLatToCell(cx / n, cy / n);
      ctx.fillStyle = "#F2EFE4";
      ctx.fillText(CITIES[p].name, cell.c * PIXEL - 10, cell.r * PIXEL + 4);
    }
  }

  function draw() {
    var w = COLS * PIXEL;
    var h = ROWS * PIXEL;
    if (canvas.width !== w) {
      canvas.width = w;
      canvas.height = h;
    }
    for (var r = 0; r < ROWS; r++) {
      for (var c = 0; c < COLS; c++) {
        var v = burned[idx(c, r)];
        if (v > 0) {
          ctx.fillStyle = fireColor(v, Math.min(1, v));
        } else {
          ctx.fillStyle = terrainColor(c, r);
        }
        ctx.fillRect(c * PIXEL, r * PIXEL, PIXEL, PIXEL);
      }
    }
    drawCityOverlays();
    // Ignition cross for Chimney Tops 2
    var ct = lonLatToCell(SEEDS[1].lon, SEEDS[1].lat);
    ctx.fillStyle = "#FFE66D";
    ctx.fillRect(ct.c * PIXEL + 3, ct.r * PIXEL, 4, PIXEL);
    ctx.fillRect(ct.c * PIXEL, ct.r * PIXEL + 3, PIXEL, 4);
  }

  function updateChrome() {
    if (els.date) els.date.textContent = formatFireDate(FRAMES[frame]);
    if (els.frame) els.frame.textContent = frame + 1 + " / " + FRAMES.length;
    if (els.slider) els.slider.value = String(frame);
    if (els.acres) {
      els.acres.textContent = "≈ " + formatAcres(burnedAcres) + " ac";
    }
    if (els.acresNote) {
      els.acresNote.textContent =
        "pixel footprint · cell ≈ " + formatAcres(ACRES_PER_CELL) + " ac";
    }
  }

  function setFrame(fi) {
    frame = Math.max(0, Math.min(FRAMES.length - 1, fi));
    simulateToFrame(frame);
    draw();
    updateChrome();
  }

  function tick(now) {
    if (!playing || (embed && !parentVisible)) {
      lastTick = now;
      requestAnimationFrame(tick);
      return;
    }
    if (!lastTick) lastTick = now;
    var msPerFrame = 700 / speed;
    if (now - lastTick >= msPerFrame) {
      lastTick = now;
      setFrame(frame + 1 >= FRAMES.length ? 0 : frame + 1);
    }
    requestAnimationFrame(tick);
  }

  function bind() {
    canvas = $("day07-canvas");
    ctx = canvas.getContext("2d");
    els.date = $("day07-date");
    els.frame = $("day07-frame");
    els.slider = $("day07-slider");
    els.acres = $("day07-acres");
    els.acresNote = $("day07-acres-note");
    els.play = $("day07-play");

    buildTerrainAndCities();

    if (els.slider) {
      els.slider.max = String(FRAMES.length - 1);
      els.slider.addEventListener("input", function () {
        playing = false;
        if (els.play) {
          els.play.setAttribute("aria-pressed", "false");
          els.play.textContent = "Play";
        }
        setFrame(Number(els.slider.value));
      });
    }
    if (els.play) {
      els.play.addEventListener("click", function () {
        playing = !playing;
        els.play.setAttribute("aria-pressed", playing ? "true" : "false");
        els.play.textContent = playing ? "Pause" : "Play";
        lastTick = 0;
      });
    }

    window.addEventListener("message", function (ev) {
      if (ev.data && ev.data.type === "cts-embed-visible") {
        parentVisible = Boolean(ev.data.visible);
      }
    });

    if (embed) {
      document.body.classList.add("day07-embed");
    }

    setFrame(0);
    requestAnimationFrame(tick);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
