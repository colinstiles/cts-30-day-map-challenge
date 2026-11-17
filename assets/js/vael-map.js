// Plate carrée chart of Vael. Relief and vectors come from VaelWorld (VAEL:2026).
(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);
  var still = params.get("still") === "1";
  var embed = still || params.get("embed") === "1";

  var canvas = document.getElementById("vael-canvas");
  var ctx = canvas.getContext("2d", { alpha: false });
  var readout = document.getElementById("vael-readout");
  var panel = document.getElementById("vael-panel");
  var notesBtn = document.getElementById("vael-notes");

  var layers = { realms: true, rivers: true, labels: true, grid: true };
  var view = null;
  var fitWidth = 100;
  var hover = null;
  var selected = null;
  var cache = document.createElement("canvas");
  var cacheCtx = cache.getContext("2d", { alpha: false });
  var dragging = false;
  var dragMoved = false;
  var lastPt = null;
  var dragView = null;
  var geo = null;
  var surface = null;

  var BATH = [
    [-4600, [10, 16, 18]],
    [-2000, [16, 40, 42]],
    [-700, [28, 72, 66]],
    [-160, [48, 104, 88]],
    [0, [118, 168, 140]]
  ];
  var LAND = [
    [0, [214, 196, 154]],
    [140, [184, 166, 114]],
    [420, [126, 138, 84]],
    [900, [86, 98, 66]],
    [1500, [102, 84, 68]],
    [2300, [168, 152, 128]],
    [3400, [240, 232, 216]]
  ];
  var TINT = {
    1: [0.94, 1.05, 0.9],
    2: [1.07, 0.98, 0.86],
    3: [1.1, 0.9, 0.8]
  };

  function mix(a, b, t) {
    return [
      a[0] + (b[0] - a[0]) * t,
      a[1] + (b[1] - a[1]) * t,
      a[2] + (b[2] - a[2]) * t
    ];
  }

  function ramp(stops, value) {
    if (value <= stops[0][0]) return stops[0][1];
    var i;
    for (i = 1; i < stops.length; i += 1) {
      if (value <= stops[i][0]) {
        var t = (value - stops[i - 1][0]) / (stops[i][0] - stops[i - 1][0]);
        return mix(stops[i - 1][1], stops[i][1], t);
      }
    }
    return stops[stops.length - 1][1];
  }

  function clamp255(v) {
    return v < 0 ? 0 : v > 255 ? 255 : v;
  }

  function unit() {
    if (still) return 1.15;
    var rect = canvas.getBoundingClientRect();
    var dpr = rect.width ? canvas.width / rect.width : 1;
    var css = Math.min(1.2, Math.max(0.82, rect.width / 1000));
    return css * dpr;
  }

  function resize() {
    if (still) {
      canvas.width = 1800;
      canvas.height = 1350;
      return;
    }
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(2, Math.round(rect.width * dpr));
    canvas.height = Math.max(2, Math.round(rect.height * dpr));
  }

  function fitView() {
    var ext = VaelWorld.worldExtent();
    var ew = ext.east - ext.west;
    var eh = ext.north - ext.south;
    var scale = Math.min(canvas.width / ew, canvas.height / eh) * 0.94;
    var vw = canvas.width / scale;
    var vh = canvas.height / scale;
    var cx = (ext.west + ext.east) / 2;
    var cy = (ext.south + ext.north) / 2;
    view = {
      west: cx - vw / 2,
      east: cx + vw / 2,
      south: cy - vh / 2,
      north: cy + vh / 2
    };
    fitWidth = vw;
  }

  function project(lon, lat) {
    return [
      ((lon - view.west) / (view.east - view.west)) * canvas.width,
      ((view.north - lat) / (view.north - view.south)) * canvas.height
    ];
  }

  function unproject(clientX, clientY) {
    var rect = canvas.getBoundingClientRect();
    var px = ((clientX - rect.left) / rect.width) * canvas.width;
    var py = ((clientY - rect.top) / rect.height) * canvas.height;
    return [
      view.west + (px / canvas.width) * (view.east - view.west),
      view.north - (py / canvas.height) * (view.north - view.south)
    ];
  }

  function bilinear(arr, stride, x, y, cols, rows) {
    if (x < 0 || y < 0 || x >= cols || y >= rows) return null;
    var x0 = Math.floor(x);
    var y0 = Math.floor(y);
    var tx = x - x0;
    var ty = y - y0;
    var i = y0 * stride + x0;
    var v00 = arr[i];
    var v10 = arr[i + 1];
    var v01 = arr[i + stride];
    var v11 = arr[i + stride + 1];
    return v00 * (1 - tx) * (1 - ty) + v10 * tx * (1 - ty) + v01 * (1 - tx) * ty + v11 * tx * ty;
  }

  function cellCode(x, y) {
    if (x < 0 || y < 0 || x >= surface.cols || y >= surface.rows) return 0;
    var stride = surface.cols + 1;
    return surface.realm[Math.round(y) * stride + Math.round(x)];
  }

  function paintRelief(g) {
    var w = canvas.width;
    var h = canvas.height;
    var img = g.createImageData(w, h);
    var data = img.data;
    var elevs = new Float32Array(w * h);
    var shift = VaelWorld.shift();
    var waters = VaelWorld.waters();
    var spanLon = view.east - view.west;
    var spanLat = view.north - view.south;
    var stride = surface.cols + 1;
    var y;
    var x;
    var i;
    for (y = 0; y < h; y += 1) {
      var lat = view.north - ((y + 0.5) / h) * spanLat;
      var gy = (lat + shift.lat - surface.south) / surface.step;
      for (x = 0; x < w; x += 1) {
        var lon = view.west + ((x + 0.5) / w) * spanLon;
        var gx = (lon + shift.lon - surface.west) / surface.step;
        var e = bilinear(surface.elev, stride, gx, gy, surface.cols, surface.rows);
        elevs[y * w + x] = e === null ? -4200 : e;
      }
    }

    var midLat = (view.north + view.south) / 2;
    var km = VaelWorld.kmPerDegree(midLat);
    var mPerPxX = (spanLon / w) * km.lon * 1000;
    var mPerPxY = (spanLat / h) * km.lat * 1000;
    var lx = -0.48;
    var ly = 0.52;
    var lz = 0.7;
    var llen = Math.hypot(lx, ly, lz);
    lx /= llen;
    ly /= llen;
    lz /= llen;

    for (y = 0; y < h; y += 1) {
      var latPx = view.north - ((y + 0.5) / h) * spanLat;
      for (x = 0; x < w; x += 1) {
        i = y * w + x;
        var e = elevs[i];
        var xm = x > 0 ? x - 1 : x;
        var xp = x + 1 < w ? x + 1 : x;
        var ym = y > 0 ? y - 1 : y;
        var yp = y + 1 < h ? y + 1 : y;
        var dzdx = (elevs[y * w + xp] - elevs[y * w + xm]) / ((xp - xm || 1) * mPerPxX);
        var dzdy = (elevs[ym * w + x] - elevs[yp * w + x]) / ((yp - ym || 1) * mPerPxY);
        var nx = -dzdx;
        var ny = -dzdy;
        var nz = 1;
        var nlen = Math.hypot(nx, ny, nz);
        var shade = (nx / nlen) * lx + (ny / nlen) * ly + (nz / nlen) * lz;
        if (shade < 0) shade = 0;
        var light = e > 0 ? 0.48 + shade * 0.78 : 0.55 + shade * 0.5;
        var lonPx = view.west + ((x + 0.5) / w) * spanLon;
        var rgb;
        if (e > 0) {
          rgb = ramp(LAND, e).slice();
          var code = cellCode(
            (lonPx + shift.lon - surface.west) / surface.step,
            (latPx + shift.lat - surface.south) / surface.step
          );
          var tint = TINT[code];
          if (tint) {
            rgb[0] *= tint[0];
            rgb[1] *= tint[1];
            rgb[2] *= tint[2];
          }
        } else {
          rgb = ramp(BATH, e).slice();
          var dMere = Math.hypot(lonPx - waters.mere.lon, latPx - waters.mere.lat);
          if (dMere < 11) rgb = mix(rgb, [186, 214, 196], 0.22 * (1 - dMere / 11));
          var dLake = Math.hypot(lonPx - waters.lake.lon, latPx - waters.lake.lat);
          if (dLake < 2.2) rgb = mix(rgb, [150, 196, 188], 0.35);
        }
        var o = i * 4;
        data[o] = clamp255(rgb[0] * light);
        data[o + 1] = clamp255(rgb[1] * light);
        data[o + 2] = clamp255(rgb[2] * light);
        data[o + 3] = 255;
      }
    }
    g.putImageData(img, 0, 0);
  }

  function strokeRings(g, rings, style) {
    g.beginPath();
    rings.forEach(function (ring) {
      if (!ring || ring.length < 2) return;
      var p = project(ring[0][0], ring[0][1]);
      g.moveTo(p[0], p[1]);
      var i;
      for (i = 1; i < ring.length; i += 1) {
        p = project(ring[i][0], ring[i][1]);
        g.lineTo(p[0], p[1]);
      }
    });
    g.strokeStyle = style.color;
    g.lineWidth = style.width;
    g.setLineDash(style.dash || []);
    g.lineJoin = "round";
    g.lineCap = "round";
    g.stroke();
    g.setLineDash([]);
  }

  function paintVectors(g) {
    var u = unit();
    if (layers.grid) {
      var lon0 = Math.ceil(view.west / 10) * 10;
      var lat0 = Math.ceil(view.south / 10) * 10;
      g.beginPath();
      var lon;
      var lat;
      for (lon = lon0; lon < view.east; lon += 10) {
        var a = project(lon, view.south);
        var b = project(lon, view.north);
        g.moveTo(a[0], a[1]);
        g.lineTo(b[0], b[1]);
      }
      for (lat = lat0; lat < view.north; lat += 10) {
        var c = project(view.west, lat);
        var d = project(view.east, lat);
        g.moveTo(c[0], c[1]);
        g.lineTo(d[0], d[1]);
      }
      g.strokeStyle = "rgba(156, 187, 116, 0.28)";
      g.lineWidth = Math.max(1, u);
      g.stroke();
      g.font = Math.round(11 * u) + "px Lato, Segoe UI, sans-serif";
      g.fillStyle = "rgba(156, 187, 116, 0.8)";
      g.textAlign = "left";
      g.textBaseline = "top";
      for (lon = lon0; lon < view.east; lon += 10) {
        var gp = project(lon, view.south);
        var label = lon === 0 ? "0°" : Math.abs(lon) + "°" + (lon > 0 ? "E" : "W");
        g.fillText(label, gp[0] + 4, canvas.height - 18 * u);
      }
    }

    if (layers.realms) paintBorders(g, u);
    if (layers.rivers) paintRivers(g, u);

    if (selected) paintPin(g, selected);
    if (layers.labels) paintLabels(g, u);
    if (!embed) paintFurniture(g, u);
  }

  function paintBorders(g, u) {
    (geo.realms || []).forEach(function (feature) {
      var realm = VaelWorld.REALMS[feature.realm];
      if (!realm) return;
      strokeRings(g, [feature.ring], {
        color: realm.color,
        width: Math.max(1.35, 1.8 * u)
      });
    });
  }

  function paintRivers(g, u) {
    geo.rivers.forEach(function (river) {
      var coords = river.coordinates;
      if (!coords || coords.length < 2) return;
      var i;
      g.lineCap = "round";
      g.lineJoin = "round";
      for (i = 1; i < coords.length; i += 1) {
        var t = i / (coords.length - 1);
        var a = project(coords[i - 1][0], coords[i - 1][1]);
        var b = project(coords[i][0], coords[i][1]);
        g.beginPath();
        g.moveTo(a[0], a[1]);
        g.lineTo(b[0], b[1]);
        g.strokeStyle = t > 0.8 ? "#e7fff6" : "#3ec4b4";
        g.lineWidth = (1.15 + t * 1.7) * u;
        g.stroke();
      }
    });
  }

  function labelPlaces() {
    var places = VaelWorld.places().slice();
    (geo.rivers || []).forEach(function (river) {
      if (!river.coordinates || river.coordinates.length < 3) return;
      var mid = river.coordinates[Math.floor(river.coordinates.length * 0.62)];
      places.push({
        name: river.name,
        kind: "river",
        lon: mid[0],
        lat: mid[1],
        labelBias: "north"
      });
    });
    return places;
  }

  function paintLabels(g, u) {
    var boxes = furnitureBoxes(u);
    var places = labelPlaces().sort(function (a, b) {
      return rank(a) - rank(b);
    });
    places.forEach(function (place) {
      var style = labelStyle(place, u);
      if (!style) return;
      g.font = style.font;
      var width = g.measureText(style.text).width;
      var height = style.size;
      var anchor = project(place.lon, place.lat);
      var placed = placeLabel(place, anchor, width, height, boxes);
      if (!placed) return;
      boxes.push(placed.box);
      if (style.kind === "capital" || style.kind === "town") {
        drawLeader(g, anchor, placed.box, style.color, u);
        drawAnchor(g, anchor, u);
      }
      g.font = style.font;
      g.textAlign = "left";
      g.textBaseline = "top";
      g.fillStyle = "rgba(16, 18, 14, 0.8)";
      g.fillText(style.text, placed.x + 1, placed.y + 1);
      g.fillStyle = style.color;
      g.fillText(style.text, placed.x, placed.y);
    });
  }

  function rank(place) {
    if (place.kind === "cape" || place.kind === "capital") return 0;
    if (place.kind === "water") return 1;
    if (place.kind === "region" || place.kind === "range") return 2;
    if (place.kind === "lake" || place.kind === "river") return 3;
    return 4;
  }

  function drawAnchor(g, anchor, u) {
    var r = 2.6 * u;
    g.beginPath();
    g.arc(anchor[0], anchor[1], r + 1.1 * u, 0, Math.PI * 2);
    g.fillStyle = "rgba(16, 14, 12, 0.9)";
    g.fill();
    g.beginPath();
    g.arc(anchor[0], anchor[1], r, 0, Math.PI * 2);
    g.fillStyle = "#f2efe4";
    g.fill();
  }

  function drawLeader(g, anchor, box, color, u) {
    var x = Math.min(Math.max(anchor[0], box.x), box.x + box.w);
    var y = Math.min(Math.max(anchor[1], box.y), box.y + box.h);
    if (Math.hypot(x - anchor[0], y - anchor[1]) < 8 * u) return;
    g.beginPath();
    g.moveTo(anchor[0], anchor[1]);
    g.lineTo(x, y);
    g.strokeStyle = color;
    g.globalAlpha = 0.75;
    g.lineWidth = Math.max(1, 0.9 * u);
    g.setLineDash([]);
    g.stroke();
    g.globalAlpha = 1;
  }

  function labelStyle(place, u) {
    var size = 12.5 * u;
    var color = "#f7f1e4";
    var text = place.name;
    var weight = "400 ";
    if (place.kind === "capital" || place.kind === "cape") {
      size = 14.5 * u;
      weight = "700 ";
      color = "#f2efe4";
    } else if (place.kind === "town") {
      if (view.east - view.west > 78 && place.name === "Brack") return null;
    } else if (place.kind === "water" || place.kind === "lake" || place.kind === "river") {
      size = place.kind === "river" ? 11.5 * u : 13 * u;
      color = "#d7f3ea";
    } else if (place.kind === "range" || place.kind === "region") {
      size = 12.5 * u;
      color = "#f0d3ae";
    } else {
      return null;
    }
    return {
      text: text,
      size: size,
      color: color,
      kind: place.kind,
      font: weight + Math.round(size) + "px \"Libre Baskerville\", Georgia, serif"
    };
  }

  function placeLabel(place, anchor, width, height, boxes) {
    var gaps;
    if (place.labelBias === "west") {
      gaps = [[-width - 12, -height / 2], [-width - 8, -height - 4], [-width - 8, 6]];
    } else if (place.labelBias === "east") {
      gaps = [[12, -height / 2], [12, -height - 4], [12, 6]];
    } else if (place.kind === "water" || place.kind === "lake") {
      gaps = [[-width / 2, -height / 2], [-width / 2, -height - 8], [8, -height / 2], [-width - 8, -height / 2]];
    } else if (place.labelBias === "north" || place.kind === "river") {
      gaps = [[-width / 2, -height - 16], [8, -height - 10], [-width - 8, -height / 2], [-width / 2, 10]];
    } else if (place.kind === "region" || place.kind === "range") {
      gaps = [[-width / 2, -height / 2], [-width / 2, -height - 8], [8, -height / 2]];
    } else {
      gaps = [[12, -height - 4], [12, 8], [-width - 12, -height / 2], [12, -height / 2], [-width - 12, 8]];
    }
    var i;
    for (i = 0; i < gaps.length; i += 1) {
      var x = anchor[0] + gaps[i][0];
      var y = anchor[1] + gaps[i][1];
      var box = { x: x - 5, y: y - 4, w: width + 10, h: height + 8 };
      if (box.x < 8 || box.y < 8 || box.x + box.w > canvas.width - 8 || box.y + box.h > canvas.height - 8) continue;
      if (hits(box, boxes)) continue;
      return { x: x, y: y, box: box };
    }
    return null;
  }

  function furnitureBoxes(u) {
    if (embed) return [];
    return [
      { x: 22 * u, y: 22 * u, w: 268 * u, h: 108 * u },
      { x: 22 * u, y: canvas.height - 128 * u, w: 168 * u, h: 100 * u },
      { x: canvas.width / 2 - 80 * u, y: canvas.height - 48 * u, w: 180 * u, h: 40 * u },
      { x: canvas.width - 52 * u, y: 8 * u, w: 44 * u, h: 44 * u }
    ];
  }

  function hits(box, boxes) {
    var i;
    for (i = 0; i < boxes.length; i += 1) {
      var b = boxes[i];
      if (box.x < b.x + b.w && box.x + box.w > b.x && box.y < b.y + b.h && box.y + box.h > b.y) return true;
    }
    return false;
  }

  function paintFurniture(g, u) {
    var x = 22 * u;
    var y = 22 * u;
    var w = 268 * u;
    var h = 108 * u;
    g.fillStyle = "rgba(16, 18, 14, 0.86)";
    g.strokeStyle = "rgba(242, 239, 228, 0.35)";
    g.lineWidth = Math.max(1, u);
    g.fillRect(x, y, w, h);
    g.strokeRect(x, y, w, h);
    g.textAlign = "left";
    g.textBaseline = "top";
    g.fillStyle = "#f2efe4";
    g.font = "700 " + Math.round(22 * u) + "px \"Libre Baskerville\", Georgia, serif";
    g.fillText("VAEL", x + 14 * u, y + 12 * u);
    g.font = "400 " + Math.round(14 * u) + "px \"Libre Baskerville\", Georgia, serif";
    g.fillStyle = "#d99a5b";
    g.fillText("The Crescent Sea", x + 14 * u, y + 38 * u);
    g.font = Math.round(11 * u) + "px Lato, Segoe UI, sans-serif";
    g.fillStyle = "#d7d3c6";
    g.fillText("Plate carrée on VAEL:2026", x + 14 * u, y + 64 * u);
    g.fillText("Sphere  R = 1,250 km  ·  seed 20261110", x + 14 * u, y + 80 * u);

    drawScale(g, u);
    drawLegend(g, u);
    drawNorth(g, u);
  }

  function drawScale(g, u) {
    var midLat = (view.south + view.north) / 2;
    var km = VaelWorld.kmPerDegree(midLat);
    var kmPerPx = km.lon / (canvas.width / (view.east - view.west));
    var choices = [25, 50, 100, 200, 400, 800];
    var targetPx = 130 * u;
    var best = choices[0];
    var i;
    for (i = 0; i < choices.length; i += 1) {
      if (choices[i] / kmPerPx <= targetPx) best = choices[i];
    }
    var px = best / kmPerPx;
    var x = canvas.width / 2 - px / 2;
    var y = canvas.height - 28 * u;
    g.strokeStyle = "#f2efe4";
    g.fillStyle = "#f2efe4";
    g.lineWidth = Math.max(1, 1.4 * u);
    g.beginPath();
    g.moveTo(x, y);
    g.lineTo(x + px, y);
    g.moveTo(x, y - 4 * u);
    g.lineTo(x, y + 4 * u);
    g.moveTo(x + px, y - 4 * u);
    g.lineTo(x + px, y + 4 * u);
    g.stroke();
    g.font = Math.round(11 * u) + "px Lato, Segoe UI, sans-serif";
    g.textAlign = "left";
    g.textBaseline = "bottom";
    g.fillText(best + " km at " + Math.abs(midLat).toFixed(0) + "°" + (midLat >= 0 ? "N" : "S"), x, y - 6 * u);
  }

  function drawLegend(g, u) {
    if (!layers.realms && !layers.labels) return;
    var x = 22 * u;
    var y = canvas.height - 128 * u;
    g.fillStyle = "rgba(16, 18, 14, 0.86)";
    g.strokeStyle = "rgba(242, 239, 228, 0.35)";
    g.lineWidth = Math.max(1, u);
    g.fillRect(x, y, 168 * u, 100 * u);
    g.strokeRect(x, y, 168 * u, 100 * u);
    var realms = ["orro", "mere", "cinder"];
    g.font = Math.round(11 * u) + "px Lato, Segoe UI, sans-serif";
    g.textAlign = "left";
    g.textBaseline = "middle";
    realms.forEach(function (id, index) {
      var realm = VaelWorld.REALMS[id];
      var yy = y + 16 * u + index * 16 * u;
      g.strokeStyle = realm.color;
      g.lineWidth = Math.max(1.5, 2 * u);
      g.beginPath();
      g.moveTo(x + 12 * u, yy);
      g.lineTo(x + 26 * u, yy);
      g.stroke();
      g.fillStyle = "#f2efe4";
      g.fillText(realm.name, x + 32 * u, yy + 1 * u);
    });
    var rampX = x + 12 * u;
    var rampY = y + 68 * u;
    var rampW = 144 * u;
    var step;
    for (step = 0; step < 24; step += 1) {
      var t = step / 23;
      var elev = t < 0.45 ? -2200 + (t / 0.45) * 2200 : ((t - 0.45) / 0.55) * 2800;
      var rgb = elev < 0 ? ramp(BATH, elev) : ramp(LAND, elev);
      g.fillStyle = "rgb(" + rgb.map(function (v) { return Math.round(v); }).join(",") + ")";
      g.fillRect(rampX + (rampW * step) / 24, rampY, rampW / 24 + 1, 8 * u);
    }
    g.fillStyle = "#d7d3c6";
    g.font = Math.round(10 * u) + "px Lato, Segoe UI, sans-serif";
    g.textBaseline = "top";
    g.fillText("deep", rampX, rampY + 10 * u);
    g.textAlign = "right";
    g.fillText("high", rampX + rampW, rampY + 10 * u);
    g.textAlign = "left";
  }

  function drawNorth(g, u) {
    var x = canvas.width - 36 * u;
    var y = 28 * u;
    g.fillStyle = "#f2efe4";
    g.beginPath();
    g.moveTo(x, y);
    g.lineTo(x - 6 * u, y + 16 * u);
    g.lineTo(x, y + 11 * u);
    g.lineTo(x + 6 * u, y + 16 * u);
    g.closePath();
    g.fill();
    g.font = "700 " + Math.round(11 * u) + "px Lato, Segoe UI, sans-serif";
    g.textAlign = "center";
    g.textBaseline = "bottom";
    g.fillText("N", x, y - 2 * u);
  }

  function paintPin(g, place) {
    var p = project(place.lon, place.lat);
    var u = unit();
    var halo = (place.kind === "water" || place.kind === "region" || place.kind === "range" || place.kind === "lake") ? 28 : 16;
    g.beginPath();
    g.arc(p[0], p[1], halo * u, 0, Math.PI * 2);
    g.fillStyle = "rgba(217, 154, 91, 0.22)";
    g.fill();
    g.strokeStyle = "rgba(217, 154, 91, 0.9)";
    g.lineWidth = Math.max(1, 1.4 * u);
    g.stroke();
  }

  function paintMarker(g, lon, lat, color) {
    var p = project(lon, lat);
    var u = unit();
    g.strokeStyle = color;
    g.lineWidth = Math.max(1, 1.4 * u);
    g.beginPath();
    g.arc(p[0], p[1], 8 * u, 0, Math.PI * 2);
    g.stroke();
  }

  function redraw() {
    if (!geo) geo = VaelWorld.buildGeometry();
    if (!surface) surface = VaelWorld.surface();
    cache.width = canvas.width;
    cache.height = canvas.height;
    paintRelief(cacheCtx);
    paintVectors(cacheCtx);
    blit();
    if (still) window.__VAEL_READY = true;
  }

  function blit() {
    ctx.drawImage(cache, 0, 0);
    if (hover && !dragging) paintMarker(ctx, hover[0], hover[1], "rgba(242, 239, 228, 0.8)");
  }

  function blitDrag() {
    var spanLon = dragView.east - dragView.west;
    var spanLat = dragView.north - dragView.south;
    var dx = ((dragView.west - view.west) / spanLon) * canvas.width;
    var dy = ((view.north - dragView.north) / spanLat) * canvas.height;
    ctx.fillStyle = "#101412";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(cache, dx, dy);
  }

  function formatReadout(lon, lat) {
    var s = VaelWorld.sample(lon, lat);
    var ns = (lat >= 0 ? "N" : "S");
    var ew = (lon >= 0 ? "E" : "W");
    var where = s.land ? s.realmName : s.water;
    var elev = Math.round(s.elevationM).toLocaleString("en-US") + " m";
    return Math.abs(lat).toFixed(2) + "° " + ns
      + "   " + Math.abs(lon).toFixed(2) + "° " + ew
      + "   ·   " + elev
      + "   ·   " + where;
  }

  function clampView() {
    var ext = VaelWorld.worldExtent();
    var cx = (ext.west + ext.east) / 2;
    var cy = (ext.south + ext.north) / 2;
    var vw = view.east - view.west;
    var vh = view.north - view.south;
    var mx = (view.west + view.east) / 2;
    var my = (view.south + view.north) / 2;
    var limitX = Math.max(vw * 0.2, (ext.east - ext.west) * 0.55);
    var limitY = Math.max(vh * 0.2, (ext.north - ext.south) * 0.55);
    if (mx < cx - limitX) mx = cx - limitX;
    if (mx > cx + limitX) mx = cx + limitX;
    if (my < cy - limitY) my = cy - limitY;
    if (my > cy + limitY) my = cy + limitY;
    view = { west: mx - vw / 2, east: mx + vw / 2, south: my - vh / 2, north: my + vh / 2 };
  }

  function zoomAt(lon, lat, factor) {
    var vw = (view.east - view.west) * factor;
    var vh = (view.north - view.south) * factor;
    var minW = 12;
    var maxW = fitWidth * 1.02;
    if (vw < minW || vw > maxW) return;
    var rx = (lon - view.west) / (view.east - view.west);
    var ry = (lat - view.south) / (view.north - view.south);
    view = {
      west: lon - rx * vw,
      east: lon + (1 - rx) * vw,
      south: lat - ry * vh,
      north: lat + (1 - ry) * vh
    };
    clampView();
    redraw();
  }

  function centerOn(lon, lat) {
    var vw = view.east - view.west;
    var vh = view.north - view.south;
    view = {
      west: lon - vw / 2,
      east: lon + vw / 2,
      south: lat - vh / 2,
      north: lat + vh / 2
    };
    clampView();
    redraw();
  }

  var placeButtons = [];

  function markSelected() {
    placeButtons.forEach(function (entry) {
      var on = selected && entry.place.name === selected.name && entry.place.kind === selected.kind;
      entry.button.classList.toggle("is-on", Boolean(on));
      entry.button.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  function showPlace(place) {
    selected = place;
    markSelected();
    var span = view.east - view.west;
    var want = (place.kind === "water" || place.kind === "region") ? 52 : 28;
    var vw = Math.min(span, want);
    var vh = vw * (canvas.height / Math.max(1, canvas.width));
    var cx = place.lon + vw * 0.16;
    var cy = place.lat;
    view = {
      west: cx - vw / 2,
      east: cx + vw / 2,
      south: cy - vh / 2,
      north: cy + vh / 2
    };
    clampView();
    redraw();
    if (readout) readout.textContent = place.name + " — " + place.blurb;
  }

  function clearSelection() {
    selected = null;
    markSelected();
  }

  function addPlaceGroup(list, title, places) {
    if (!places.length) return;
    var heading = document.createElement("p");
    heading.className = "vael-realm";
    heading.textContent = title;
    list.appendChild(heading);
    var row = document.createElement("div");
    row.className = "vael-places";
    places.forEach(function (place) {
      var button = document.createElement("button");
      button.type = "button";
      button.textContent = place.name;
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", function () { showPlace(place); });
      placeButtons.push({ place: place, button: button });
      row.appendChild(button);
    });
    list.appendChild(row);
  }

  function fillPanel() {
    var list = document.getElementById("vael-place-list");
    var prompts = document.getElementById("vael-prompt-list");
    if (!list || !prompts) return;
    var places = VaelWorld.places();
    addPlaceGroup(list, "Orro Reach", places.filter(function (p) {
      return p.realm === "orro" && (p.kind === "cape" || p.kind === "capital" || p.kind === "town");
    }));
    addPlaceGroup(list, "Mere Compact", places.filter(function (p) {
      return p.realm === "mere" && (p.kind === "capital" || p.kind === "town");
    }));
    addPlaceGroup(list, "Cinder League", places.filter(function (p) {
      return p.realm === "cinder" && (p.kind === "capital" || p.kind === "town");
    }));
    addPlaceGroup(list, "Seas and landforms", places.filter(function (p) {
      return p.kind === "water" || p.kind === "lake" || p.kind === "range" || p.kind === "region";
    }));
    var rivers = (VaelWorld.buildGeometry().rivers || []).filter(function (river) {
      return river.coordinates && river.coordinates.length > 2;
    }).map(function (river) {
      var mid = river.coordinates[Math.floor(river.coordinates.length * 0.45)];
      return {
        name: river.name,
        kind: "river",
        lon: mid[0],
        lat: mid[1],
        blurb: "Meandering river. Mouth: " + (river.mouth || "the sea") + "."
      };
    });
    addPlaceGroup(list, "Rivers", rivers);
    VaelWorld.PROMPTS.forEach(function (prompt) {
      var block = document.createElement("section");
      block.className = "vael-prompt";
      var kicker = document.createElement("p");
      kicker.className = "vael-kicker";
      kicker.textContent = "Prompt " + prompt.id + " · " + prompt.role;
      var heading = document.createElement("h3");
      heading.textContent = prompt.title;
      var body = document.createElement("p");
      body.textContent = prompt.text;
      block.appendChild(kicker);
      block.appendChild(heading);
      block.appendChild(body);
      prompts.appendChild(block);
    });
  }

  function bind() {
    document.querySelectorAll("[data-layer]").forEach(function (button) {
      button.addEventListener("click", function () {
        var key = button.getAttribute("data-layer");
        layers[key] = !layers[key];
        button.setAttribute("aria-pressed", layers[key] ? "true" : "false");
        redraw();
      });
    });
    var reset = document.getElementById("vael-reset");
    if (reset) {
      reset.addEventListener("click", function () {
        clearSelection();
        hover = null;
        fitView();
        redraw();
        if (readout) readout.textContent = "Full sheet. Longitude 0 is Cape Orro.";
      });
    }
    if (notesBtn && panel) {
      notesBtn.addEventListener("click", function () {
        var open = panel.hasAttribute("hidden");
        if (open) panel.removeAttribute("hidden");
        else panel.setAttribute("hidden", "");
        notesBtn.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }
    canvas.addEventListener("pointerdown", function (event) {
      dragging = true;
      dragMoved = false;
      lastPt = [event.clientX, event.clientY];
      dragView = {
        west: view.west,
        east: view.east,
        south: view.south,
        north: view.north
      };
      canvas.classList.add("is-dragging");
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener("pointermove", function (event) {
      if (!view) return;
      if (dragging && lastPt && dragView) {
        var dx = event.clientX - lastPt[0];
        var dy = event.clientY - lastPt[1];
        if (Math.abs(dx) + Math.abs(dy) > 3) dragMoved = true;
        var rect = canvas.getBoundingClientRect();
        var dLon = (dx / rect.width) * (view.east - view.west);
        var dLat = (dy / rect.height) * (view.north - view.south);
        view = {
          west: view.west - dLon,
          east: view.east - dLon,
          south: view.south + dLat,
          north: view.north + dLat
        };
        lastPt = [event.clientX, event.clientY];
        clampView();
        blitDrag();
        return;
      }
      if (embed) return;
      hover = unproject(event.clientX, event.clientY);
      if (readout) readout.textContent = formatReadout(hover[0], hover[1]);
      blit();
    });
    canvas.addEventListener("pointerup", function (event) {
      var moved = dragMoved;
      dragging = false;
      dragView = null;
      canvas.classList.remove("is-dragging");
      if (moved) redraw();
      else {
        var ll = unproject(event.clientX, event.clientY);
        clearSelection();
        hover = ll;
        if (readout) readout.textContent = formatReadout(ll[0], ll[1]);
        blit();
      }
      lastPt = null;
    });
    canvas.addEventListener("pointerleave", function () {
      if (dragging) return;
      hover = null;
      blit();
    });
    canvas.addEventListener("wheel", function (event) {
      event.preventDefault();
      var ll = unproject(event.clientX, event.clientY);
      zoomAt(ll[0], ll[1], event.deltaY > 0 ? 1.12 : 0.89);
    }, { passive: false });
    canvas.addEventListener("dblclick", function () {
      clearSelection();
      fitView();
      redraw();
    });
    window.addEventListener("resize", function () {
      if (still) return;
      resize();
      fitView();
      redraw();
    });
    window.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && panel && !panel.hasAttribute("hidden")) {
        panel.setAttribute("hidden", "");
        if (notesBtn) notesBtn.setAttribute("aria-expanded", "false");
      }
    });
  }

  function boot() {
    try {
      fillPanel();
      bind();
      resize();
      fitView();
      redraw();
      if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(function () { redraw(); });
      }
    } catch (err) {
      if (readout) readout.textContent = err && err.message ? err.message : "The chart failed to draw.";
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
