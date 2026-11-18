import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";

const TERRAIN = window.DAY05_TERRAIN;
const EXAG = 3;
const INTRO_S = 11;
const SWEEP_SPEED = 0.22;

const params = new URLSearchParams(window.location.search);
const embed = params.get("embed") === "1";
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const view = document.getElementById("viewshed-view");
const readout = document.getElementById("viewshed-readout");
const statusEl = document.getElementById("viewshed-status");
const credit = document.getElementById("viewshed-credit");
const playButton = document.getElementById("viewshed-play");
const replayButton = document.getElementById("viewshed-replay");
const groundButton = document.getElementById("viewshed-ground");
const platformButton = document.getElementById("viewshed-platform");
const compass = document.getElementById("viewshed-compass").querySelector("span");

function fail(message) {
  statusEl.hidden = false;
  statusEl.textContent = message;
}

window.addEventListener("error", (event) => {
  fail(event.message || "The view stopped.");
});

if (!TERRAIN) {
  fail("Terrain data did not load.");
} else {
  start();
}

function decodeBase64(b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) {
    bytes[i] = bin.charCodeAt(i);
  }
  return bytes;
}

function decodeElev(b64) {
  const bytes = decodeBase64(b64);
  return new Uint16Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 2);
}

function decodeMask(b64, count) {
  const bytes = decodeBase64(b64);
  const mask = new Uint8Array(count);
  for (let i = 0; i < count; i += 1) {
    mask[i] = (bytes[i >> 3] >> (i & 7)) & 1;
  }
  return mask;
}

function metersPerDegree(lat) {
  const mLat = 111132.92 - 559.82 * Math.cos((2 * lat * Math.PI) / 180);
  const mLon = 111412.84 * Math.cos((lat * Math.PI) / 180);
  return { mLat, mLon };
}

function hillshade(elev, n, cell) {
  const shade = new Float32Array(n * n);
  const azimuth = (315 * Math.PI) / 180;
  const zenith = ((90 - 42) * Math.PI) / 180;
  const at = (r, c) => elev[Math.max(0, Math.min(n - 1, r)) * n + Math.max(0, Math.min(n - 1, c))];
  for (let r = 0; r < n; r += 1) {
    for (let c = 0; c < n; c += 1) {
      const dzdx =
        (at(r - 1, c + 1) + 2 * at(r, c + 1) + at(r + 1, c + 1) -
          (at(r - 1, c - 1) + 2 * at(r, c - 1) + at(r + 1, c - 1))) /
        (8 * cell);
      const dzdy =
        (at(r + 1, c - 1) + 2 * at(r + 1, c) + at(r + 1, c + 1) -
          (at(r - 1, c - 1) + 2 * at(r - 1, c) + at(r - 1, c + 1))) /
        (8 * cell);
      const slope = Math.atan(Math.hypot(dzdx, dzdy));
      const aspect = Math.atan2(dzdy, -dzdx);
      const lit =
        Math.cos(zenith) * Math.cos(slope) +
        Math.sin(zenith) * Math.sin(slope) * Math.cos(azimuth - aspect);
      shade[r * n + c] = Math.max(0, lit);
    }
  }
  return shade;
}

function seenShare(mask) {
  let seen = 0;
  for (let i = 0; i < mask.length; i += 1) {
    seen += mask[i];
  }
  return seen / mask.length;
}

function start() {
  if (embed) {
    document.body.classList.add("viewshed-embed");
  }

  const n = TERRAIN.n;
  const cell = TERRAIN.cell;
  const center = (n - 1) / 2;
  const elev = decodeElev(TERRAIN.elev);
  const masks = {
    ground: decodeMask(TERRAIN.masks.ground, n * n),
    platform: decodeMask(TERRAIN.masks.platform, n * n)
  };
  const shade = hillshade(elev, n, cell);
  let zMin = elev[0];
  let zMax = elev[0];
  for (let i = 1; i < elev.length; i += 1) {
    zMin = Math.min(zMin, elev[i]);
    zMax = Math.max(zMax, elev[i]);
  }
  const maxDist = TERRAIN.radius * Math.SQRT2;
  const shares = {
    ground: seenShare(masks.ground),
    platform: seenShare(masks.platform)
  };
  let mode = "platform";
  let playing = !reduced;
  let pageVisible = true;
  let elapsed = reduced ? INTRO_S : 0;
  let lastTick = performance.now();

  const groundY = (TERRAIN.ground - zMin) * EXAG;
  const targetY = groundY * 0.45;

  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.setSize(view.clientWidth, view.clientHeight);
  renderer.setClearColor(0x12140e, 1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  view.appendChild(renderer.domElement);

  const labels = new CSS2DRenderer();
  labels.setSize(view.clientWidth, view.clientHeight);
  labels.domElement.style.position = "absolute";
  labels.domElement.style.inset = "0";
  labels.domElement.style.pointerEvents = "none";
  view.appendChild(labels.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, view.clientWidth / view.clientHeight, 20, 180000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, targetY, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.autoRotateSpeed = 0.55;
  controls.maxPolarAngle = Math.PI * 0.49;
  controls.minDistance = 1800;
  controls.maxDistance = TERRAIN.radius * 2.4;
  controls.enabled = false;

  const positions = new Float32Array(n * n * 3);
  const vis = new Float32Array(masks.platform);
  const shadeAttr = new Float32Array(shade);
  const elevAttr = new Float32Array(elev);
  const distAttr = new Float32Array(n * n);
  for (let r = 0; r < n; r += 1) {
    for (let c = 0; c < n; c += 1) {
      const i = r * n + c;
      const east = (c - center) * cell;
      const north = (center - r) * cell;
      positions[i * 3] = east;
      positions[i * 3 + 1] = (elev[i] - zMin) * EXAG;
      positions[i * 3 + 2] = -north;
      distAttr[i] = Math.hypot(east, north);
    }
  }
  const indices = new Uint32Array((n - 1) * (n - 1) * 6);
  let k = 0;
  for (let r = 0; r < n - 1; r += 1) {
    for (let c = 0; c < n - 1; c += 1) {
      const a = r * n + c;
      indices[k] = a;
      indices[k + 1] = a + n;
      indices[k + 2] = a + 1;
      indices[k + 3] = a + 1;
      indices[k + 4] = a + n;
      indices[k + 5] = a + n + 1;
      k += 6;
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("vis", new THREE.BufferAttribute(vis, 1));
  geometry.setAttribute("shade", new THREE.BufferAttribute(shadeAttr, 1));
  geometry.setAttribute("elevM", new THREE.BufferAttribute(elevAttr, 1));
  geometry.setAttribute("dist", new THREE.BufferAttribute(distAttr, 1));
  geometry.setIndex(new THREE.BufferAttribute(indices, 1));
  geometry.computeVertexNormals();

  const material = new THREE.ShaderMaterial({
    uniforms: {
      reveal: { value: reduced ? maxDist : 0 },
      zMin: { value: zMin },
      zSpan: { value: Math.max(1, zMax - zMin) }
    },
    vertexShader: `
      attribute float vis;
      attribute float shade;
      attribute float elevM;
      attribute float dist;
      varying float vVis;
      varying float vShade;
      varying float vElev;
      varying float vDist;
      varying float vCam;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        vCam = length(mv.xyz);
        vVis = vis;
        vShade = shade;
        vElev = elevM;
        vDist = dist;
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: `
      precision highp float;
      uniform float reveal;
      uniform float zMin;
      uniform float zSpan;
      varying float vVis;
      varying float vShade;
      varying float vElev;
      varying float vDist;
      varying float vCam;
      void main() {
        float h = clamp((vElev - zMin) / zSpan, 0.0, 1.0);
        vec3 hidden = mix(vec3(0.09, 0.12, 0.08), vec3(0.30, 0.27, 0.22), h);
        vec3 seen = mix(vec3(0.48, 0.40, 0.16), vec3(0.93, 0.78, 0.42), h);
        float show = vVis * (1.0 - smoothstep(reveal - 600.0, reveal + 900.0, vDist));
        vec3 col = mix(hidden, seen, show);
        col *= 0.42 + 0.78 * clamp(vShade, 0.0, 1.0);
        float fog = smoothstep(22000.0, 70000.0, vCam);
        col = mix(col, vec3(0.07, 0.075, 0.055), fog);
        gl_FragColor = vec4(col, 1.0);
      }
    `
  });
  scene.add(new THREE.Mesh(geometry, material));

  const beacon = new THREE.Mesh(
    new THREE.SphereGeometry(80, 18, 12),
    new THREE.MeshBasicMaterial({ color: 0xe8c46a })
  );
  beacon.position.set(0, groundY + 90, 0);
  scene.add(beacon);

  const beam = new THREE.Mesh(
    new THREE.CylinderGeometry(36, 36, 1, 7),
    new THREE.MeshBasicMaterial({ color: 0xf3e7b0, transparent: true, opacity: 0.85 })
  );
  scene.add(beam);
  const beamTip = new THREE.Mesh(
    new THREE.SphereGeometry(90, 14, 10),
    new THREE.MeshBasicMaterial({ color: 0xf3e7b0 })
  );
  scene.add(beamTip);
  const yAxis = new THREE.Vector3(0, 1, 0);

  const { mLat, mLon } = metersPerDegree(TERRAIN.lat);
  const roan = TERRAIN.places.find((place) => place.name === "Roan High Knob");
  const roanEast = roan ? (roan.lon - TERRAIN.lon) * mLon : 1;
  const roanNorth = roan ? (roan.lat - TERRAIN.lat) * mLat : -1;
  let sweep = Math.atan2(roanEast, roanNorth);
  function placeLabel(name, lat, lon, elevM, className) {
    const el = document.createElement("div");
    el.className = className;
    el.textContent = className.includes("is-hidden") ? `${name} · hidden` : name;
    const obj = new CSS2DObject(el);
    const east = (lon - TERRAIN.lon) * mLon;
    const north = (lat - TERRAIN.lat) * mLat;
    obj.position.set(east, (elevM - zMin) * EXAG + 220, -north);
    scene.add(obj);
  }
  placeLabel("Fire tower", TERRAIN.lat, TERRAIN.lon, TERRAIN.ground, "viewshed-label is-tower");
  TERRAIN.places.forEach((place) => {
    const kind = place.seen ? "viewshed-label is-seen" : "viewshed-label is-hidden";
    placeLabel(place.name, place.lat, place.lon, place.elev, kind);
  });

  function orbitPoint(theta) {
    const reach = TERRAIN.radius * 0.92;
    const height = (zMax - zMin) * EXAG * 0.72 + 3500;
    return new THREE.Vector3(Math.sin(theta) * reach, height, Math.cos(theta) * reach);
  }

  const introFrom = new THREE.Vector3(700, groundY + 280, 1100);
  const introLook = new THREE.Vector3(1800, groundY, -2600);
  const theta = -2.35;
  let orbiting = false;

  function applyIntro(t) {
    const ease = 1 - (1 - t) ** 3;
    camera.position.lerpVectors(introFrom, orbitPoint(theta), ease);
    const look = introLook.clone().lerp(controls.target, ease);
    camera.lookAt(look);
    camera.up.set(0, 1, 0);
  }

  function horizonIndex(angle) {
    // The sightline crosses hidden valleys, so keep the farthest revealed cell.
    const sin = Math.sin(angle);
    const cos = Math.cos(angle);
    const mask = masks[mode];
    const reach = material.uniforms.reveal.value;
    let last = -1;
    for (let s = 1; s <= center; s += 1) {
      const c = Math.round(center + sin * s);
      const r = Math.round(center - cos * s);
      if (r < 0 || c < 0 || r >= n || c >= n) {
        break;
      }
      const i = r * n + c;
      if (distAttr[i] > reach) {
        break;
      }
      if (mask[i]) {
        last = i;
      }
    }
    return last;
  }

  function aimBeam() {
    const i = horizonIndex(sweep);
    if (i < 0) {
      beam.visible = false;
      beamTip.visible = false;
      return;
    }
    const end = new THREE.Vector3(positions[i * 3], positions[i * 3 + 1] + 40, positions[i * 3 + 2]);
    const eye = TERRAIN.heights[mode] * EXAG;
    const start = new THREE.Vector3(0, groundY + eye, 0);
    const dir = end.clone().sub(start);
    const len = dir.length();
    beam.visible = true;
    beamTip.visible = true;
    beam.scale.set(1, len, 1);
    beam.position.copy(start).addScaledVector(dir, 0.5);
    beam.quaternion.setFromUnitVectors(yAxis, dir.multiplyScalar(1 / len));
    beamTip.position.copy(end);
  }

  function updateCompass() {
    const forward = new THREE.Vector3();
    camera.getWorldDirection(forward);
    // +x is east and +z is south, so a north-facing camera has heading 0.
    const heading = Math.atan2(forward.x, -forward.z);
    compass.style.transform = `rotate(${-heading}rad)`;
  }

  function setMode(next) {
    mode = next;
    geometry.getAttribute("vis").array.set(masks[mode]);
    geometry.getAttribute("vis").needsUpdate = true;
    groundButton.setAttribute("aria-pressed", String(mode === "ground"));
    platformButton.setAttribute("aria-pressed", String(mode === "platform"));
    writeReadout();
  }

  function writeReadout() {
    const height = TERRAIN.heights[mode];
    const pct = Math.round(shares[mode] * 100);
    const where = mode === "platform" ? "the platform" : "the rock";
    readout.textContent = `${pct}% in sight from ${where} · ${height} m up`;
  }

  function writeCredit() {
    const km = Math.round((TERRAIN.radius * 2) / 1000);
    credit.textContent =
      `USGS 3DEP elevation. Viewshed on a ${TERRAIN.viewCell} m grid, drawn on a ${TERRAIN.cell} m mesh, ` +
      `${km} km across. Curvature and refraction are included. ` +
      `${TERRAIN.lat.toFixed(5)}°N, ${Math.abs(TERRAIN.lon).toFixed(5)}°W.`;
  }

  function replay() {
    elapsed = 0;
    sweep = Math.atan2(roanEast, roanNorth);
    orbiting = false;
    controls.enabled = false;
    controls.autoRotate = false;
    playing = true;
    playButton.textContent = "Pause";
    playButton.setAttribute("aria-pressed", "true");
  }

  playButton.addEventListener("click", () => {
    playing = !playing;
    playButton.textContent = playing ? "Pause" : "Play";
    playButton.setAttribute("aria-pressed", String(playing));
    controls.autoRotate = playing && elapsed >= INTRO_S;
  });
  replayButton.addEventListener("click", replay);
  groundButton.addEventListener("click", () => setMode("ground"));
  platformButton.addEventListener("click", () => setMode("platform"));

  window.addEventListener("message", (event) => {
    if (!event.data || event.data.type !== "cts-embed-visible") {
      return;
    }
    pageVisible = Boolean(event.data.visible);
  });
  document.addEventListener("visibilitychange", () => {
    lastTick = performance.now();
  });

  function resize() {
    const w = view.clientWidth;
    const h = Math.max(1, view.clientHeight);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    labels.setSize(w, h);
  }
  window.addEventListener("resize", resize);

  writeReadout();
  writeCredit();
  statusEl.hidden = true;

  function frame(now) {
    const dt = Math.min(0.05, (now - lastTick) / 1000);
    lastTick = now;
    const active = playing && pageVisible && document.visibilityState !== "hidden";
    if (active) {
      elapsed += dt;
      sweep += dt * SWEEP_SPEED;
    }
    const introT = Math.min(elapsed / INTRO_S, 1);
    material.uniforms.reveal.value = (reduced ? 1 : 1 - (1 - introT) ** 3) * maxDist;
    if (elapsed < INTRO_S) {
      controls.autoRotate = false;
      controls.enabled = false;
      applyIntro(introT);
    } else {
      if (!orbiting) {
        camera.position.copy(orbitPoint(theta));
        camera.lookAt(controls.target);
        controls.enabled = !embed;
        orbiting = true;
      }
      controls.autoRotate = active && !reduced;
      controls.update();
    }
    aimBeam();
    updateCompass();
    renderer.render(scene, camera);
    if (!embed) {
      labels.render(scene, camera);
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
