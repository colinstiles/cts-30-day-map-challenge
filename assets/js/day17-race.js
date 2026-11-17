// Day 17 — Sri Chinmoy Self-Transcendence 3100 Mile Race.
// The course is the Jamaica, Queens block bounded by 164th Place,
// the Grand Central Parkway, 168th Street, and 84th Avenue.
// Centerlines are OpenStreetMap. The certified lap is 0.5488 miles.
(function () {
  "use strict";

  var MILES = 3100;
  var DAYS = 52;
  var LAP_MILES = 0.5488;
  var LAPS = 5649;
  var DAY_MS = 5000;
  var RACE_MS = DAYS * DAY_MS;
  var CODA_MS = 10000;
  var HOLD_MS = 4000;
  var CYCLE_MS = RACE_MS + CODA_MS + HOLD_MS;
  var VISUAL_LAPS = DAYS;
  var LAT = 40.7162;
  var LON = -73.7994;
  var M_LAT = 111320;
  var M_LON = 111320 * Math.cos(LAT * Math.PI / 180);

  // Counterclockwise from the southwest corner: 84th, 168th, the parkway, 164th.
  var SIDES = [
    {
      name: "84th Avenue",
      points: [
        [40.715204, -73.801570],
        [40.715216, -73.801485],
        [40.715267, -73.801130],
        [40.715452, -73.799802],
        [40.715497, -73.799593],
        [40.715558, -73.799378],
        [40.715662, -73.799142],
        [40.715672, -73.799121],
        [40.715806, -73.798874],
        [40.715871, -73.798697],
        [40.715938, -73.798477],
        [40.715886, -73.797638],
        [40.715858, -73.797505]
      ]
    },
    {
      name: "168th Street",
      points: [
        [40.715858, -73.797505],
        [40.715941, -73.797535],
        [40.717112, -73.797946],
        [40.717162, -73.797963]
      ]
    },
    {
      name: "Grand Central Pkwy",
      points: [
        [40.717162, -73.797963],
        [40.717135, -73.798044],
        [40.716581, -73.800090],
        [40.716265, -73.801763],
        [40.716253, -73.801837]
      ]
    },
    {
      name: "164th Place",
      points: [
        [40.716253, -73.801837],
        [40.716199, -73.801823],
        [40.716172, -73.801816],
        [40.715326, -73.801601],
        [40.715267, -73.801586],
        [40.715204, -73.801570]
      ]
    }
  ];

  var FREEWAY = [
    [40.71766, -73.79719],
    [40.71741, -73.79806],
    [40.71711, -73.79910],
    [40.71704, -73.79935],
    [40.71697, -73.79959],
    [40.71690, -73.79984],
    [40.71684, -73.80008],
    [40.71678, -73.80035],
    [40.71655, -73.80148],
    [40.71647, -73.80187]
  ];

  var SCHOOL = [
    [40.717074, -73.798052],
    [40.716123, -73.797712],
    [40.716064, -73.797692],
    [40.716017, -73.797698],
    [40.715991, -73.797736],
    [40.715981, -73.797789],
    [40.716011, -73.798336],
    [40.716003, -73.798478],
    [40.715981, -73.798610],
    [40.715908, -73.798843],
    [40.715688, -73.799288],
    [40.715625, -73.799430],
    [40.715572, -73.799640],
    [40.715581, -73.799687],
    [40.715673, -73.799691],
    [40.715954, -73.799911],
    [40.715973, -73.799922],
    [40.716005, -73.799939],
    [40.716361, -73.800116],
    [40.716472, -73.800169],
    [40.716668, -73.799427],
    [40.716741, -73.799147],
    [40.716928, -73.798545],
    [40.717074, -73.798052]
  ];

  var PLAYGROUND = [
    [40.716160, -73.801701],
    [40.716206, -73.801394],
    [40.716472, -73.800169],
    [40.716361, -73.800116],
    [40.716005, -73.799939],
    [40.715973, -73.799922],
    [40.715954, -73.799911],
    [40.715673, -73.799691],
    [40.715581, -73.799687],
    [40.715304, -73.801483],
    [40.715705, -73.801581],
    [40.715915, -73.801637],
    [40.716160, -73.801701]
  ];

  var STUBS = [
    [[40.715204, -73.801570], [40.715024, -73.802780]],
    [[40.715858, -73.797505], [40.715230, -73.797290]]
  ];

  var COURSE = [];
  SIDES.forEach(function (side, s) {
    side.points.forEach(function (p, i) {
      if (s === 0 || i > 0) COURSE.push(p);
    });
  });

  function hav(a, b) {
    var r = 6371000;
    var p1 = a[0] * Math.PI / 180;
    var p2 = b[0] * Math.PI / 180;
    var dp = (b[0] - a[0]) * Math.PI / 180;
    var dl = (b[1] - a[1]) * Math.PI / 180;
    var h = Math.sin(dp / 2) * Math.sin(dp / 2) +
      Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2);
    return 2 * r * Math.asin(Math.min(1, Math.sqrt(h)));
  }

  var CUM = [0];
  for (var i = 1; i < COURSE.length; i += 1) {
    CUM.push(CUM[i - 1] + hav(COURSE[i - 1], COURSE[i]));
  }
  var CLOSE = hav(COURSE[COURSE.length - 1], COURSE[0]);
  var LOOP_M = CUM[CUM.length - 1] + CLOSE;

  function pointAt(frac) {
    var d = ((frac % 1) + 1) % 1 * LOOP_M;
    if (d >= CUM[CUM.length - 1]) {
      var t = CLOSE === 0 ? 0 : (d - CUM[CUM.length - 1]) / CLOSE;
      return [
        COURSE[COURSE.length - 1][0] + (COURSE[0][0] - COURSE[COURSE.length - 1][0]) * t,
        COURSE[COURSE.length - 1][1] + (COURSE[0][1] - COURSE[COURSE.length - 1][1]) * t
      ];
    }
    for (var k = 1; k < CUM.length; k += 1) {
      if (d <= CUM[k]) {
        var span = CUM[k] - CUM[k - 1] || 1;
        var u = (d - CUM[k - 1]) / span;
        return [
          COURSE[k - 1][0] + (COURSE[k][0] - COURSE[k - 1][0]) * u,
          COURSE[k - 1][1] + (COURSE[k][1] - COURSE[k - 1][1]) * u
        ];
      }
    }
    return COURSE[0];
  }

  function raceDay(index) {
    var d = new Date(2026, 7, 30);
    d.setDate(d.getDate() + index);
    return d;
  }

  function dayOfYear(date) {
    var start = new Date(date.getFullYear(), 0, 0);
    return Math.round((date - start) / 86400000);
  }

  function solar(date) {
    var gamma = (2 * Math.PI / 365) * (dayOfYear(date) - 1);
    var eqtime = 229.18 * (
      0.000075 + 0.001868 * Math.cos(gamma) - 0.032077 * Math.sin(gamma) -
      0.014615 * Math.cos(2 * gamma) - 0.040849 * Math.sin(2 * gamma)
    );
    var decl = 0.006918 - 0.399912 * Math.cos(gamma) + 0.070257 * Math.sin(gamma) -
      0.006758 * Math.cos(2 * gamma) + 0.000907 * Math.sin(2 * gamma) -
      0.002697 * Math.cos(3 * gamma) + 0.00148 * Math.sin(3 * gamma);
    var lat = LAT * Math.PI / 180;
    var cosha = Math.cos(90.833 * Math.PI / 180) / (Math.cos(lat) * Math.cos(decl)) -
      Math.tan(lat) * Math.tan(decl);
    cosha = Math.max(-1, Math.min(1, cosha));
    var ha = Math.acos(cosha) * 180 / Math.PI;
    var noon = (720 - 4 * LON - eqtime + (-4) * 60) / 60;
    return {
      decl: decl,
      noon: noon,
      rise: noon - ha / 15,
      set: noon + ha / 15
    };
  }

  var SUN = [];
  for (var d = 0; d < DAYS; d += 1) SUN.push(solar(raceDay(d)));

  function splitOf(index) {
    var s = SUN[index];
    var morning = Math.max(0, s.rise - 6) / 18;
    var evening = Math.max(0, 24 - s.set) / 18;
    var day = Math.max(0, 1 - morning - evening);
    return { morning: morning, day: day, evening: evening };
  }

  function milesSplit(u) {
    var daily = MILES / DAYS;
    var exact = Math.max(0, Math.min(DAYS, u * DAYS));
    var full = Math.floor(exact);
    var part = exact - full;
    var dayM = 0;
    var nightM = 0;
    function add(index, frac) {
      var sp = splitOf(index);
      var left = frac;
      var bits = [
        [sp.morning, true],
        [sp.day, false],
        [sp.evening, true]
      ];
      for (var b = 0; b < bits.length; b += 1) {
        var take = Math.min(left, bits[b][0]);
        if (bits[b][1]) nightM += take * daily;
        else dayM += take * daily;
        left -= take;
      }
    }
    for (var n = 0; n < full; n += 1) add(n, 1);
    if (full < DAYS && part > 0) add(full, part);
    return { day: dayM, night: nightM };
  }

  function altitude(index, hour) {
    var s = SUN[Math.max(0, Math.min(DAYS - 1, index))];
    var ha = (hour - s.noon) * 15 * Math.PI / 180;
    var lat = LAT * Math.PI / 180;
    var alt = Math.asin(
      Math.sin(lat) * Math.sin(s.decl) + Math.cos(lat) * Math.cos(s.decl) * Math.cos(ha)
    );
    return alt * 180 / Math.PI;
  }

  // One pass through the open hours for each of the 52 days.
  var DAY_CYCLES = DAYS;

  function hourFor(u) {
    var local = u >= 1 ? 0.999 : (u * DAY_CYCLES) % 1;
    // Night, a short dawn, daylight, then straight into night. No dusk hold.
    var keys = [[0, 5.75], [0.14, 7.5], [0.72, 15.6], [0.84, 22.2], [1, 24]];
    for (var i = 1; i < keys.length; i += 1) {
      if (local <= keys[i][0]) {
        var span = keys[i][0] - keys[i - 1][0] || 1;
        var t = (local - keys[i - 1][0]) / span;
        return keys[i - 1][1] + (keys[i][1] - keys[i - 1][1]) * t;
      }
    }
    return 24;
  }

  function sample(elapsed) {
    var e = ((elapsed % CYCLE_MS) + CYCLE_MS) % CYCLE_MS;
    if (e < RACE_MS) {
      var u = e / RACE_MS;
      return {
        u: u,
        coda: 0,
        miles: u * MILES,
        day: Math.min(DAYS - 1, Math.floor(u * DAYS)),
        hour: hourFor(u),
        lap: (u * VISUAL_LAPS) % 1
      };
    }
    if (e < RACE_MS + CODA_MS) {
      var c = (e - RACE_MS) / CODA_MS;
      return {
        u: 1,
        coda: c,
        miles: MILES,
        day: DAYS - 1,
        hour: 5.7 + c * 3.2,
        lap: (c * 0.85) % 1
      };
    }
    return {
      u: 1,
      coda: 1,
      miles: MILES,
      day: DAYS - 1,
      hour: 8.9,
      lap: 0.85
    };
  }

  function mix(a, b, t) {
    var out = [0, 0, 0];
    for (var i = 0; i < 3; i += 1) out[i] = Math.round(a[i] + (b[i] - a[i]) * t);
    return out;
  }

  function rgb(c, a) {
    if (a === undefined) return "rgb(" + c[0] + "," + c[1] + "," + c[2] + ")";
    return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a + ")";
  }

  function smooth(t) {
    var x = Math.max(0, Math.min(1, t));
    return x * x * (3 - 2 * x);
  }

  // Drawn block. Night is a dark field. Daylight is a white page around a dark map.
  function palette(alt, hour, coda) {
    var night = {
      top: [7, 9, 14],
      bottom: [12, 14, 20],
      ground: [17, 19, 24],
      block: [26, 29, 36],
      street: [78, 84, 96],
      casing: [20, 22, 28],
      building: [34, 38, 48],
      park: [22, 34, 32],
      parkway: [12, 14, 18],
      ink: [244, 220, 160],
      halo: [10, 12, 16]
    };
    var dawn = { top: [232, 228, 220], bottom: [244, 240, 232] };
    var day = { top: [255, 255, 255], bottom: [255, 255, 255] };
    var skyT = alt < -7 ? 0 : alt < 12 ? smooth((alt + 7) / 19) : 1;
    var lit = smooth(Math.max(0, Math.min(1, (alt + 1) / 12)));
    var dayTop = hour < 12 && skyT < 0.9 ? dawn.top : day.top;
    var dayBottom = hour < 12 && skyT < 0.9 ? dawn.bottom : day.bottom;
    var top = mix(night.top, dayTop, skyT);
    var bottom = mix(night.bottom, dayBottom, skyT);
    if (coda > 0) {
      top = mix(top, day.top, smooth(coda));
      bottom = mix(bottom, day.bottom, smooth(coda));
      lit = Math.max(lit, smooth(coda));
    }
    var onPaper = (bottom[0] + bottom[1] + bottom[2]) / 3 > 170;
    return {
      top: top,
      bottom: bottom,
      ground: mix(night.ground, [32, 34, 40], lit * 0.4),
      block: mix(night.block, [44, 48, 56], lit * 0.35),
      street: mix(night.street, [214, 210, 200], lit),
      casing: night.casing,
      building: mix(night.building, [52, 56, 64], lit * 0.4),
      park: mix(night.park, [28, 48, 42], lit * 0.55),
      parkway: mix(night.parkway, [22, 26, 32], lit * 0.35),
      ink: night.ink,
      halo: night.halo,
      onPaper: onPaper
    };
  }

  function clock(hour) {
    var h24 = ((hour % 24) + 24) % 24;
    var h = Math.floor(h24);
    var m = Math.floor((h24 - h) * 60);
    var suffix = h >= 12 ? "p.m." : "a.m.";
    var h12 = h % 12;
    if (h12 === 0) h12 = 12;
    return h12 + ":" + String(m).padStart(2, "0") + " " + suffix;
  }

  function monthDay(index) {
    var date = raceDay(index);
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return months[date.getMonth()] + " " + date.getDate();
  }

  function phaseName(state, alt) {
    if (state.coda > 0.42) return "Into the light";
    if (state.coda > 0) return "The finish";
    if (alt < -2) return "Night · course open";
    if (state.hour < 12 && alt < 6) return "Dawn";
    return "Daylight";
  }

  var canvas;
  var ctx;
  var view = { w: 1, h: 1, dpr: 1 };
  var map = null;
  var playing = true;
  var parentVisible = true;
  var elapsed = 0;
  var last = 0;
  var speed = 1;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var embed = document.body.classList.contains("d17-embed");
  var scrubbing = false;

  var els = {};

  function resize() {
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    var w = window.innerWidth;
    var h = window.innerHeight;
    canvas.width = Math.max(1, Math.round(w * dpr));
    canvas.height = Math.max(1, Math.round(h * dpr));
    view = { w: w, h: h, dpr: dpr };
    var cx = w * 0.6;
    var cy = h * 0.48;
    var radius = Math.max(78, Math.min(w * 0.34, h * 0.4));
    if (embed) {
      cx = w * 0.58;
      cy = h * 0.58;
      radius = Math.max(70, Math.min(w * 0.34, h * 0.36));
    } else if (w > 900) {
      cx = Math.max(w * 0.62, 480);
      radius = Math.min(radius, h * 0.38, (w - 440) * 0.4);
    }
    map = fit(cx, cy, radius);
  }

  function fit(cx, cy, radius) {
    var minX = Infinity;
    var maxX = -Infinity;
    var minY = Infinity;
    var maxY = -Infinity;
    function include(pt) {
      var x = pt[1] * M_LON;
      var y = pt[0] * M_LAT;
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    COURSE.forEach(include);
    FREEWAY.forEach(include);
    var bw = maxX - minX || 1;
    var bh = maxY - minY || 1;
    var scale = Math.min((radius * 1.28) / bw, (radius * 1.05) / bh);
    return {
      cx: cx,
      cy: cy + radius * 0.02,
      radius: radius,
      scale: scale,
      ox: (minX + maxX) / 2,
      oy: (minY + maxY) / 2
    };
  }

  function xy(pt) {
    return {
      x: map.cx + (pt[1] * M_LON - map.ox) * map.scale,
      y: map.cy - (pt[0] * M_LAT - map.oy) * map.scale
    };
  }

  function trace(points, close) {
    if (!points.length) return;
    var p0 = xy(points[0]);
    ctx.moveTo(p0.x, p0.y);
    for (var i = 1; i < points.length; i += 1) {
      var p = xy(points[i]);
      ctx.lineTo(p.x, p.y);
    }
    if (close) ctx.closePath();
  }

  function strokePath(points, close, width, color) {
    ctx.beginPath();
    trace(points, close);
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.stroke();
  }

  function fillPath(points, color) {
    ctx.beginPath();
    trace(points, true);
    ctx.fillStyle = color;
    ctx.fill();
  }

  function drawSky(pal) {
    var g = ctx.createLinearGradient(0, 0, 0, view.h);
    g.addColorStop(0, rgb(pal.top));
    g.addColorStop(1, rgb(pal.bottom));
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, view.w, view.h);
  }

  function drawMap(pal, state) {
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(map.cx, map.cy, map.radius * 0.92, map.radius * 0.92, 0, 0, Math.PI * 2);
    ctx.fillStyle = rgb(pal.ground);
    ctx.fill();
    ctx.clip();
    strokePath(FREEWAY, false, Math.max(8, 28 * map.scale), rgb(pal.parkway));
    strokePath(FREEWAY, false, Math.max(1.5, 5 * map.scale), rgb(mix(pal.parkway, pal.street, 0.4)));
    if (state.hour >= 20 || state.hour < 7) drawTraffic(state);
    STUBS.forEach(function (stub) {
      strokePath(stub, false, Math.max(2.5, 8 * map.scale), rgb(pal.street));
    });
    fillPath(COURSE, rgb(pal.block));
    fillPath(PLAYGROUND, rgb(pal.park));
    fillPath(SCHOOL, rgb(pal.building));
    SIDES.forEach(function (side) {
      strokePath(side.points, false, Math.max(3, 10 * map.scale), rgb(pal.casing));
      strokePath(side.points, false, Math.max(1.5, 5.5 * map.scale), rgb(pal.street));
    });
    ctx.restore();
  }

  function drawTraffic(state) {
    var speed = state.u * 4 + state.coda;
    for (var n = 0; n < 7; n += 1) {
      var f = (speed * 0.15 + n / 7) % 1;
      var idx = f * (FREEWAY.length - 1);
      var i0 = Math.floor(idx);
      var t = idx - i0;
      var a = FREEWAY[i0];
      var b = FREEWAY[Math.min(FREEWAY.length - 1, i0 + 1)];
      var p = xy([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
      ctx.fillStyle = n % 2 === 0 ? "rgba(255, 214, 140, 0.85)" : "rgba(210, 220, 255, 0.55)";
      ctx.beginPath();
      ctx.arc(p.x, p.y, 1.6, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function drawCourse(state) {
    var laps = Math.max(state.miles / LAP_MILES, state.coda * LAPS);
    var t = Math.max(0, Math.min(1, laps / LAPS));
    var width = (embed ? 1.2 : 1.5) + t * (embed ? 7 : 11);
    var gold = [255, 206, 110];
    strokePath(COURSE, true, width + 4 + t * 8, rgb(gold, 0.06 + 0.34 * t));
    strokePath(COURSE, true, width, rgb(gold, 0.18 + 0.82 * t));
    var steps = 16;
    for (var s = 1; s <= steps; s += 1) {
      var f = state.lap - (s / steps) * 0.06;
      var a = pointAt(f);
      var b = pointAt(f + 0.01);
      ctx.beginPath();
      var pa = xy(a);
      var pb = xy(b);
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.strokeStyle = rgb([255, 236, 196], (1 - s / steps) * (0.35 + 0.65 * t));
      ctx.lineWidth = width;
      ctx.stroke();
    }
    var runner = xy(pointAt(state.lap));
    var rad = (embed ? 2.6 : 3.2) + t * (embed ? 2.2 : 3);
    ctx.beginPath();
    ctx.fillStyle = rgb(gold, 0.2 + 0.45 * t);
    ctx.arc(runner.x, runner.y, rad * 2.6, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.fillStyle = rgb([255, 244, 214]);
    ctx.arc(runner.x, runner.y, rad, 0, Math.PI * 2);
    ctx.fill();
  }

  function drawRing(state, pal) {
    var cx = map.cx;
    var cy = map.cy;
    var r = map.radius;
    var gap = 0.012;
    var span = (Math.PI * 2) / DAYS - gap;
    ctx.lineCap = "butt";
    ctx.lineWidth = embed ? 7 : 11;
    ctx.beginPath();
    ctx.strokeStyle = pal.onPaper ? "rgba(36, 32, 28, 0.22)" : rgb(pal.ink, 0.18);
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();

    var dayMark = pal.onPaper ? [138, 84, 12] : [228, 196, 106];
    var nightMark = pal.onPaper ? [36, 64, 128] : [140, 164, 214];
    var progressDays = state.u * DAYS;
    for (var i = 0; i < DAYS; i += 1) {
      var filled = Math.max(0, Math.min(1, progressDays - i));
      if (filled <= 0) continue;
      var sp = splitOf(i);
      var parts = [
        [sp.morning, nightMark],
        [sp.day, dayMark],
        [sp.evening, nightMark]
      ];
      var start = -Math.PI / 2 + i * (span + gap);
      var acc = 0;
      for (var p = 0; p < parts.length; p += 1) {
        var frac = parts[p][0];
        var a0 = start + acc * span;
        var a1 = start + Math.min(filled, acc + frac) * span;
        if (a1 > a0 + 0.0008) {
          ctx.beginPath();
          ctx.strokeStyle = rgb(parts[p][1], pal.onPaper ? 1 : 0.55 + 0.45 * state.u);
          ctx.arc(cx, cy, r, a0, a1);
          ctx.stroke();
        }
        acc += frac;
        if (acc >= filled) break;
      }
    }
    drawMileCounter(state, pal);
  }

  function drawMileCounter(state, pal) {
    var ang = -Math.PI / 2 + state.u * Math.PI * 2;
    var ringX = map.cx + Math.cos(ang) * map.radius;
    var ringY = map.cy + Math.sin(ang) * map.radius;
    var labelR = map.radius + (embed ? 22 : 32);
    var x = map.cx + Math.cos(ang) * labelR;
    var y = map.cy + Math.sin(ang) * labelR;
    var miles = state.miles >= MILES - 0.5 ? MILES : Math.round(state.miles);
    var text = miles.toLocaleString("en-US") + " mi";
    ctx.font = "900 " + (embed ? 12 : 15) + "px Lato, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    var w = ctx.measureText(text).width + (embed ? 14 : 18);
    var h = embed ? 20 : 26;
    var edge = 8;
    var floor = embed ? edge : 84;
    x = Math.max(w / 2 + edge, Math.min(view.w - w / 2 - edge, x));
    y = Math.max(h / 2 + edge, Math.min(view.h - floor - h / 2, y));

    var mark = pal.onPaper ? "rgba(122, 74, 12, 0.95)" : "rgba(255, 206, 110, 0.95)";
    ctx.beginPath();
    ctx.fillStyle = mark;
    ctx.arc(ringX, ringY, embed ? 3.2 : 4.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.strokeStyle = mark;
    ctx.lineWidth = 1.25;
    ctx.moveTo(ringX, ringY);
    ctx.lineTo(x, y);
    ctx.stroke();

    var r = h / 2;
    ctx.beginPath();
    ctx.moveTo(x - w / 2 + r, y - h / 2);
    ctx.arcTo(x + w / 2, y - h / 2, x + w / 2, y + h / 2, r);
    ctx.arcTo(x + w / 2, y + h / 2, x - w / 2, y + h / 2, r);
    ctx.arcTo(x - w / 2, y + h / 2, x - w / 2, y - h / 2, r);
    ctx.arcTo(x - w / 2, y - h / 2, x + w / 2, y - h / 2, r);
    ctx.closePath();
    ctx.fillStyle = "rgba(10, 12, 16, 0.92)";
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(255, 206, 110, 0.85)";
    ctx.stroke();
    ctx.fillStyle = "#f4efe4";
    ctx.fillText(text, x, y);
  }

  var STREET_FONT = "\"Barlow Condensed\", Lato, sans-serif";

  function trackedText(text, x, y, tracking, draw) {
    var chars = text.split("");
    var widths = chars.map(function (ch) { return ctx.measureText(ch).width; });
    var total = 0;
    widths.forEach(function (w) { total += w; });
    total += tracking * Math.max(0, chars.length - 1);
    var cursor = x - total / 2;
    ctx.textAlign = "left";
    chars.forEach(function (ch, i) {
      draw(ch, cursor, y);
      cursor += widths[i] + tracking;
    });
  }

  function drawStreetNames(pal) {
    var names = ["84TH AVENUE", "168TH STREET", "GRAND CENTRAL", "164TH PLACE"];
    ctx.save();
    ctx.font = "600 " + (embed ? 11 : 15) + "px " + STREET_FONT;
    ctx.textBaseline = "middle";
    SIDES.forEach(function (side, i) {
      var pts = side.points;
      var mid = pts[Math.floor(pts.length / 2)];
      var a = xy(pts[0]);
      var b = xy(pts[pts.length - 1]);
      var p = xy(mid);
      var ang = Math.atan2(b.y - a.y, b.x - a.x);
      if (ang > Math.PI / 2 || ang < -Math.PI / 2) ang += Math.PI;
      var nx = Math.cos(ang + Math.PI / 2);
      var ny = Math.sin(ang + Math.PI / 2);
      if ((p.x - map.cx) * nx + (p.y - map.cy) * ny < 0) {
        nx *= -1;
        ny *= -1;
      }
      var gap = embed ? 16 : 22;
      ctx.save();
      ctx.translate(p.x + nx * gap, p.y + ny * gap);
      ctx.rotate(ang);
      ctx.lineWidth = 3;
      ctx.strokeStyle = rgb(pal.halo, 0.9);
      ctx.lineJoin = "round";
      trackedText(names[i], 0, 0, embed ? 0.8 : 1.3, function (ch, x, y) {
        ctx.strokeText(ch, x, y);
      });
      ctx.fillStyle = rgb(pal.ink);
      trackedText(names[i], 0, 0, embed ? 0.8 : 1.3, function (ch, x, y) {
        ctx.fillText(ch, x, y);
      });
      ctx.restore();
    });
    if (map.radius > 140) {
      var school = xy([40.71635, -73.79915]);
      ctx.font = "500 " + (embed ? 10 : 12) + "px " + STREET_FONT;
      ctx.textAlign = "center";
      ctx.strokeStyle = rgb(pal.halo, 0.88);
      ctx.lineWidth = 3;
      ctx.strokeText("EDISON H.S.", school.x, school.y);
      ctx.fillStyle = rgb(pal.ink, 0.9);
      ctx.fillText("EDISON H.S.", school.x, school.y);
    }
    ctx.restore();
  }

  function drawScale(pal) {
    var meters = 100;
    var px = meters * map.scale;
    var x = map.cx - map.radius * 0.15;
    var y = map.cy + map.radius * 0.62;
    ctx.strokeStyle = rgb(pal.ink);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + px, y);
    ctx.moveTo(x, y - 4);
    ctx.lineTo(x, y + 4);
    ctx.moveTo(x + px, y - 4);
    ctx.lineTo(x + px, y + 4);
    ctx.stroke();
    ctx.font = "600 10px Lato, sans-serif";
    ctx.textAlign = "left";
    ctx.fillStyle = rgb(pal.ink);
    ctx.fillText("100 m", x, y - 8);
    if (!embed) {
      ctx.font = "600 10px Lato, sans-serif";
      ctx.fillText(LAPS.toLocaleString("en-US") + " laps · " + LAP_MILES + " mi", x, y + 16);
    }
  }

  function draw() {
    var state = reduceMotion && !scrubbing && elapsed === 0
      ? { u: 1, coda: 1, miles: MILES, day: DAYS - 1, hour: 8.9, lap: 0.85 }
      : sample(elapsed);
    var alt = state.coda > 0 ? altitude(DAYS - 1, state.hour) : altitude(state.day, state.hour);
    var pal = palette(alt, state.hour, state.coda);
    ctx.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
    drawSky(pal);
    drawMap(pal, state);
    drawCourse(state);
    drawStreetNames(pal);
    drawRing(state, pal);
    if (!embed) drawScale(pal);
    document.body.style.background = rgb(pal.bottom);
    paintReadout(state, alt);
  }

  function paintReadout(state, alt) {
    var miles = state.miles >= MILES - 0.5 ? MILES : Math.round(state.miles);
    els.miles.textContent = miles.toLocaleString("en-US");
    var when = state.coda > 0
      ? "Day 52 · " + monthDay(DAYS - 1) + " · finish"
      : "Day " + (state.day + 1) + " of 52 · " + monthDay(state.day);
    els.when.textContent = when + " · " + clock(state.hour);
    els.phase.textContent = phaseName(state, alt);
    var split = milesSplit(state.u);
    els.dayMi.textContent = "Daylight " + Math.round(split.day).toLocaleString("en-US");
    els.nightMi.textContent = "Night " + Math.round(split.night).toLocaleString("en-US");
    if (!scrubbing && els.slider) els.slider.value = String(Math.round(timelineFraction() * 1000));
  }

  function timelineFraction() {
    return Math.max(0, Math.min(1, elapsed / (RACE_MS + CODA_MS)));
  }

  function setPlaying(next) {
    playing = next;
    if (els.play) {
      els.play.setAttribute("aria-pressed", playing ? "true" : "false");
      els.play.textContent = playing ? "Pause" : "Play";
    }
    last = 0;
  }

  function tick(now) {
    if (playing && (!embed || parentVisible) && !document.hidden) {
      if (!last) last = now;
      var delta = Math.min(80, now - last);
      last = now;
      elapsed += delta * speed;
      if (elapsed >= CYCLE_MS) elapsed = 0;
    } else {
      last = now;
    }
    draw();
    window.requestAnimationFrame(tick);
  }

  function bind() {
    canvas = document.getElementById("d17-canvas");
    ctx = canvas.getContext("2d");
    els.miles = document.getElementById("d17-miles");
    els.when = document.getElementById("d17-when");
    els.phase = document.getElementById("d17-phase");
    els.dayMi = document.getElementById("d17-day-mi");
    els.nightMi = document.getElementById("d17-night-mi");
    els.play = document.getElementById("d17-play");
    els.slider = document.getElementById("d17-slider");
    els.speed = document.getElementById("d17-speed");
    els.speedLabel = document.getElementById("d17-speed-label");

    if (embed) {
      var ui = document.querySelector(".d17-ui");
      if (ui) ui.setAttribute("aria-hidden", "true");
    }

    if (reduceMotion) {
      playing = false;
      elapsed = RACE_MS + CODA_MS;
    }

    if (els.play) {
      els.play.addEventListener("click", function () {
        reduceMotion = false;
        setPlaying(!playing);
      });
    }
    if (els.slider) {
      els.slider.addEventListener("input", function () {
        scrubbing = true;
        reduceMotion = false;
        setPlaying(false);
        elapsed = (Number(els.slider.value) / 1000) * (RACE_MS + CODA_MS);
        draw();
        scrubbing = false;
      });
    }
    function setSpeed(percent) {
      speed = Math.max(0.25, Math.min(4, Number(percent) / 100));
      if (els.speed) els.speed.value = String(Math.round(speed * 100));
      if (els.speedLabel) {
        var shown = speed % 1 === 0 ? String(speed) : speed.toFixed(2).replace(/0$/, "");
        els.speedLabel.textContent = shown + "×";
      }
    }
    if (els.speed) {
      setSpeed(els.speed.value);
      els.speed.addEventListener("input", function () {
        setSpeed(els.speed.value);
      });
    }

    window.addEventListener("message", function (event) {
      if (!event.data || event.data.type !== "cts-embed-visible") return;
      parentVisible = Boolean(event.data.visible);
    });
    window.addEventListener("resize", function () {
      resize();
      draw();
    });

    resize();
    setPlaying(playing);
    window.requestAnimationFrame(tick);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
