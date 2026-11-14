/* Day 14 — Borgesian map.
   The photograph is the map. It is drawn at 1:1: one centimeter of sidewalk
   is one centimeter on the screen, after the scale bar is matched to a ruler.
   There is no zoom. */
(function () {
  "use strict";

  // Concrete between the grass edges. 4 feet is a usual residential sidewalk.
  // The page uses this unless the JPEG records a plausible focus distance.
  var SIDEWALK_WIDTH_M = 1.2192;

  // Image fractions (0–1) of the displayed photograph.
  // The scale line runs grass edge to grass edge through the subject leaf.
  var SCALE_LINE = { y: 0.52, x0: 0.08, x1: 0.95 };
  // Subject leaf: on the measured line, between the 30 cm and 40 cm ticks.
  var LEAF_CM = 35;
  var LEAF = {
    x: SCALE_LINE.x0 + (LEAF_CM / 100) / (SIDEWALK_WIDTH_M / (SCALE_LINE.x1 - SCALE_LINE.x0)),
    y: SCALE_LINE.y
  };

  var STORAGE_KEY = "cts-day14-px-per-cm";

  var stage = document.getElementById("d14-stage");
  var sheet = document.getElementById("d14-sheet");
  var photo = document.getElementById("d14-photo");
  var grid = document.getElementById("d14-grid");
  var leafMark = document.getElementById("d14-leaf");
  var leafHit = document.getElementById("d14-leaf-hit");
  var leafPop = document.getElementById("d14-leaf-pop");
  var cmHost = document.getElementById("d14-cm");
  var whenEl = document.getElementById("d14-when");
  var widthTag = document.getElementById("d14-width");
  var probe = document.getElementById("d14-probe");
  var barLine = document.getElementById("d14-bar-line");
  var barLabel = document.getElementById("d14-bar-label");
  var note = document.getElementById("d14-note");
  var embed = document.body.classList.contains("d14-embed");

  var groundWidthM = null;
  var method = "sidewalk";
  var pxPerCmOverride = readStoredPxPerCm();
  var anchor = { u: LEAF.x, v: LEAF.y };
  var origin = { x: 0, y: 0 };
  var drag = null;

  leafMark.style.left = (LEAF.x * 100) + "%";
  leafMark.style.top = (LEAF.y * 100) + "%";
  widthTag.style.left = (SCALE_LINE.x1 * 100) + "%";
  widthTag.style.top = (SCALE_LINE.y * 100) + "%";
  widthTag.style.transform = "translate(-110%, -1.5em)";

  function readStoredPxPerCm() {
    try {
      var stored = window.localStorage.getItem(STORAGE_KEY);
      var value = stored ? Number(stored) : NaN;
      if (value > 10 && value < 200) return value;
    } catch (err) {
      return null;
    }
    return null;
  }

  function cssPxPerCm() {
    var width = probe.getBoundingClientRect().width;
    if (width > 0) return width / 10;
    return 96 / 2.54;
  }

  function pxPerCm() {
    return pxPerCmOverride || cssPxPerCm();
  }

  function barCentimeters() {
    if (embed || stage.clientWidth < 560) return 5;
    return 10;
  }

  function formatLength(meters) {
    var inches = meters / 0.0254;
    var feet = Math.floor(inches / 12);
    var inch = Math.round(inches - feet * 12);
    if (inch === 12) {
      feet += 1;
      inch = 0;
    }
    if (inch === 0) return feet + " ft";
    return feet + " ft " + inch + " in";
  }

  function concreteWidthM() {
    return groundWidthM * (SCALE_LINE.x1 - SCALE_LINE.x0);
  }

  function writeNote() {
    var sentence;
    if (method === "focus") {
      sentence = "Scale 1:1 from the camera focus distance. The frame is " +
        formatLength(groundWidthM) + " across, and the concrete between the grass is " +
        formatLength(concreteWidthM()) + ".";
    } else {
      sentence = "Scale 1:1, taking the concrete between the grass edges as 4 ft.";
    }
    note.textContent = sentence +
      " Match the bar to a ruler. Drag to move across the sidewalk. " +
      "The camera is not straight down, so the centimeter grid holds along the measured line and drifts toward the edges of the frame.";
  }

  function layoutSheet() {
    var displayWidth = groundWidthM * pxPerCm() * 100;
    var displayHeight = displayWidth * (photo.naturalHeight / photo.naturalWidth);
    sheet.style.width = displayWidth + "px";
    sheet.style.height = displayHeight + "px";
    barLine.style.width = (barCentimeters() * pxPerCm()) + "px";
    barLabel.textContent = barCentimeters() + " cm · 1:1";
    widthTag.textContent = formatLength(concreteWidthM());

    var stageW = stage.clientWidth;
    var stageH = stage.clientHeight;
    origin.x = stageW / 2 - anchor.u * displayWidth;
    origin.y = stageH / 2 - anchor.v * displayHeight;
    clamp(displayWidth, displayHeight, stageW, stageH);
    syncView();
  }

  function syncView() {
    sheet.style.transform = "translate(" + origin.x + "px, " + origin.y + "px)";
    placeCmLabels();
  }

  function placeCmLabels() {
    if (!cmHost || !groundWidthM || !photo.naturalWidth) return;
    var mPerPx = groundWidthM / photo.naturalWidth;
    var sheetW = sheet.offsetWidth;
    var x0 = SCALE_LINE.x0 * photo.naturalWidth;
    var reserve = whenEl.textContent ? 176 : 16;
    cmHost.replaceChildren();
    var i;
    var cm;
    var imgX;
    var screenX;
    var label;
    for (i = 0; i <= 14; i += 1) {
      cm = i * 10;
      imgX = x0 + (cm / 100) / mPerPx;
      screenX = origin.x + (imgX / photo.naturalWidth) * sheetW;
      if (screenX < 18 || screenX > stage.clientWidth - reserve) continue;
      label = document.createElement("span");
      label.style.left = screenX + "px";
      label.style.transform = "translateX(-50%)";
      label.textContent = cm === 0 ? "0 cm" : String(cm);
      cmHost.appendChild(label);
    }
  }

  function clamp(sheetW, sheetH, stageW, stageH) {
    if (sheetW <= stageW) origin.x = (stageW - sheetW) / 2;
    else origin.x = Math.min(0, Math.max(stageW - sheetW, origin.x));
    if (sheetH <= stageH) origin.y = (stageH - sheetH) / 2;
    else origin.y = Math.min(0, Math.max(stageH - sheetH, origin.y));
  }

  function rememberAnchor() {
    var sheetW = sheet.offsetWidth;
    var sheetH = sheet.offsetHeight;
    if (!sheetW || !sheetH) return;
    anchor.u = (stage.clientWidth / 2 - origin.x) / sheetW;
    anchor.v = (stage.clientHeight / 2 - origin.y) / sheetH;
  }

  function drawGrid() {
    var iw = photo.naturalWidth;
    var ih = photo.naturalHeight;
    var mPerPx = groundWidthM / iw;
    var cellPx = 0.1 / mPerPx;
    var x0 = SCALE_LINE.x0 * iw;
    var yLine = SCALE_LINE.y * ih;
    var x1 = SCALE_LINE.x1 * iw;
    var ns = "http://www.w3.org/2000/svg";

    grid.setAttribute("viewBox", "0 0 " + iw + " " + ih);
    grid.replaceChildren();

    function addLine(x1p, y1p, x2p, y2p, weight, color) {
      var casing = document.createElementNS(ns, "line");
      var line = document.createElementNS(ns, "line");
      [casing, line].forEach(function (node) {
        node.setAttribute("x1", x1p);
        node.setAttribute("y1", y1p);
        node.setAttribute("x2", x2p);
        node.setAttribute("y2", y2p);
        node.setAttribute("vector-effect", "non-scaling-stroke");
        node.setAttribute("stroke-linecap", "square");
      });
      casing.setAttribute("stroke", "#241f1a");
      casing.setAttribute("stroke-opacity", "0.55");
      casing.setAttribute("stroke-width", weight + 2.5);
      line.setAttribute("stroke", color);
      line.setAttribute("stroke-opacity", "0.92");
      line.setAttribute("stroke-width", weight);
      grid.appendChild(casing);
      grid.appendChild(line);
    }

    var i;
    var x;
    for (i = 0, x = x0; x < x1 + 1; i += 1, x = x0 + i * cellPx) {
      addLine(x, 0, x, ih, i % 5 === 0 ? 2.25 : 1.15, "#f4f1ea");
    }
    for (i = 0; i * cellPx < ih; i += 1) {
      addLine(x0, i * cellPx, x1, i * cellPx, i % 5 === 0 ? 2.25 : 1.15, "#f4f1ea");
    }
    addLine(x0, yLine, x1, yLine, 2.5, "#e4c56a");
  }

  function applyScale() {
    var frac = SCALE_LINE.x1 - SCALE_LINE.x0;
    groundWidthM = SIDEWALK_WIDTH_M / frac;
    method = "sidewalk";
    drawGrid();
    writeNote();
    layoutSheet();
  }

  function useFocusDistance(exif) {
    var portrait = photo.naturalHeight > photo.naturalWidth;
    var filmMm = portrait ? 24 : 36;
    var widthM = exif.subjectM * filmMm / exif.focal35;
    if (!(widthM >= 0.9 && widthM <= 2.2)) return false;
    groundWidthM = widthM;
    method = "focus";
    drawGrid();
    writeNote();
    layoutSheet();
    return true;
  }

  function setLeafOpen(open) {
    leafPop.hidden = !open;
    leafHit.setAttribute("aria-expanded", open ? "true" : "false");
    leafHit.classList.toggle("is-open", open);
  }

  leafHit.addEventListener("click", function (event) {
    event.stopPropagation();
    setLeafOpen(leafPop.hidden);
  });

  function onPointerDown(event) {
    if (event.button !== undefined && event.button !== 0) return;
    if (event.target.closest && event.target.closest("#d14-leaf-hit, .d14-leaf-card")) return;
    setLeafOpen(false);
    drag = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      ox: origin.x,
      oy: origin.y
    };
    stage.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event) {
    if (!drag || event.pointerId !== drag.id) return;
    origin.x = drag.ox + (event.clientX - drag.x);
    origin.y = drag.oy + (event.clientY - drag.y);
    clamp(sheet.offsetWidth, sheet.offsetHeight, stage.clientWidth, stage.clientHeight);
    syncView();
  }

  function onPointerUp(event) {
    if (!drag || event.pointerId !== drag.id) return;
    drag = null;
    rememberAnchor();
  }

  stage.addEventListener("pointerdown", onPointerDown);
  stage.addEventListener("pointermove", onPointerMove);
  stage.addEventListener("pointerup", onPointerUp);
  stage.addEventListener("pointercancel", onPointerUp);

  stage.addEventListener("wheel", function (event) {
    event.preventDefault();
    var dx = event.shiftKey ? event.deltaY : event.deltaX;
    var dy = event.shiftKey ? 0 : event.deltaY;
    origin.x -= dx;
    origin.y -= dy;
    clamp(sheet.offsetWidth, sheet.offsetHeight, stage.clientWidth, stage.clientHeight);
    syncView();
    rememberAnchor();
  }, { passive: false });

  stage.addEventListener("dblclick", function () {
    anchor.u = LEAF.x;
    anchor.v = LEAF.y;
    layoutSheet();
  });

  window.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      setLeafOpen(false);
      return;
    }
    if (event.target && event.target.closest && event.target.closest("button, a")) return;
    var step = event.shiftKey ? 80 : 40;
    var moved = true;
    if (event.key === "ArrowLeft") origin.x += step;
    else if (event.key === "ArrowRight") origin.x -= step;
    else if (event.key === "ArrowUp") origin.y += step;
    else if (event.key === "ArrowDown") origin.y -= step;
    else moved = false;
    if (!moved) return;
    event.preventDefault();
    clamp(sheet.offsetWidth, sheet.offsetHeight, stage.clientWidth, stage.clientHeight);
    syncView();
    rememberAnchor();
  });

  window.addEventListener("resize", function () {
    if (groundWidthM) layoutSheet();
  });

  function nudge(factor) {
    pxPerCmOverride = pxPerCm() * factor;
    try {
      window.localStorage.setItem(STORAGE_KEY, String(pxPerCmOverride));
    } catch (err) {
      /* the bar still updates for this visit */
    }
    layoutSheet();
  }

  document.getElementById("d14-minus").addEventListener("click", function () {
    nudge(1 / 1.02);
  });
  document.getElementById("d14-plus").addEventListener("click", function () {
    nudge(1.02);
  });
  document.getElementById("d14-reset").addEventListener("click", function () {
    pxPerCmOverride = null;
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch (err) {
      /* ignore */
    }
    layoutSheet();
  });

  function readExif(buffer) {
    try {
      return readExifUnsafe(buffer);
    } catch (err) {
      return null;
    }
  }

  function readExifUnsafe(buffer) {
    var view = new DataView(buffer);
    if (view.byteLength < 16 || view.getUint16(0) !== 0xffd8) return null;
    var offset = 2;
    while (offset + 4 < view.byteLength) {
      var marker = view.getUint16(offset);
      if (marker === 0xffda || marker === 0xffd9) break;
      var size = view.getUint16(offset + 2);
      if (size < 2) break;
      if (marker === 0xffe1 && size > 14 && view.getUint32(offset + 4) === 0x45786966) {
        return readTiff(view, offset + 10);
      }
      offset += 2 + size;
    }
    return null;
  }

  function readTiff(view, tiff) {
    var le = view.getUint16(tiff) === 0x4949;
    function u16(pos) { return view.getUint16(tiff + pos, le); }
    function u32(pos) { return view.getUint32(tiff + pos, le); }
    if (u16(2) !== 42) return null;

    function readIfd(pos) {
      var tags = {};
      if (pos < 0 || tiff + pos + 2 > view.byteLength) return tags;
      var count = u16(pos);
      var entry = pos + 2;
      var i;
      for (i = 0; i < count; i += 1) {
        if (tiff + entry + 12 > view.byteLength) break;
        tags[u16(entry)] = {
          type: u16(entry + 2),
          count: u32(entry + 4),
          valuePos: tiff + entry + 8,
          value: u32(entry + 8)
        };
        entry += 12;
      }
      return tags;
    }

    function payloadPos(entry) {
      var sizes = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 10: 8 };
      var size = (sizes[entry.type] || 0) * entry.count;
      if (size > 0 && size <= 4) return entry.valuePos;
      return tiff + entry.value;
    }

    function rational(entry) {
      var pos = payloadPos(entry);
      var signed = entry.type === 10;
      if (pos < 0 || pos + 8 > view.byteLength) return null;
      var num = signed ? view.getInt32(pos, le) : view.getUint32(pos, le);
      var den = signed ? view.getInt32(pos + 4, le) : view.getUint32(pos + 4, le);
      if (!den) return null;
      return num / den;
    }

    function numeric(entry) {
      if (!entry) return null;
      if (entry.type === 5 || entry.type === 10) return rational(entry);
      if (entry.type === 3) return view.getUint16(entry.valuePos, le);
      if (entry.type === 4) return view.getUint32(entry.valuePos, le);
      return null;
    }

    function ascii(entry) {
      if (!entry || entry.type !== 2 || !entry.count) return "";
      var pos = payloadPos(entry);
      var out = "";
      var i;
      for (i = 0; i < entry.count; i += 1) {
        if (pos + i >= view.byteLength) break;
        var code = view.getUint8(pos + i);
        if (!code) break;
        out += String.fromCharCode(code);
      }
      return out;
    }

    var ifd0 = readIfd(u32(4));
    var result = {};
    var exif = ifd0[0x8769] ? readIfd(ifd0[0x8769].value) : {};
    result.focal35 = numeric(exif[0xa405]);
    result.subjectM = numeric(exif[0x9206]);
    result.when = ascii(exif[0x9003]) || ascii(ifd0[0x0132]);
    return result;
  }

  function findWhen(buffer) {
    var bytes = new Uint8Array(buffer);
    var limit = Math.min(bytes.length, 131072);
    var text = "";
    var i;
    var code;
    for (i = 0; i < limit; i += 1) {
      code = bytes[i];
      text += (code >= 32 && code <= 126) ? String.fromCharCode(code) : " ";
    }
    var match = text.match(/20\d{2}:\d{2}:\d{2} \d{2}:\d{2}:\d{2}/);
    return match ? match[0] : "";
  }

  function formatWhen(raw) {
    var match = /^(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2})/.exec(raw || "");
    if (!match) return "";
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var hour = Number(match[4]);
    var h12 = hour % 12 || 12;
    return Number(match[3]) + " " + months[Number(match[2]) - 1] + " " + match[1] +
      ", " + h12 + ":" + match[5] + " " + (hour >= 12 ? "PM" : "AM");
  }

  function start() {
    applyScale();
    fetch(photo.getAttribute("src"))
      .then(function (response) { return response.arrayBuffer(); })
      .then(function (buffer) {
        var exif = readExif(buffer) || {};
        var taken = formatWhen(exif.when || findWhen(buffer));
        if (taken) {
          whenEl.textContent = "Photographed " + taken;
          placeCmLabels();
        }
        if (exif.subjectM > 0 && exif.focal35 > 0) useFocusDistance(exif);
      })
      .catch(function () {
        /* the sidewalk width remains the scale */
      });
  }

  if (photo.complete && photo.naturalWidth) start();
  else photo.addEventListener("load", start);
  photo.addEventListener("error", function () {
    note.textContent = "The sidewalk photograph did not load.";
  });
})();
