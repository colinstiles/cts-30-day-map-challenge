// Vael — fictional world for Day 10 (Prompting only).
// Coordinates are degrees on the Vael sphere (VAEL:2026), not Earth / WGS84.
// Longitude 0 is the Cape Orro meridian. Latitude 0 is the Vael equator,
// which crosses the Glass Mere. Sphere radius is 1,250 km.
(function (factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.VaelWorld = api;
})(function () {
  "use strict";

  var SEED = 20261110;
  var RADIUS_M = 1250000;
  var RADIUS_KM = RADIUS_M / 1000;
  var GENERATOR = "vael-world.js@1";

  // Design frame. Published lon/lat subtract SHIFT so Cape Orro sits at lon 0.
  // SHIFT is frozen (not recomputed) so Day 22 geometry does not drift.
  var SHIFT = { lon: 3.2, lat: 0 };

  var GEO = {
    crescent: { cx: 26.2, cy: 5.1 },
    mere: { cx: 27.7, cy: 5.35 },
    plateau: { cx: 14.2, cy: 23.4, rx: 13.6, ry: 8.0 },
    lake: { cx: 12.4, cy: 26.6, rx: 1.45, ry: 0.95 },
    mouthHalfWidth: 3.15
  };

  // Design-frame extent of the charted sheet. World extent is this minus SHIFT.
  var DESIGN_EXTENT = { west: -8, south: -36, east: 92, north: 40 };

  var REALMS = {
    orro: {
      id: "orro",
      name: "Orro Reach",
      color: "#9CBB74",
      blurb: "Western highlands, the Pale Spine, and the cape that fixes the prime meridian."
    },
    mere: {
      id: "mere",
      name: "Mere Compact",
      color: "#D99A5B",
      blurb: "The harbors and headlands around the Glass Mere, bound by a treaty meridian."
    },
    cinder: {
      id: "cinder",
      name: "Cinder League",
      color: "#E07A4C",
      blurb: "Volcanic islands of the Cinder Chain, southeast of the Narrows."
    }
  };

  var ISLANDS = [
    { name: "Ashwake", lon: 58.2, lat: -8.2, r: 3.35, capital: true },
    { name: "Cinder", lon: 65.4, lat: -14.0, r: 2.65, peak: true },
    { name: "Low Bell", lon: 52.4, lat: -14.4, r: 2.05 },
    { name: "Kelp", lon: 72.6, lat: -19.2, r: 2.25 },
    { name: "Nun", lon: 61.4, lat: -21.2, r: 1.4 },
    { name: "Brack", lon: 78.4, lat: -12.2, r: 1.2 }
  ];

  // Design longitudes. kind: capital | town | water | region | range | lake
  var PLACES = [
    { name: "Cape Orro", kind: "cape", realm: "orro", lon: 4.6, lat: 5.1, labelBias: "west",
      blurb: "Western headland of Cairn. Longitude 0 is the meridian of this cape." },
    { name: "Orro", kind: "capital", realm: "orro", lon: 6.4, lat: 5.0, labelBias: "east",
      blurb: "Capital of Orro Reach, just inland of Cape Orro." },
    { name: "High Ash", kind: "town", realm: "orro", lon: 15.2, lat: 14.4,
      blurb: "Stone town on the Pale Spine, above the headwaters of the Slow Ribbon." },
    { name: "Thornstep", kind: "town", realm: "orro", lon: 16.2, lat: 24.2,
      blurb: "Plateau market east of Lake Merrin." },
    { name: "Siltmouth", kind: "town", realm: "mere", lon: 35.5, lat: 12.2,
      blurb: "North-headland port where the Glass Mere meets the Narrows." },
    { name: "Harrow Quay", kind: "town", realm: "mere", lon: 36.8, lat: 0.4,
      blurb: "South-headland quay opposite Siltmouth." },
    { name: "Vellum", kind: "capital", realm: "mere", lon: 29.6, lat: 14.6,
      blurb: "Capital of the Mere Compact, on the north shore of the inland sea." },
    { name: "Brine", kind: "town", realm: "mere", lon: 28.4, lat: -4.6,
      blurb: "Salt town on the south shore of the Glass Mere." },
    { name: "Redwick", kind: "town", realm: "mere", lon: 40.2, lat: 16.2,
      blurb: "Inland town in the eastern hills of Cairn." },
    { name: "Pell", kind: "town", realm: "mere", lon: 44.8, lat: 12.6,
      blurb: "Outer-coast harbor facing the Cinder Chain." },
    { name: "Ashwake", kind: "capital", realm: "cinder", lon: 58.2, lat: -8.2,
      blurb: "Seat of the Cinder League, on the largest island of the chain." },
    { name: "Cinder", kind: "town", realm: "cinder", lon: 65.4, lat: -14.0,
      blurb: "Town under the chain's highest volcanic peak." },
    { name: "Low Bell", kind: "town", realm: "cinder", lon: 52.4, lat: -14.4,
      blurb: "Westernmost island of the league, nearest the Narrows." },
    { name: "Kelp", kind: "town", realm: "cinder", lon: 72.6, lat: -19.2,
      blurb: "Fishing island at the southeast end of the chain." },
    { name: "Nun", kind: "town", realm: "cinder", lon: 61.4, lat: -21.2,
      blurb: "Small steep island south of Cinder." },
    { name: "Brack", kind: "town", realm: "cinder", lon: 78.4, lat: -12.2,
      blurb: "Eastern outlier of the Cinder Chain." },
    { name: "Cairn", kind: "region", lon: 16.4, lat: -1.6,
      blurb: "The single continent of the charted sheet." },
    { name: "Pale Spine", kind: "range", lon: 13.0, lat: 16.0,
      blurb: "Mountain arc along the western rim of Cairn." },
    { name: "Lake Merrin", kind: "lake", lon: 12.4, lat: 26.6,
      blurb: "Crater lake on the Thornstep plateau." },
    { name: "Glass Mere", kind: "water", lon: 27.7, lat: 5.2,
      blurb: "Nearly enclosed inland sea. The Vael equator crosses it." },
    { name: "The Narrows", kind: "water", lon: 43.5, lat: 4.6,
      blurb: "Strait between the Glass Mere and the Outer Quiet." },
    { name: "The Outer Quiet", kind: "water", lon: 68, lat: 26,
      blurb: "Uncharted ocean beyond the crescent and the island chain." },
    { name: "Cinder Chain", kind: "region", lon: 66, lat: -26.5,
      blurb: "Volcanic arc southeast of Cairn." }
  ];

  var RIVER_SEEDS = [
    { name: "Slow Ribbon", lon: 20.2, lat: 14.8 },
    { name: "Ashwash", lon: 9.2, lat: -0.6 },
    { name: "Merrin Brook", lon: 14.8, lat: 28.2 }
  ];

  var PROMPTS = [
    {
      id: 1,
      role: "Colin",
      title: "Day brief",
      text: "Work the Day 10 map from the 2026 plan. Theme: Prompting only. Use AI from start to finish, purely through prompting, to invent an entirely fictional place or world. No real-world data. Document the prompt chain beside the result. The world is also the base for Day 22, so keep a coordinate system, extent, and coastline geometry in a reusable form. Static, interactive, or both."
    },
    {
      id: 2,
      role: "Working prompt",
      title: "Invent the world",
      text: "Invent one ocean world, not a copy of Earth. Name it Vael. Radius 1,250 km, a sphere. Longitude 0 is the meridian of Cape Orro. Latitude 0 crosses an inland sea. Chart only the inhabited sheet: one crescent continent (Cairn) wrapped around that sea (the Glass Mere), open to the east through a strait (the Narrows), a northern plateau with a crater lake (Merrin), a western mountain arc (the Pale Spine), and a volcanic island arc to the southeast (the Cinder Chain). Three polities: Orro Reach on the highlands and cape, the Mere Compact around the inland sea, the Cinder League on the islands. Place names, borders, rivers, and terrain must come from this description and a fixed seed (20261110). Do not import Earth coastlines, DEMs, or place names."
    },
    {
      id: 3,
      role: "Working prompt",
      title: "Draw it and file the geometry",
      text: "Turn that description into a deterministic elevation field and extract coastline, realm, river, and place geometry. Publish the sheet as a plate carrée chart, labeled as a display choice rather than the datum. Write VAEL:2026 (sphere, R = 1,250,000 m), the mapped extent, and GeoJSON in Vael degrees for Day 22. Keep the generator and the geometry in the repo so the projection day can reuse them without redrawing."
    }
  ];

  function hash(ix, iy, salt) {
    var n = Math.imul(ix | 0, 374761393) ^ Math.imul(iy | 0, 668265263) ^ Math.imul((salt + SEED) | 0, 1442695041);
    n = Math.imul(n ^ (n >>> 13), 1274126177);
    n ^= n >>> 16;
    return (n >>> 0) / 4294967296;
  }

  function fade(t) {
    return t * t * (3 - 2 * t);
  }

  function valueNoise(x, y, salt) {
    var x0 = Math.floor(x);
    var y0 = Math.floor(y);
    var tx = fade(x - x0);
    var ty = fade(y - y0);
    var v00 = hash(x0, y0, salt);
    var v10 = hash(x0 + 1, y0, salt);
    var v01 = hash(x0, y0 + 1, salt);
    var v11 = hash(x0 + 1, y0 + 1, salt);
    var a = v00 + (v10 - v00) * tx;
    var b = v01 + (v11 - v01) * tx;
    return a + (b - a) * ty;
  }

  function fbm(x, y, octaves, salt) {
    var amp = 1;
    var sum = 0;
    var norm = 0;
    var freq = 1;
    var o;
    for (o = 0; o < octaves; o += 1) {
      sum += amp * valueNoise(x * freq, y * freq, salt + o * 19);
      norm += amp;
      amp *= 0.5;
      freq *= 2.05;
    }
    return sum / norm;
  }

  function smoothMax(a, b, k) {
    var h = Math.max(k - Math.abs(a - b), 0) / k;
    return Math.max(a, b) + h * h * k * 0.25;
  }

  function toDesign(lon, lat) {
    return [lon + SHIFT.lon, lat + SHIFT.lat];
  }

  function toWorldLon(designLon) {
    return designLon - SHIFT.lon;
  }

  function toWorldLat(designLat) {
    return designLat - SHIFT.lat;
  }

  function warp(lon, lat) {
    var wx = (fbm(lon * 0.08, lat * 0.08, 3, 11) - 0.5) * 3.2;
    var wy = (fbm(lon * 0.08 + 4.2, lat * 0.08 - 2.1, 3, 29) - 0.5) * 3.2;
    return [lon + wx, lat + wy];
  }

  // Signed degrees-like field. Positive is land. The mouth is a parallel-sided
  // cut from the mere eastward so the crescent stays one continent and still opens.
  function crescentField(lon, lat) {
    var c = GEO.crescent;
    var dx = lon - c.cx;
    var dy = lat - c.cy;
    var r = Math.hypot(dx, dy) || 1e-6;
    var ang = Math.atan2(dy, dx);
    var outerR = 21.4 + 1.7 * Math.cos(ang * 2) + 1.05 * Math.sin(ang * 3);
    var m = GEO.mere;
    var dx2 = lon - m.cx;
    var dy2 = lat - m.cy;
    var r2 = Math.hypot(dx2, dy2);
    var ang2 = Math.atan2(dy2, dx2);
    var innerR = 9.15 + 0.95 * Math.cos(ang2 * 2) + 0.35 * Math.sin(ang2 * 3);
    var ring = Math.min(outerR - r, r2 - innerR);
    var along = dx2;
    var across = Math.abs(dy2 - dx2 * 0.06);
    var mouth = along < 6.2 ? 40 : across - GEO.mouthHalfWidth;
    return Math.min(ring, mouth);
  }

  function plateauField(lon, lat) {
    var p = GEO.plateau;
    var nx = (lon - p.cx) / p.rx;
    var ny = (lat - p.cy) / p.ry;
    var d = Math.hypot(nx, ny);
    return (1 - d) * Math.min(p.rx, p.ry);
  }

  function islandField(lon, lat) {
    var best = -99;
    var n = (fbm(lon * 0.48, lat * 0.48, 3, 41) - 0.5) * 1.2;
    var i;
    var isl;
    var d;
    for (i = 0; i < ISLANDS.length; i += 1) {
      isl = ISLANDS[i];
      d = Math.hypot(lon - isl.lon, lat - isl.lat);
      best = Math.max(best, isl.r + n * (0.7 + 0.3 * Math.sin(i * 2.2)) - d);
    }
    return best;
  }

  function lakeField(lon, lat) {
    var lake = GEO.lake;
    var n = Math.hypot((lon - lake.cx) / lake.rx, (lat - lake.cy) / lake.ry);
    return 1.2 - n;
  }

  function signedLandDesign(lon, lat) {
    var w = warp(lon, lat);
    var macro = smoothMax(crescentField(w[0], w[1]), plateauField(w[0], w[1]), 4.2);
    var islands = islandField(lon, lat);
    var base = Math.max(macro, islands);
    var amp = Math.exp(-Math.max(-base, 0) / 1.85) * 1.65;
    var detail = (fbm(lon * 0.22, lat * 0.22, 5, 3) - 0.5) * 2 * amp;
    var field = base + detail;
    var lake = lakeField(lon, lat);
    if (lake > 0) field = Math.min(field, -0.45 - lake * 0.55);
    return field;
  }

  function spineMask(lon, lat) {
    var c = GEO.crescent;
    var dx = lon - c.cx;
    var dy = lat - c.cy;
    var r = Math.hypot(dx, dy);
    var ang = Math.atan2(dy, dx);
    var west = Math.pow(Math.max(0, -Math.cos(ang)), 1.15);
    var onRim = Math.exp(-((r - 14.6) * (r - 14.6)) / (2 * 3.3 * 3.3));
    return west * onRim;
  }

  function plateauMask(lon, lat) {
    var p = GEO.plateau;
    var n = Math.hypot((lon - p.cx) / p.rx, (lat - p.cy) / p.ry);
    if (n >= 1) return 0;
    return Math.pow(1 - n, 1.35);
  }

  function volcanoMask(lon, lat) {
    var m = 0;
    var i;
    var isl;
    var d;
    var amp;
    var sigma;
    for (i = 0; i < ISLANDS.length; i += 1) {
      isl = ISLANDS[i];
      d = Math.hypot(lon - isl.lon, lat - isl.lat);
      amp = isl.peak ? 1 : 0.62;
      sigma = isl.r * 0.52;
      m = Math.max(m, amp * Math.exp(-(d * d) / (2 * sigma * sigma)));
    }
    return m;
  }

  function elevationDesign(lon, lat, signedKnown) {
    var s = signedKnown === undefined ? signedLandDesign(lon, lat) : signedKnown;
    var n;
    var h;
    if (s <= 0) {
      n = fbm(lon * 0.07, lat * 0.07, 3, 9);
      return -Math.min(4600, 25 - s * 410 + n * 280);
    }
    n = fbm(lon * 0.16, lat * 0.16, 4, 5);
    h = 12 + Math.min(s, 5.5) * 48;
    h += spineMask(lon, lat) * (820 + n * 2100);
    h += plateauMask(lon, lat) * (460 + n * 520);
    h += volcanoMask(lon, lat) * (380 + n * 1750);
    h += (n - 0.5) * 320 * Math.min(1, s / 2);
    return Math.max(2, Math.min(3600, h));
  }

  function islandDominates(lon, lat) {
    var islands = islandField(lon, lat);
    if (islands <= 0.2) return false;
    var w = warp(lon, lat);
    var continent = smoothMax(crescentField(w[0], w[1]), plateauField(w[0], w[1]), 4.2);
    return islands > continent;
  }

  function realmDesign(lon, lat, signedKnown) {
    var signed = signedKnown === undefined ? signedLandDesign(lon, lat) : signedKnown;
    if (signed <= 0) return null;
    if (islandDominates(lon, lat)) return "cinder";
    var treaty = 22.4 + (lat - 5) * 0.16;
    if (lon < treaty || lat > 19.8) return "orro";
    return "mere";
  }

  function waterBodyDesign(lon, lat) {
    if (signedLandDesign(lon, lat) > 0) return null;
    if (lakeField(lon, lat) > 0.15 && plateauMask(lon, lat) > 0.2) return "Lake Merrin";
    var m = GEO.mere;
    var d = Math.hypot(lon - m.cx, lat - m.cy);
    if (d < 10.4) return "Glass Mere";
    var dx = lon - m.cx;
    var dy = lat - m.cy;
    if (dx > 4 && Math.abs(dy - dx * 0.06) < GEO.mouthHalfWidth + 1.4 && dx < 22) return "The Narrows";
    return "The Outer Quiet";
  }

  function elevation(lon, lat) {
    var d = toDesign(lon, lat);
    return elevationDesign(d[0], d[1]);
  }

  function sample(lon, lat) {
    var d = toDesign(lon, lat);
    var realm = realmDesign(d[0], d[1]);
    var elev = elevationDesign(d[0], d[1]);
    return {
      elevationM: elev,
      land: elev > 0,
      realm: realm,
      realmName: realm ? REALMS[realm].name : null,
      water: waterBodyDesign(d[0], d[1])
    };
  }

  function worldExtent() {
    return {
      west: toWorldLon(DESIGN_EXTENT.west),
      east: toWorldLon(DESIGN_EXTENT.east),
      south: toWorldLat(DESIGN_EXTENT.south),
      north: toWorldLat(DESIGN_EXTENT.north)
    };
  }

  function placesWorld() {
    return PLACES.map(function (p) {
      return {
        name: p.name,
        kind: p.kind,
        realm: p.realm || null,
        realmName: p.realm ? REALMS[p.realm].name : null,
        lon: toWorldLon(p.lon),
        lat: toWorldLat(p.lat),
        blurb: p.blurb,
        labelBias: p.labelBias || null
      };
    });
  }

  function kmPerDegree(latDeg) {
    var lat = (latDeg * Math.PI) / 180;
    return {
      lat: RADIUS_KM * Math.PI / 180,
      lon: RADIUS_KM * Math.PI / 180 * Math.cos(lat)
    };
  }

  function keyOf(pt) {
    return pt[0].toFixed(3) + "," + pt[1].toFixed(3);
  }

  function lerpZero(p0, p1, v0, v1) {
    var denom = v0 - v1;
    var t = denom === 0 ? 0.5 : v0 / denom;
    if (t < 0) t = 0;
    if (t > 1) t = 1;
    return p0 + (p1 - p0) * t;
  }

  function contourPairs(mask, centerPositive) {
    switch (mask) {
      case 1: return [["W", "S"]];
      case 2: return [["S", "E"]];
      case 3: return [["W", "E"]];
      case 4: return [["E", "N"]];
      case 5: return centerPositive ? [["W", "N"], ["S", "E"]] : [["W", "S"], ["E", "N"]];
      case 6: return [["S", "N"]];
      case 7: return [["W", "N"]];
      case 8: return [["N", "W"]];
      case 9: return [["N", "S"]];
      case 10: return centerPositive ? [["N", "E"], ["W", "S"]] : [["N", "W"], ["E", "S"]];
      case 11: return [["N", "E"]];
      case 12: return [["E", "W"]];
      case 13: return [["E", "S"]];
      case 14: return [["S", "W"]];
      default: return [];
    }
  }

  function linkSegments(segs) {
    var adj = new Map();
    function add(a, b) {
      var k = keyOf(a);
      if (!adj.has(k)) adj.set(k, []);
      adj.get(k).push(b);
    }
    segs.forEach(function (seg) {
      add(seg[0], seg[1]);
      add(seg[1], seg[0]);
    });
    var used = new Set();
    function ek(a, b) {
      var ka = keyOf(a);
      var kb = keyOf(b);
      return ka < kb ? ka + "|" + kb : kb + "|" + ka;
    }
    var rings = [];
    segs.forEach(function (seg) {
      if (used.has(ek(seg[0], seg[1]))) return;
      var ring = [seg[0]];
      var prev = null;
      var cur = seg[0];
      var guard = 0;
      while (guard < segs.length + 2) {
        guard += 1;
        var nbs = adj.get(keyOf(cur)) || [];
        var incoming = null;
        if (prev) {
          incoming = [cur[0] - prev[0], cur[1] - prev[1]];
        }
        var best = null;
        var bestScore = -Infinity;
        nbs.forEach(function (nb) {
          var id = ek(cur, nb);
          if (used.has(id)) return;
          if (prev && keyOf(nb) === keyOf(prev)) return;
          var score = 0;
          if (incoming) {
            var vx = nb[0] - cur[0];
            var vy = nb[1] - cur[1];
            var mag = Math.hypot(incoming[0], incoming[1]) * Math.hypot(vx, vy);
            score = mag === 0 ? 0 : (incoming[0] * vx + incoming[1] * vy) / mag;
          }
          if (score > bestScore) {
            bestScore = score;
            best = nb;
          }
        });
        if (!best) break;
        used.add(ek(cur, best));
        ring.push(best);
        if (keyOf(best) === keyOf(ring[0]) && ring.length > 3) break;
        prev = cur;
        cur = best;
      }
      if (ring.length > 8) rings.push(ring);
    });
    return rings;
  }

  function ringArea(ring) {
    var a = 0;
    var i;
    var j;
    for (i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
      a += ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1];
    }
    return a / 2;
  }

  function pointInRing(lon, lat, ring) {
    var inside = false;
    var i;
    var j;
    for (i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
      var yi = ring[i][1];
      var yj = ring[j][1];
      var xi = ring[i][0];
      var xj = ring[j][0];
      var intersect = (yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / ((yj - yi) || 1e-12) + xi;
      if (intersect) inside = !inside;
    }
    return inside;
  }

  function rdp(points, epsilon) {
    if (points.length < 3) return points.slice();
    var first = points[0];
    var last = points[points.length - 1];
    var dx = last[0] - first[0];
    var dy = last[1] - first[1];
    var mag = Math.hypot(dx, dy) || 1;
    var maxDist = -1;
    var index = -1;
    var i;
    for (i = 1; i < points.length - 1; i += 1) {
      var dist = Math.abs(dy * points[i][0] - dx * points[i][1] + last[0] * first[1] - last[1] * first[0]) / mag;
      if (dist > maxDist) {
        maxDist = dist;
        index = i;
      }
    }
    if (maxDist > epsilon) {
      var left = rdp(points.slice(0, index + 1), epsilon);
      var right = rdp(points.slice(index), epsilon);
      return left.slice(0, -1).concat(right);
    }
    return [first, last];
  }

  function roundRing(ring) {
    return ring.map(function (pt) {
      return [Math.round(pt[0] * 1000) / 1000, Math.round(pt[1] * 1000) / 1000];
    });
  }

  function interiorProbe(ring) {
    var bestLen = -1;
    var bestI = 0;
    var i;
    for (i = 0; i < ring.length - 1; i += 1) {
      var len = Math.hypot(ring[i + 1][0] - ring[i][0], ring[i + 1][1] - ring[i][1]);
      if (len > bestLen) {
        bestLen = len;
        bestI = i;
      }
    }
    var a = ring[bestI];
    var b = ring[bestI + 1];
    var mx = (a[0] + b[0]) / 2;
    var my = (a[1] + b[1]) / 2;
    var vx = b[0] - a[0];
    var vy = b[1] - a[1];
    var mag = Math.hypot(vx, vy) || 1;
    var lx = mx + (-vy / mag) * 0.28;
    var ly = my + (vx / mag) * 0.28;
    if (pointInRing(lx, ly, ring)) return [lx, ly];
    return [mx - (-vy / mag) * 0.28, my - (vx / mag) * 0.28];
  }

  var SURFACE_STEP = 0.3;
  var surfaceCache = null;

  // One analytic pass for relief, coastline, and realms. Later lookups bilinear-sample it.
  function warmSurface() {
    if (surfaceCache) return surfaceCache;
    var ext = DESIGN_EXTENT;
    var step = SURFACE_STEP;
    var cols = Math.round((ext.east - ext.west) / step);
    var rows = Math.round((ext.north - ext.south) / step);
    var n = (cols + 1) * (rows + 1);
    var elev = new Float32Array(n);
    var signed = new Float32Array(n);
    var realm = new Int8Array(n);
    var realmCode = { orro: 1, mere: 2, cinder: 3 };
    var r;
    var c;
    var lon;
    var lat;
    var id;
    for (r = 0; r <= rows; r += 1) {
      lat = ext.south + r * step;
      for (c = 0; c <= cols; c += 1) {
        lon = ext.west + c * step;
        var i = r * (cols + 1) + c;
        var ground = signedLandDesign(lon, lat);
        signed[i] = ground;
        elev[i] = elevationDesign(lon, lat, ground);
        id = realmDesign(lon, lat, ground);
        realm[i] = id ? realmCode[id] : 0;
      }
    }
    surfaceCache = {
      step: step,
      cols: cols,
      rows: rows,
      west: ext.west,
      south: ext.south,
      elev: elev,
      signed: signed,
      realm: realm
    };
    return surfaceCache;
  }

  function marchGrid(values, cols, rows, west, south, step) {
    var segs = [];
    var r;
    var c;
    for (r = 0; r < rows; r += 1) {
      var lat0 = south + r * step;
      var lat1 = lat0 + step;
      for (c = 0; c < cols; c += 1) {
        var lon0 = west + c * step;
        var lon1 = lon0 + step;
        var stride = cols + 1;
        var vSW = values[r * stride + c];
        var vSE = values[r * stride + c + 1];
        var vNW = values[(r + 1) * stride + c];
        var vNE = values[(r + 1) * stride + c + 1];
        var mask = (vSW > 0 ? 1 : 0) | (vSE > 0 ? 2 : 0) | (vNE > 0 ? 4 : 0) | (vNW > 0 ? 8 : 0);
        if (mask === 0 || mask === 15) continue;
        var mid = {
          S: [lerpZero(lon0, lon1, vSW, vSE), lat0],
          N: [lerpZero(lon0, lon1, vNW, vNE), lat1],
          W: [lon0, lerpZero(lat0, lat1, vSW, vNW)],
          E: [lon1, lerpZero(lat0, lat1, vSE, vNE)]
        };
        var center = (vSW + vSE + vNE + vNW) / 4;
        contourPairs(mask, center > 0).forEach(function (pair) {
          segs.push([mid[pair[0]], mid[pair[1]]]);
        });
      }
    }
    return linkSegments(segs).filter(function (ring) {
      return Math.abs(ringArea(ring)) >= 0.55;
    });
  }

  function toWorldRing(ring) {
    var open = ring;
    var closed = open.length > 2 && keyOf(open[0]) === keyOf(open[open.length - 1]);
    if (closed) open = open.slice(0, -1);
    var simplified = rdp(open, 0.09);
    var gap = Math.hypot(
      simplified[0][0] - simplified[simplified.length - 1][0],
      simplified[0][1] - simplified[simplified.length - 1][1]
    );
    // Only join the ends when they already meet. A long join is a chord across the land.
    if ((closed || gap < 0.75) && keyOf(simplified[0]) !== keyOf(simplified[simplified.length - 1])) {
      simplified = simplified.concat([simplified[0]]);
    }
    return roundRing(simplified.map(function (pt) {
      return [toWorldLon(pt[0]), toWorldLat(pt[1])];
    }));
  }

  function chaikin(points, iterations) {
    var pts = points;
    var k;
    var i;
    for (k = 0; k < iterations; k += 1) {
      var out = [pts[0]];
      for (i = 0; i < pts.length - 1; i += 1) {
        var a = pts[i];
        var b = pts[i + 1];
        out.push([a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25]);
        out.push([a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75]);
      }
      out.push(pts[pts.length - 1]);
      pts = out;
    }
    return pts;
  }

  function lineLength(line) {
    var n = 0;
    var i;
    for (i = 1; i < line.length; i += 1) {
      n += Math.hypot(line[i][0] - line[i - 1][0], line[i][1] - line[i - 1][1]);
    }
    return n;
  }

  // Open polylines. Used for borders that end where they meet the sea.
  function linkOpen(segs) {
    var adj = new Map();
    function add(a, b) {
      var k = keyOf(a);
      if (!adj.has(k)) adj.set(k, []);
      adj.get(k).push(b);
    }
    segs.forEach(function (seg) {
      add(seg[0], seg[1]);
      add(seg[1], seg[0]);
    });
    var used = new Set();
    function ek(a, b) {
      var ka = keyOf(a);
      var kb = keyOf(b);
      return ka < kb ? ka + "|" + kb : kb + "|" + ka;
    }
    function walk(start, first) {
      var line = [start, first];
      used.add(ek(start, first));
      var prev = start;
      var cur = first;
      var guard = 0;
      while (guard < segs.length + 2) {
        guard += 1;
        var nbs = adj.get(keyOf(cur)) || [];
        var incoming = [cur[0] - prev[0], cur[1] - prev[1]];
        var best = null;
        var bestScore = -Infinity;
        nbs.forEach(function (nb) {
          if (used.has(ek(cur, nb))) return;
          var vx = nb[0] - cur[0];
          var vy = nb[1] - cur[1];
          var mag = Math.hypot(incoming[0], incoming[1]) * Math.hypot(vx, vy);
          var score = mag === 0 ? 0 : (incoming[0] * vx + incoming[1] * vy) / mag;
          if (score > bestScore) {
            bestScore = score;
            best = nb;
          }
        });
        if (!best) break;
        used.add(ek(cur, best));
        line.push(best);
        prev = cur;
        cur = best;
      }
      return line;
    }
    var lines = [];
    segs.forEach(function (seg) {
      if (used.has(ek(seg[0], seg[1]))) return;
      var n0 = (adj.get(keyOf(seg[0])) || []).length;
      var n1 = (adj.get(keyOf(seg[1])) || []).length;
      var start = n1 < n0 ? seg[1] : seg[0];
      var next = start === seg[0] ? seg[1] : seg[0];
      var line = walk(start, next);
      if (line.length >= 4 && lineLength(line) >= 1.1) lines.push(line);
    });
    return lines;
  }

  function toWorldLine(line) {
    return roundRing(rdp(line, 0.05).map(function (pt) {
      return [toWorldLon(pt[0]), toWorldLat(pt[1])];
    }));
  }

  // Realm borders only where two land realms meet. Cells that touch water are
  // skipped so the political line does not retrace the coastline.
  function politicalBorders(surface) {
    var stride = surface.cols + 1;
    var segs = [];
    var r;
    var c;
    function code(col, row) {
      return surface.realm[row * stride + col];
    }
    for (r = 0; r < surface.rows; r += 1) {
      var lat0 = surface.south + r * surface.step;
      var lat1 = lat0 + surface.step;
      for (c = 0; c < surface.cols; c += 1) {
        var sw = code(c, r);
        var se = code(c + 1, r);
        var nw = code(c, r + 1);
        var ne = code(c + 1, r + 1);
        if (!sw || !se || !nw || !ne) continue;
        if (sw === se && se === ne && ne === nw) continue;
        var lon0 = surface.west + c * surface.step;
        var lon1 = lon0 + surface.step;
        var mids = [];
        if (sw !== se) mids.push([(lon0 + lon1) / 2, lat0]);
        if (nw !== ne) mids.push([(lon0 + lon1) / 2, lat1]);
        if (sw !== nw) mids.push([lon0, (lat0 + lat1) / 2]);
        if (se !== ne) mids.push([lon1, (lat0 + lat1) / 2]);
        if (mids.length >= 2) {
          var cx = 0;
          var cy = 0;
          mids.forEach(function (mid) {
            cx += mid[0];
            cy += mid[1];
          });
          var center = [cx / mids.length, cy / mids.length];
          mids.forEach(function (mid) {
            segs.push([mid, center]);
          });
        }
      }
    }
    return linkOpen(segs).map(toWorldLine);
  }

  function heapPush(heap, pri, idx) {
    heap.push([pri, idx]);
    var i = heap.length - 1;
    while (i > 0) {
      var parent = (i - 1) >> 1;
      if (heap[parent][0] <= heap[i][0]) break;
      var swap = heap[parent];
      heap[parent] = heap[i];
      heap[i] = swap;
      i = parent;
    }
  }

  function heapPop(heap) {
    var top = heap[0];
    var last = heap.pop();
    if (!heap.length) return top;
    heap[0] = last;
    var i = 0;
    while (true) {
      var left = i * 2 + 1;
      var right = left + 1;
      var smallest = i;
      if (left < heap.length && heap[left][0] < heap[smallest][0]) smallest = left;
      if (right < heap.length && heap[right][0] < heap[smallest][0]) smallest = right;
      if (smallest === i) break;
      var swap = heap[smallest];
      heap[smallest] = heap[i];
      heap[i] = swap;
      i = smallest;
    }
    return top;
  }

  // Fill pits on the same elevation grid the relief uses, then point every land
  // cell at its downhill neighbor. A river traced on this grid follows the valleys.
  function buildDrainage(surface) {
    var stride = surface.cols + 1;
    var n = surface.elev.length;
    var filled = new Float32Array(n);
    var seen = new Uint8Array(n);
    var heap = [];
    var dirs = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]];
    var i;
    for (i = 0; i < n; i += 1) {
      if (surface.signed[i] <= 0) {
        filled[i] = surface.elev[i];
        seen[i] = 1;
        heapPush(heap, filled[i], i);
      } else {
        filled[i] = Infinity;
      }
    }
    while (heap.length) {
      var cur = heapPop(heap);
      var ci = cur[1];
      var c = ci % stride;
      var r = (ci / stride) | 0;
      dirs.forEach(function (dir) {
        var nc = c + dir[0];
        var nr = r + dir[1];
        if (nc < 0 || nr < 0 || nc > surface.cols || nr > surface.rows) return;
        var ni = nr * stride + nc;
        if (seen[ni]) return;
        seen[ni] = 1;
        var spill = Math.max(surface.elev[ni], filled[ci] + 0.05);
        filled[ni] = spill;
        heapPush(heap, spill, ni);
      });
    }
    var down = new Int32Array(n);
    down.fill(-1);
    for (i = 0; i < n; i += 1) {
      if (surface.signed[i] <= 0) continue;
      var col = i % stride;
      var row = (i / stride) | 0;
      var best = -1;
      var bestZ = filled[i];
      dirs.forEach(function (dir) {
        var nc = col + dir[0];
        var nr = row + dir[1];
        if (nc < 0 || nr < 0 || nc > surface.cols || nr > surface.rows) return;
        var ni = nr * stride + nc;
        if (filled[ni] < bestZ) {
          bestZ = filled[ni];
          best = ni;
        }
      });
      down[i] = best;
    }
    return down;
  }

  function cellDesign(surface, index) {
    var stride = surface.cols + 1;
    var c = index % stride;
    var r = (index / stride) | 0;
    return [surface.west + c * surface.step, surface.south + r * surface.step];
  }

  // Step downhill on the elevation field, so the line follows the ridges and
  // valleys that the relief paints. A pit spills along the filled drainage.
  function traceRiver(seed, surface, down) {
    var step = 0.1;
    var lon = seed.lon;
    var lat = seed.lat;
    if (signedLandDesign(lon, lat) <= 0) return null;
    var line = [[lon, lat]];
    var prev = null;
    var guard = 0;
    while (guard < 900) {
      guard += 1;
      if (signedLandDesign(lon, lat) <= 0) break;
      var here = elevationDesign(lon, lat);
      var best = null;
      var bestZ = here - 0.5;
      var k;
      for (k = 0; k < 16; k += 1) {
        var ang = (Math.PI * 2 * k) / 16;
        var x = lon + Math.cos(ang) * step;
        var y = lat + Math.sin(ang) * step;
        if (prev) {
          var back = (x - prev[0]) * (x - prev[0]) + (y - prev[1]) * (y - prev[1]);
          if (back < step * step * 0.36) continue;
        }
        var z = elevationDesign(x, y);
        if (z < bestZ) {
          bestZ = z;
          best = [x, y];
        }
      }
      if (!best) {
        var stride = surface.cols + 1;
        var c = Math.round((lon - surface.west) / surface.step);
        var r = Math.round((lat - surface.south) / surface.step);
        if (c < 0 || r < 0 || c > surface.cols || r > surface.rows) break;
        var next = down[r * stride + c];
        if (next < 0) break;
        best = cellDesign(surface, next);
      }
      prev = [lon, lat];
      lon = best[0];
      lat = best[1];
      line.push([lon, lat]);
    }
    if (line.length < 6) return null;
    var end = line[line.length - 1];
    if (signedLandDesign(end[0], end[1]) > 0.15) return null;
    return chaikin(line, 1);
  }

  var geometryCache = null;

  function buildGeometry() {
    if (geometryCache) return geometryCache;
    var surface = warmSurface();
    var landRings = marchGrid(surface.signed, surface.cols, surface.rows, surface.west, surface.south, surface.step);
    var shells = [];
    var holes = [];
    landRings.forEach(function (ring) {
      var probe = interiorProbe(ring);
      var insideLand = signedLandDesign(probe[0], probe[1]) > 0;
      (insideLand ? shells : holes).push(ring);
    });

    function holeInShell(hole, shell) {
      var probe = interiorProbe(hole);
      return pointInRing(probe[0], probe[1], shell);
    }

    var landPolygons = [];
    shells.forEach(function (shell) {
      var polygonHoles = holes.filter(function (hole) {
        return holeInShell(hole, shell);
      });
      landPolygons.push({
        shell: toWorldRing(shell),
        holes: polygonHoles.map(toWorldRing)
      });
    });

    var realmCode = { orro: 1, mere: 2, cinder: 3 };
    var realmFeatures = [];
    Object.keys(REALMS).forEach(function (id) {
      var code = realmCode[id];
      var field = new Float32Array(surface.signed.length);
      var i;
      for (i = 0; i < field.length; i += 1) field[i] = surface.realm[i] === code ? 1 : -1;
      var rings = marchGrid(field, surface.cols, surface.rows, surface.west, surface.south, surface.step);
      rings.forEach(function (ring) {
        var probe = interiorProbe(ring);
        if (realmDesign(probe[0], probe[1]) !== id) return;
        realmFeatures.push({
          realm: id,
          ring: toWorldRing(ring)
        });
      });
    });

    var rivers = [];
    var down = buildDrainage(surface);
    RIVER_SEEDS.forEach(function (seed) {
      var line = traceRiver(seed, surface, down);
      if (!line) return;
      var end = line[line.length - 1];
      rivers.push({
        name: seed.name,
        mouth: waterBodyDesign(end[0], end[1]),
        coordinates: roundRing(line).map(function (pt) {
          return [toWorldLon(pt[0]), toWorldLat(pt[1])];
        })
      });
    });

    var borders = politicalBorders(surface);

    var shorelines = landRings.map(function (ring) {
      var probe = interiorProbe(ring);
      return {
        interior: signedLandDesign(probe[0], probe[1]) > 0 ? "land" : "water",
        coordinates: toWorldRing(ring)
      };
    });

    geometryCache = {
      land: landPolygons,
      realms: realmFeatures,
      borders: borders,
      rivers: rivers,
      shorelines: shorelines
    };
    return geometryCache;
  }

  function featureCollection() {
    var geo = buildGeometry();
    var features = [];
    geo.land.forEach(function (poly, index) {
      features.push({
        type: "Feature",
        properties: {
          kind: "land",
          name: poly.holes.length ? "Cairn" : "island",
          index: index,
          crs: "VAEL:2026"
        },
        geometry: {
          type: "Polygon",
          coordinates: [poly.shell].concat(poly.holes)
        }
      });
    });
    geo.shorelines.forEach(function (line) {
      features.push({
        type: "Feature",
        properties: { kind: "shoreline", interior: line.interior, crs: "VAEL:2026" },
        geometry: { type: "LineString", coordinates: line.coordinates }
      });
    });
    geo.realms.forEach(function (realm) {
      features.push({
        type: "Feature",
        properties: {
          kind: "realm",
          realm: realm.realm,
          name: REALMS[realm.realm].name,
          crs: "VAEL:2026"
        },
        geometry: { type: "Polygon", coordinates: [realm.ring] }
      });
    });
    geo.borders.forEach(function (line, index) {
      features.push({
        type: "Feature",
        properties: { kind: "realm-border", index: index, crs: "VAEL:2026" },
        geometry: { type: "LineString", coordinates: line }
      });
    });
    geo.rivers.forEach(function (river) {
      features.push({
        type: "Feature",
        properties: {
          kind: "river",
          name: river.name,
          mouth: river.mouth,
          crs: "VAEL:2026"
        },
        geometry: { type: "LineString", coordinates: river.coordinates }
      });
    });
    placesWorld().forEach(function (place) {
      features.push({
        type: "Feature",
        properties: {
          kind: place.kind,
          name: place.name,
          realm: place.realm,
          blurb: place.blurb,
          crs: "VAEL:2026"
        },
        geometry: { type: "Point", coordinates: [Math.round(place.lon * 1000) / 1000, Math.round(place.lat * 1000) / 1000] }
      });
    });
    var extent = worldExtent();
    features.push({
      type: "Feature",
      properties: { kind: "mapped-extent", name: "Charted sheet", crs: "VAEL:2026" },
      geometry: {
        type: "Polygon",
        coordinates: [[
          [extent.west, extent.south],
          [extent.east, extent.south],
          [extent.east, extent.north],
          [extent.west, extent.north],
          [extent.west, extent.south]
        ]]
      }
    });
    return {
      type: "FeatureCollection",
      name: "Vael",
      crs_vael: frame().crs,
      notice: "Coordinates are degrees on the Vael sphere (VAEL:2026), not WGS84. Do not plot them as Earth longitude and latitude.",
      features: features
    };
  }

  function frame() {
    var extent = worldExtent();
    return {
      name: "Vael",
      title: "The Crescent Sea",
      generator: GENERATOR,
      seed: SEED,
      continent: "Cairn",
      crs: {
        id: "VAEL:2026",
        type: "geographic",
        datum: "Vael Sphere 2026",
        ellipsoid: { a: RADIUS_M, b: RADIUS_M, unit: "metre" },
        primeMeridian: {
          name: "Cape Orro",
          longitude: 0,
          note: "The meridian through Cape Orro, the western headland of Cairn. Not Greenwich."
        },
        equator: "The Vael equator crosses the Glass Mere.",
        angularUnit: "degree",
        not: "WGS84"
      },
      mappedExtent: extent,
      designShift: { lon: SHIFT.lon, lat: SHIFT.lat, note: "world = design - shift; shift is frozen" },
      display: {
        projection: "plate carree",
        note: "Plate carrée is the Day 10 drawing. It is not the datum. Day 22 replaces it."
      },
      geometry: "2026/10_prompting/vael.geojson"
    };
  }

  function audit() {
    var lines = [];
    var ok = true;
    function fail(msg) {
      ok = false;
      lines.push("FAIL " + msg);
    }
    function okLine(msg) {
      lines.push("ok   " + msg);
    }
    placesWorld().forEach(function (p) {
      var s = sample(p.lon, p.lat);
      if (p.kind === "capital" || p.kind === "town" || p.kind === "cape") {
        if (!s.land) fail(p.name + " is in the water at " + p.lon.toFixed(2) + "," + p.lat.toFixed(2));
        else if (p.realm && s.realm !== p.realm) fail(p.name + " expected " + p.realm + " got " + s.realm);
        else okLine(p.name + " " + Math.round(s.elevationM) + " m " + s.realm);
      } else if (p.kind === "water" || p.kind === "lake") {
        if (s.land) fail(p.name + " label is on land");
        else okLine(p.name + " water " + Math.round(s.elevationM) + " m " + s.water);
      } else if (p.kind === "range") {
        if (s.elevationM < 400) fail(p.name + " is not on high ground (" + Math.round(s.elevationM) + " m)");
        else okLine(p.name + " " + Math.round(s.elevationM) + " m");
      }
    });
    var geo = buildGeometry();
    if (!geo.land.length) fail("no land polygons");
    else okLine("land polygons " + geo.land.length + ", shorelines " + geo.shorelines.length);
    if (!geo.rivers.length) fail("no rivers reached water");
    geo.rivers.forEach(function (river) {
      okLine("river " + river.name + " → " + river.mouth + " (" + river.coordinates.length + " pts)");
    });
    RIVER_SEEDS.forEach(function (seed) {
      var found = geo.rivers.some(function (river) { return river.name === seed.name; });
      if (!found) fail("river dropped: " + seed.name);
    });
    var mere = sample(toWorldLon(GEO.mere.cx), toWorldLat(GEO.mere.cy));
    if (mere.land || mere.water !== "Glass Mere") fail("Glass Mere center is not the mere");
    else okLine("Glass Mere center " + Math.round(mere.elevationM) + " m");
    var orro = placesWorld().filter(function (p) { return p.name === "Orro"; })[0];
    if (Math.abs(orro.lon) > 6) fail("Orro is far from lon 0 (" + orro.lon.toFixed(2) + ")");
    else okLine("Orro longitude " + orro.lon.toFixed(2));
    return { ok: ok, lines: lines };
  }

  function ascii(cols, rows) {
    var ext = worldExtent();
    var out = [];
    var r;
    var c;
    for (r = 0; r < rows; r += 1) {
      var lat = ext.north - ((r + 0.5) / rows) * (ext.north - ext.south);
      var line = "";
      for (c = 0; c < cols; c += 1) {
        var lon = ext.west + ((c + 0.5) / cols) * (ext.east - ext.west);
        var s = sample(lon, lat);
        if (!s.land) {
          if (s.water === "Glass Mere" || s.water === "Lake Merrin") line += "≈";
          else if (s.elevationM < -1800) line += " ";
          else line += "·";
        } else if (s.realm === "cinder") {
          line += s.elevationM > 900 ? "▲" : "○";
        } else if (s.elevationM > 1600) line += "█";
        else if (s.elevationM > 700) line += "▓";
        else if (s.elevationM > 250) line += "▒";
        else line += "░";
      }
      out.push(line + " " + lat.toFixed(0));
    }
    return out.join("\n");
  }

  return {
    SEED: SEED,
    RADIUS_M: RADIUS_M,
    RADIUS_KM: RADIUS_KM,
    REALMS: REALMS,
    PROMPTS: PROMPTS,
    sample: sample,
    elevation: elevation,
    worldExtent: worldExtent,
    places: placesWorld,
    kmPerDegree: kmPerDegree,
    buildGeometry: buildGeometry,
    surface: warmSurface,
    shift: function () { return { lon: SHIFT.lon, lat: SHIFT.lat }; },
    waters: function () {
      return {
        mere: { lon: toWorldLon(GEO.mere.cx), lat: toWorldLat(GEO.mere.cy) },
        lake: { lon: toWorldLon(GEO.lake.cx), lat: toWorldLat(GEO.lake.cy) }
      };
    },
    featureCollection: featureCollection,
    frame: frame,
    audit: audit,
    ascii: ascii
  };
});
