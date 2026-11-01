/* Small interactive Mars globe in grayscale shaded relief.
   The texture is an equirectangular NASA MOLA shaded-relief image, wrapped onto an orthographic
   sphere with a per-pixel inverse projection on a canvas. Drag to rotate. */
(function () {
    'use strict';

    var TEXTURE_URL = window.MARS_TEXTURE_URL;                 // equirectangular, lon -180..180, NASA/JPL MOLA shaded relief (public domain); data URI so it also loads from file://
    var N = 440;                                               // canvas resolution (CSS size is set by the layout)
    var RAD = Math.PI / 180;

    var host = document.getElementById('mars-globe');
    if (!host) { return; }

    var canvas = document.createElement('canvas');
    canvas.width = N;
    canvas.height = N;
    canvas.className = 'mars-canvas';
    host.appendChild(canvas);
    var ctx = canvas.getContext('2d');
    if (!ctx) { return; }

    var label = document.createElement('span');
    label.className = 'mars-label';
    label.textContent = 'Mars';
    host.appendChild(label);

    var view = { lon: 241.3931, lat: -5.5332 };                // view centre (degrees)
    var dragging = false;
    var last = null;
    var dirty = true;
    var onscreen = true;

    // ---- Rendering ----
    var tex = null;            // { w, h, data } sampled by nearest-neighbour from a pre-shrunk copy
    var nx = new Float32Array(N * N);
    var ny = new Float32Array(N * N);
    var nz = new Float32Array(N * N);
    var inside = new Uint8Array(N * N);
    (function () {
        var c = (N - 1) / 2;
        for (var y = 0; y < N; y++) {
            for (var x = 0; x < N; x++) {
                var k = y * N + x;
                var px = (x - c) / (N / 2), py = (c - y) / (N / 2);
                var r2 = px * px + py * py;
                nx[k] = px; ny[k] = py;
                if (r2 <= 1) { inside[k] = 1; nz[k] = Math.sqrt(1 - r2); }
            }
        }
    })();
    var frame = ctx.createImageData(N, N);

    function render() {
        dirty = false;
        if (!tex) { return; }
        var out = frame.data, src = tex.data, W = tex.w, H = tex.h;
        var l0 = view.lon * RAD, f0 = view.lat * RAD;
        var s0 = Math.sin(f0), c0 = Math.cos(f0);
        var TWO_PI = 2 * Math.PI;
        for (var k = 0, n = N * N; k < n; k++) {
            var o = k * 4;
            if (!inside[k]) { out[o + 3] = 0; continue; }
            var z = nz[k], y = ny[k];
            var sinf = z * s0 + y * c0;
            var f = Math.asin(sinf > 1 ? 1 : sinf < -1 ? -1 : sinf);
            var l = l0 + Math.atan2(nx[k], z * c0 - y * s0);
            var u = (l + Math.PI) / TWO_PI; u -= Math.floor(u);
            var v = (Math.PI / 2 - f) / Math.PI;
            var tx = (u * W) | 0, ty = (v * H) | 0;
            if (ty >= H) { ty = H - 1; }
            var t = (ty * W + tx) * 4;
            out[o] = src[t]; out[o + 1] = src[t + 1]; out[o + 2] = src[t + 2]; out[o + 3] = 255;
        }
        ctx.putImageData(frame, 0, 0);
    }

    function loadTexture() {
        var img = new Image();
        img.onload = function () {
            var w = 1536, h = 768;                              // shrink once so sampling a ~440px disc does not alias
            var c = document.createElement('canvas');
            c.width = w; c.height = h;
            var cx = c.getContext('2d');
            cx.imageSmoothingQuality = 'high';
            cx.drawImage(img, 0, 0, w, h);
            tex = { w: w, h: h, data: cx.getImageData(0, 0, w, h).data };
            host.classList.add('ready');
            dirty = true;
        };
        img.src = TEXTURE_URL;                                  // on failure the CSS terracotta disc stays
    }

    // ---- Interaction ----
    host.addEventListener('pointerdown', function (e) {
        dragging = true;
        last = [e.clientX, e.clientY];
        host.setPointerCapture(e.pointerId);
    });
    host.addEventListener('pointermove', function (e) {
        if (!dragging) { return; }
        var k = 0.4;
        view.lon -= (e.clientX - last[0]) * k;
        view.lat = Math.max(-70, Math.min(70, view.lat + (e.clientY - last[1]) * k));
        last = [e.clientX, e.clientY];
        dirty = true;
    });
    function endDrag() { dragging = false; }
    host.addEventListener('pointerup', endDrag);
    host.addEventListener('pointercancel', endDrag);

    function tick() {
        if (dirty && onscreen && !document.hidden) { render(); }
        requestAnimationFrame(tick);
    }

    if ('IntersectionObserver' in window) {
        new IntersectionObserver(function (entries) {
            onscreen = entries[0].isIntersecting;
            if (onscreen) { dirty = true; }
        }).observe(host);
    }

    host.hidden = false;
    if (TEXTURE_URL) { loadTexture(); }
    requestAnimationFrame(tick);
})();
