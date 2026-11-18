// Day 18 — NULL. Static sheet of the 1994 Marathon des Sables.
// Three recorded fixes, WGS84. The track between them is not drawn.
// Equirectangular, scaled by cos(lat0) so longitude matches latitude at the sheet center.

(function () {
  var START = { name: "Start", place: "Foum Zguid", lat: 30.0931852, lon: -6.8760994, kind: "start" };
  var FINISH = { name: "Finish", place: "Zagora", lat: 30.3334719, lon: -5.8348245, kind: "finish" };
  var FOUND = { name: "Found", place: "Tindouf", lat: 27.6691707, lon: -8.1434270, kind: "found" };
  var FIXES = [START, FINISH, FOUND];

  // Straight-line separations, haversine, mean Earth radius 6371 km.
  // Start to Tindouf 296 km. Finish to Tindouf 372 km. Start to finish 104 km.
  var NULL_AT = { lon: -7.22, lat: 29.02 };

  var CORE = { west: -11.7, east: -4.4, south: 26.7, north: 32.15 };

  var INK = "#3F2A1A";
  var INK_SOFT = "rgba(63, 42, 26, 0.62)";
  var CLAY = "#9C3B22";
  var SAND = "#F4D9AA";
  var SEA = "#6E908B";
  var SEA_INK = "rgba(243, 230, 200, 0.88)";

  var canvas = document.getElementById("d18-canvas");
  var ctx = canvas.getContext("2d");

  function embed() {
    return document.body.classList.contains("d18-embed");
  }

  function project(view, lon, lat) {
    var x = view.cx + (lon - view.lon0) * view.k * view.scale;
    var y = view.cy - (lat - view.lat0) * view.scale;
    return [x, y];
  }

  function makeView(w, h) {
    var padTop = embed() ? 18 : Math.min(148, h * 0.18);
    var padBottom = embed() ? 22 : Math.min(132, h * 0.2);
    var padX = Math.max(18, Math.min(w, h) * 0.045);
    var availW = Math.max(40, w - padX * 2);
    var availH = Math.max(40, h - padTop - padBottom);
    var lon0 = (CORE.west + CORE.east) / 2;
    var lat0 = (CORE.south + CORE.north) / 2;
    var k = Math.cos(lat0 * Math.PI / 180);
    var gw = (CORE.east - CORE.west) * k;
    var gh = CORE.north - CORE.south;
    var aspect = availW / availH;
    if (aspect > gw / gh) gw = gh * aspect;
    else gh = gw / aspect;
    var scale = availW / gw;
    return {
      lon0: lon0,
      lat0: lat0,
      k: k,
      scale: scale,
      cx: padX + availW / 2,
      cy: padTop + availH / 2,
      west: lon0 - gw / (2 * k),
      east: lon0 + gw / (2 * k),
      south: lat0 - gh / 2,
      north: lat0 + gh / 2
    };
  }

  function ringPath(view, ring) {
    var p = project(view, ring[0][0], ring[0][1]);
    ctx.moveTo(p[0], p[1]);
    for (var i = 1; i < ring.length; i++) {
      p = project(view, ring[i][0], ring[i][1]);
      ctx.lineTo(p[0], p[1]);
    }
    ctx.closePath();
  }

  function linePath(view, line) {
    var p = project(view, line[0][0], line[0][1]);
    ctx.moveTo(p[0], p[1]);
    for (var i = 1; i < line.length; i++) {
      p = project(view, line[i][0], line[i][1]);
      ctx.lineTo(p[0], p[1]);
    }
  }

  function inLand(lon, lat) {
    var ring = LAND[0];
    var inside = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var xi = ring[i][0];
      var yi = ring[i][1];
      var xj = ring[j][0];
      var yj = ring[j][1];
      var cross = ((yi > lat) !== (yj > lat)) &&
        (lon < (xj - xi) * (lat - yi) / ((yj - yi) || 1e-12) + xi);
      if (cross) inside = !inside;
    }
    return inside;
  }

  function tracked(text, x, y, spacing, draw) {
    var widths = [];
    var total = 0;
    for (var i = 0; i < text.length; i++) {
      var w = ctx.measureText(text[i]).width;
      widths.push(w);
      total += w;
    }
    total += spacing * (text.length - 1);
    var cursor = x - total / 2;
    for (var n = 0; n < text.length; n++) {
      draw(text[n], cursor + widths[n] / 2, y);
      cursor += widths[n] + spacing;
    }
    return total;
  }

  function haloText(text, x, y, align) {
    ctx.textAlign = align || "center";
    ctx.lineJoin = "round";
    ctx.miterLimit = 2;
    ctx.strokeStyle = "rgba(244, 217, 170, 0.94)";
    ctx.lineWidth = 5;
    ctx.strokeText(text, x, y);
    ctx.fillStyle = INK;
    ctx.fillText(text, x, y);
  }

  function drawFix(x, y, kind, r) {
    ctx.save();
    ctx.translate(x, y);
    ctx.lineJoin = "round";
    if (kind === "finish") {
      ctx.beginPath();
      ctx.arc(0, 0, r, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(244, 217, 170, 0.95)";
      ctx.lineWidth = r * 0.95;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(0, 0, r * 0.72, 0, Math.PI * 2);
      ctx.strokeStyle = CLAY;
      ctx.lineWidth = Math.max(1.4, r * 0.28);
      ctx.stroke();
    } else if (kind === "found") {
      ctx.rotate(Math.PI / 4);
      ctx.fillStyle = CLAY;
      ctx.fillRect(-r * 0.78, -r * 0.78, r * 1.56, r * 1.56);
      ctx.strokeStyle = "rgba(244, 217, 170, 0.95)";
      ctx.lineWidth = Math.max(2, r * 0.38);
      ctx.strokeRect(-r * 0.78, -r * 0.78, r * 1.56, r * 1.56);
    } else {
      ctx.beginPath();
      ctx.arc(0, 0, r, 0, Math.PI * 2);
      ctx.fillStyle = CLAY;
      ctx.fill();
      ctx.strokeStyle = "rgba(244, 217, 170, 0.95)";
      ctx.lineWidth = Math.max(2, r * 0.42);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(0, 0, r * 0.28, 0, Math.PI * 2);
      ctx.fillStyle = SAND;
      ctx.fill();
    }
    ctx.restore();
  }

  function drawDunes(view, w, h, nullBox) {
    var rand = mulberry(18);
    ctx.save();
    ctx.beginPath();
    ringPath(view, LAND[0]);
    ctx.clip();
    ctx.strokeStyle = "rgba(138, 88, 40, 0.16)";
    ctx.lineWidth = 1;
    var hits = 0;
    var guard = 0;
    while (hits < 90 && guard < 700) {
      guard += 1;
      var lon = view.west + rand() * (view.east - view.west);
      var lat = view.south + rand() * (view.north - view.south);
      if (!inLand(lon, lat)) continue;
      var p = project(view, lon, lat);
      if (nearFix(p[0], p[1], 34)) continue;
      if (p[0] > nullBox.x && p[0] < nullBox.x + nullBox.w && p[1] > nullBox.y && p[1] < nullBox.y + nullBox.h) continue;
      var len = 18 + rand() * 28;
      ctx.beginPath();
      ctx.moveTo(p[0], p[1]);
      ctx.quadraticCurveTo(p[0] + len * 0.45, p[1] - 3.5, p[0] + len, p[1] + 0.6);
      ctx.stroke();
      hits += 1;
    }
    ctx.restore();
  }

  function nearFix(x, y, pad) {
    for (var i = 0; i < FIXES.length; i++) {
      var dx = x - FIXES[i].sx;
      var dy = y - FIXES[i].sy;
      if (dx * dx + dy * dy < pad * pad) return true;
    }
    return false;
  }

  function mulberry(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function drawGraticule(view, w, h, label) {
    ctx.save();
    ctx.beginPath();
    ringPath(view, LAND[0]);
    ctx.clip();
    ctx.strokeStyle = "rgba(63, 42, 26, 0.16)";
    ctx.lineWidth = 1;
    ctx.font = "500 11px Barlow Condensed, sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    var lon = Math.ceil(view.west);
    for (; lon < view.east; lon++) {
      ctx.beginPath();
      linePath(view, [[lon, view.south], [lon, view.north]]);
      ctx.stroke();
    }
    var lat = Math.ceil(view.south);
    for (; lat < view.north; lat++) {
      ctx.beginPath();
      linePath(view, [[view.west, lat], [view.east, lat]]);
      ctx.stroke();
    }
    ctx.restore();
    if (!label) return;

    ctx.fillStyle = INK_SOFT;
    ctx.font = "500 12px Barlow Condensed, sans-serif";
    ctx.textBaseline = "middle";
    lat = Math.ceil(view.south);
    for (; lat < view.north; lat++) {
      if (lat % 2) continue;
      var p = project(view, view.west, lat);
      var label = lat + "°N";
      if (nearFix(p[0] + 28, p[1], 36)) continue;
      ctx.textAlign = "left";
      ctx.fillText(label, Math.max(8, p[0] + 6), p[1]);
    }
    ctx.textBaseline = "alphabetic";
    lon = Math.ceil(view.west);
    for (; lon < view.east; lon++) {
      if (lon % 2) continue;
      p = project(view, lon, view.south);
      label = Math.abs(lon) + "°W";
      if (nearFix(p[0], p[1] - 16, 36)) continue;
      ctx.textAlign = "center";
      ctx.fillText(label, p[0], Math.min(h - 8, p[1] - 6));
    }
  }

  function chromeBottom(h) {
    if (embed()) return 22;
    if (window.innerWidth > 720) return 28;
    var dock = document.querySelector(".d18-dock");
    var block = dock ? dock.offsetHeight + 20 : Math.min(160, h * 0.24);
    return block;
  }

  function drawScale(view, w, h) {
    var km = 100;
    var px = (km / 110.574) * view.scale;
    var margin = chromeBottom(h);
    var x = w - 24 - px;
    var y = h - margin;
    ctx.strokeStyle = INK;
    ctx.fillStyle = INK;
    ctx.lineWidth = 1.25;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + px, y);
    ctx.moveTo(x, y - 4);
    ctx.lineTo(x, y + 4);
    ctx.moveTo(x + px, y - 4);
    ctx.lineTo(x + px, y + 4);
    ctx.stroke();
    ctx.font = "500 12px Barlow Condensed, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    ctx.fillText("100 km", x + px / 2, y - 6);
  }

  function draw(w, h) {
    var view = makeView(w, h);
    var shortSide = Math.min(w, h);
    var compact = shortSide < 560;
    var tiny = shortSide < 420;

    for (var i = 0; i < FIXES.length; i++) {
      var s = project(view, FIXES[i].lon, FIXES[i].lat);
      FIXES[i].sx = s[0];
      FIXES[i].sy = s[1];
    }

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = SEA;
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    ctx.beginPath();
    ringPath(view, LAND[0]);
    ctx.clip();
    var sand = ctx.createLinearGradient(0, 0, 0, h);
    sand.addColorStop(0, "#F7E6C4");
    sand.addColorStop(0.55, "#F0D2A0");
    sand.addColorStop(1, "#E0BC82");
    ctx.fillStyle = sand;
    ctx.fillRect(0, 0, w, h);
    ctx.restore();

    var nullSize = tiny
      ? Math.max(18, shortSide * 0.085)
      : Math.max(28, shortSide * (compact ? 0.09 : 0.078));
    ctx.font = "600 " + nullSize + "px Fraunces, Georgia, serif";
    var nullWidth = 0;
    var spacing = nullSize * 0.22;
    for (var c = 0; c < 4; c++) nullWidth += ctx.measureText("NULL"[c]).width;
    nullWidth += spacing * 3;
    var nullPt = project(view, NULL_AT.lon, NULL_AT.lat);
    var nullBox = {
      x: nullPt[0] - nullWidth / 2 - 12,
      y: nullPt[1] - nullSize * 0.8,
      w: nullWidth + 24,
      h: nullSize * 1.7
    };

    drawDunes(view, w, h, nullBox);
    drawGraticule(view, w, h, !tiny);

    ctx.save();
    ctx.beginPath();
    ringPath(view, LAND[0]);
    ctx.strokeStyle = INK;
    ctx.lineWidth = 1.35;
    ctx.stroke();
    ctx.restore();

    ctx.save();
    ctx.setLineDash([2.5, 3.5]);
    ctx.strokeStyle = "rgba(63, 42, 26, 0.55)";
    ctx.lineWidth = 1;
    for (i = 0; i < BORDERS.length; i++) {
      ctx.beginPath();
      linePath(view, BORDERS[i]);
      ctx.stroke();
    }
    ctx.restore();

    var placeSize = compact ? 13 : 15;
    ctx.textBaseline = "middle";
    if (!tiny) {
      ctx.font = "500 " + placeSize + "px Barlow Condensed, sans-serif";
      ctx.fillStyle = "rgba(63, 42, 26, 0.55)";
      ctx.textAlign = "center";
      var morocco = project(view, -9.15, 31.15);
      var algeria = project(view, -5.55, 28.15);
      ctx.fillText("MOROCCO", morocco[0], morocco[1]);
      ctx.fillText("ALGERIA", algeria[0], algeria[1]);
    }

    if (!tiny) {
      var ocean = project(view, -11.15, 30.55);
      ctx.font = "italic 500 " + (compact ? 13 : 16) + "px Fraunces, Georgia, serif";
      var oceanWord = "ATLANTIC";
      var oceanWidth = 0;
      for (var oi = 0; oi < oceanWord.length; oi++) oceanWidth += ctx.measureText(oceanWord[oi]).width;
      oceanWidth += 3.2 * (oceanWord.length - 1);
      if (!inLand(-11.15, 30.55) && ocean[0] - oceanWidth / 2 > 10 && ocean[0] + oceanWidth / 2 < w - 10) {
        ctx.fillStyle = SEA_INK;
        tracked(oceanWord, ocean[0], ocean[1], 3.2, function (ch, x, y) {
          ctx.textAlign = "center";
          ctx.fillText(ch, x, y);
        });
      }
    }

    ctx.font = "600 " + nullSize + "px Fraunces, Georgia, serif";
    ctx.textBaseline = "middle";
    ctx.lineJoin = "round";
    tracked("NULL", nullPt[0], nullPt[1], spacing, function (ch, x, y) {
      ctx.strokeStyle = "rgba(244, 217, 170, 0.55)";
      ctx.lineWidth = 6;
      ctx.strokeText(ch, x, y);
      ctx.fillStyle = "#6B4124";
      ctx.fillText(ch, x, y);
    });
    if (!tiny) {
      ctx.font = "500 " + (compact ? 11 : 13) + "px Barlow Condensed, sans-serif";
      ctx.fillStyle = INK_SOFT;
      ctx.textAlign = "center";
      ctx.fillText("THE TRACK", nullPt[0], nullPt[1] + nullSize * 0.62);
    }

    var r = tiny ? 3.5 : (compact ? 5 : 6.5);
    FIXES.forEach(function (fix) {
      drawFix(fix.sx, fix.sy, fix.kind, r);
    });

    ctx.textBaseline = "middle";
    labelFix(START, compact, tiny, -1);
    labelFix(FINISH, compact, tiny, 1);
    labelFix(FOUND, compact, tiny, 1);

    drawScale(view, w, h);
  }

  function labelFix(fix, compact, tiny, side) {
    var nameSize = tiny ? 11 : (compact ? 14 : 16);
    var subSize = compact ? 12 : 13;
    var gap = tiny ? 8 : (compact ? 12 : 16);
    var x = fix.sx + side * (gap + 2);
    var align = side < 0 ? "right" : "left";
    var title = tiny ? (fix.kind === "found" ? "Tindouf" : fix.name) : fix.name.toUpperCase();
    ctx.textAlign = align;
    ctx.font = "600 " + nameSize + "px Barlow Condensed, sans-serif";
    haloText(title, x, fix.sy + (tiny ? 0 : -(compact ? 8 : 12)), align);
    if (tiny) return;
    ctx.font = "500 " + subSize + "px Barlow Condensed, sans-serif";
    haloText(fix.place, x, fix.sy + (compact ? 6 : 4), align);
    if (!compact) {
      ctx.font = "400 12px Barlow Condensed, sans-serif";
      ctx.fillStyle = INK_SOFT;
      var coord = Math.abs(fix.lat).toFixed(3) + "° N   " + Math.abs(fix.lon).toFixed(3) + "° W";
      ctx.fillText(coord, x, fix.sy + 20);
    }
  }

  function resize() {
    var w = canvas.clientWidth;
    var h = canvas.clientHeight;
    if (!w || !h) return;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw(w, h);
  }

  window.addEventListener("resize", resize);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(resize);
  resize();
})();
