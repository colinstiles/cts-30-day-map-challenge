(function () {
  "use strict";

  var embed = document.documentElement.classList.contains("d29-embed");
  var stage = document.getElementById("d29-stage");
  var img = document.getElementById("d29-map");
  var summary = document.getElementById("d29-summary");
  var note = document.getElementById("d29-note");
  var legend = document.getElementById("d29-legend");
  var readout = document.getElementById("d29-readout");
  var fuelLine = document.getElementById("d29-fuel");
  var recentLine = document.getElementById("d29-recent");
  var futureLine = document.getElementById("d29-future");
  var deltaLine = document.getElementById("d29-delta");
  var slopeLine = document.getElementById("d29-slope");
  var buttons = Array.prototype.slice.call(document.querySelectorAll(".d29-modes button"));

  var MODES = {
    threat: "day-29.png",
    fuels: "fuels.png",
    change: "change.png"
  };

  var meta = null;
  var fuels = {};
  var values = null;
  var recentGrid = null;
  var view = 1;
  var panX = 0;
  var panY = 0;
  var base = 1;
  var dragging = false;
  var dragX = 0;
  var dragY = 0;
  var mode = "threat";

  function oneIn(probability) {
    if (!(probability > 0)) return "No simulated large fire";
    var years = 1 / probability;
    if (years >= 10) return "1 year in " + Math.round(years).toLocaleString("en-US");
    return (probability * 100).toFixed(2) + "% in a year";
  }

  function decode(high, low) {
    return ((high * 256 + low) / 65535) * meta.bpScale;
  }

  function loadCanvas(src) {
    return new Promise(function (resolve, reject) {
      var image = new Image();
      image.onload = function () {
        var canvas = document.createElement("canvas");
        canvas.width = image.naturalWidth;
        canvas.height = image.naturalHeight;
        var context = canvas.getContext("2d", { willReadFrequently: true });
        context.drawImage(image, 0, 0);
        resolve(context);
      };
      image.onerror = reject;
      image.src = src;
    });
  }

  function layout() {
    var rect = stage.getBoundingClientRect();
    if (!img.naturalWidth || rect.width === 0) return;
    base = Math.min(rect.width / img.naturalWidth, rect.height / img.naturalHeight);
    apply();
  }

  function apply() {
    var rect = stage.getBoundingClientRect();
    var width = img.naturalWidth * base * view;
    var height = img.naturalHeight * base * view;
    var left = (rect.width - width) / 2 + panX;
    var top = (rect.height - height) / 2 + panY;
    img.style.width = width + "px";
    img.style.height = height + "px";
    img.style.transform = "translate(" + left + "px, " + top + "px)";
  }

  function imagePixel(clientX, clientY) {
    var rect = stage.getBoundingClientRect();
    var width = img.naturalWidth * base * view;
    var height = img.naturalHeight * base * view;
    var left = (rect.width - width) / 2 + panX;
    var top = (rect.height - height) / 2 + panY;
    return {
      x: Math.floor((clientX - rect.left - left) / (base * view)),
      y: Math.floor((clientY - rect.top - top) / (base * view))
    };
  }

  function showReadout(event) {
    if (!values || !recentGrid || !meta) return;
    var pixel = imagePixel(event.clientX, event.clientY);
    if (pixel.x < 0 || pixel.y < 0 || pixel.x >= img.naturalWidth || pixel.y >= img.naturalHeight) {
      readout.hidden = true;
      return;
    }
    var sample = values.getImageData(pixel.x, pixel.y, 1, 1).data;
    var fuel = fuels[sample[2]];
    if (!fuel) {
      readout.hidden = true;
      return;
    }
    var other = recentGrid.getImageData(pixel.x, pixel.y, 1, 1).data;
    var future = decode(sample[0], sample[1]);
    var recent = decode(other[0], other[1]);
    fuelLine.textContent = fuel.name;
    recentLine.textContent = "2004–2018 · " + oneIn(recent);
    futureLine.textContent = "2040–2054 · " + oneIn(future);
    if (recent > 0) {
      var pct = ((future - recent) / recent) * 100;
      var sign = pct > 0 ? "+" : "";
      deltaLine.textContent = sign + pct.toFixed(0) + "% from the recent climate";
    } else if (future > 0) {
      deltaLine.textContent = "Rises from no simulated large fire";
    } else {
      deltaLine.textContent = "Unchanged at no simulated large fire";
    }
    slopeLine.textContent = "Slope " + other[2] + "°";
    readout.hidden = false;
  }

  function setMode(next) {
    mode = next;
    img.src = MODES[next];
    buttons.forEach(function (button) {
      button.setAttribute("aria-pressed", button.getAttribute("data-mode") === next ? "true" : "false");
    });
    if (meta) note.textContent = meta.notes[next];
    if (meta) drawLegend();
  }

  function drawLegend() {
    legend.textContent = "";
    var items = mode === "change"
      ? [
          { id: "odds rise", color: "#db662e" },
          { id: "odds fall", color: "#61858f" }
        ]
      : meta.groups;
    items.forEach(function (group) {
      var item = document.createElement("span");
      item.className = "d29-swatch";
      var chip = document.createElement("i");
      chip.style.setProperty("--swatch", group.color);
      item.appendChild(chip);
      item.appendChild(document.createTextNode(group.id.replace("-", " ")));
      legend.appendChild(item);
    });
  }

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      setMode(button.getAttribute("data-mode"));
    });
  });

  window.addEventListener("keydown", function (event) {
    if (embed) return;
    if (event.key === "1") setMode("threat");
    if (event.key === "2") setMode("fuels");
    if (event.key === "3") setMode("change");
  });

  stage.addEventListener("pointermove", function (event) {
    if (dragging) {
      panX += event.clientX - dragX;
      panY += event.clientY - dragY;
      dragX = event.clientX;
      dragY = event.clientY;
      apply();
    }
    if (!embed) showReadout(event);
  });

  stage.addEventListener("pointerdown", function (event) {
    if (embed || view === 1) return;
    dragging = true;
    dragX = event.clientX;
    dragY = event.clientY;
    stage.setPointerCapture(event.pointerId);
  });

  stage.addEventListener("pointerup", function () { dragging = false; });
  stage.addEventListener("pointerleave", function () {
    dragging = false;
    readout.hidden = true;
  });

  stage.addEventListener("wheel", function (event) {
    if (embed) return;
    event.preventDefault();
    var previous = view;
    var factor = event.deltaY < 0 ? 1.12 : 1 / 1.12;
    view = Math.min(8, Math.max(1, previous * factor));
    var rect = stage.getBoundingClientRect();
    var pointerX = event.clientX - rect.left;
    var pointerY = event.clientY - rect.top;
    var left = (rect.width - img.naturalWidth * base * previous) / 2 + panX;
    var top = (rect.height - img.naturalHeight * base * previous) / 2 + panY;
    var imageX = (pointerX - left) / (base * previous);
    var imageY = (pointerY - top) / (base * previous);
    var nextWidth = img.naturalWidth * base * view;
    var nextHeight = img.naturalHeight * base * view;
    panX = pointerX - imageX * base * view - (rect.width - nextWidth) / 2;
    panY = pointerY - imageY * base * view - (rect.height - nextHeight) / 2;
    if (view === 1) {
      panX = 0;
      panY = 0;
    }
    apply();
  }, { passive: false });

  window.addEventListener("resize", layout);

  fetch("meta.json")
    .then(function (response) { return response.json(); })
    .then(function (payload) {
      meta = payload;
      payload.fuels.forEach(function (fuel) { fuels[fuel.index] = fuel; });
      summary.textContent = payload.summary;
      note.textContent = payload.notes.threat;
      drawLegend();
      return Promise.all([loadCanvas("values.png"), loadCanvas("recent.png")]);
    })
    .then(function (grids) {
      values = grids[0];
      recentGrid = grids[1];
    })
    .catch(function () {
      summary.textContent = "The raster metadata did not load.";
    });

  img.addEventListener("load", layout);
  setMode("threat");
})();
