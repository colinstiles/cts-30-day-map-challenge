import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";

// World axes: +X is west, +Y is up, +Z is north. A camera looking east
// then has north on the left and the north face of Langtang Lirung on the right.
// Elevations are exaggerated by bounds.exaggeration. The water surface is the
// reported observer wave, 250 m above a smoothed channel bed, not the raw grid.

const DURATION = 58;
const params = new URLSearchParams(window.location.search);
const embed = params.has("embed");
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const view = document.getElementById("d28-view");
const phaseEl = document.getElementById("d28-phase");
const lineEl = document.getElementById("d28-line");
const steps = document.querySelectorAll("#d28-steps li");
const playButton = document.getElementById("d28-play");
const replayButton = document.getElementById("d28-replay");
const slider = document.getElementById("d28-slider");
const clockEl = document.getElementById("d28-clock");
const roseArrow = document.getElementById("d28-rose-arrow");
const inset = document.getElementById("d28-inset");
const insetCtx = inset.getContext("2d");

const COPY = {
  before: ["Before 08:37 NPT", "Looking east, up the Lende Khola. The north face of Langtang Lirung is still intact."],
  fail: ["1 · Slope failure", "The face near 5,200 m gives way. The flood leaves the release and starts down the glacier."],
  quake: ["2 · M5.2", "The impact radiates the energy of an M5.2 earthquake. The signal is the collapse, at 08:37."],
  flow: ["3 · Debris flow and flood", "Observers at the border reported a wave about 200–300 m high. The surface is drawn at 250 m above the channel, the middle of that report."],
  ruin: ["4 · Destruction", "At Rasuwagadhi, the bridge gives way. About 08:45. The bridge and the buildings are symbolized in the animation."],
  after: ["Downstream", "The flood continues about 100 km down the Bhotekoshi and Trishuli. Three hours later, a second signal: M4.2."]
};
const STEP_ORDER = ["fail", "quake", "flow", "ruin"];

const REPORTED_WAVE_M = 250;

const WATER_VERT = `
  uniform sampler2D uStageA;
  uniform sampler2D uStageB;
  uniform float uMix;
  uniform float uExag;
  uniform float uAmount;
  uniform vec2 uTexel;
  uniform vec2 uSpan;
  varying float vDepth;
  varying vec3 vWorld;
  varying vec3 vNormal;
  float stageAt(vec2 sampleUv) {
    return mix(texture2D(uStageA, sampleUv).r, texture2D(uStageB, sampleUv).r, uMix);
  }
  void main() {
    float stage = stageAt(uv);
    float left = stageAt(uv - vec2(uTexel.x * 2.0, 0.0));
    float right = stageAt(uv + vec2(uTexel.x * 2.0, 0.0));
    float down = stageAt(uv - vec2(0.0, uTexel.y * 2.0));
    float up = stageAt(uv + vec2(0.0, uTexel.y * 2.0));
    if (left < 1.0) left = stage;
    if (right < 1.0) right = stage;
    if (down < 1.0) down = stage;
    if (up < 1.0) up = stage;
    float slopeX = ((right - left) / (4.0 * uTexel.x)) / -uSpan.x;
    float slopeZ = ((up - down) / (4.0 * uTexel.y)) / uSpan.y;
    vec3 displaced = position;
    float waterY = mix(position.y, stage * uExag, uAmount);
    float depth = (waterY - position.y) / uExag;
    if (stage < 1.0 || depth < 0.4) depth = 0.0;
    else displaced.y = waterY;
    vec4 world = modelMatrix * vec4(displaced, 1.0);
    vWorld = world.xyz;
    vDepth = depth;
    vNormal = normalize(vec3(-slopeX * uExag, 1.0, -slopeZ * uExag));
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

const WATER_FRAG = `
  varying float vDepth;
  varying vec3 vWorld;
  varying vec3 vNormal;
  void main() {
    if (vDepth < 0.4) discard;
    vec3 shallow = vec3(0.64, 0.83, 0.96);
    vec3 deep = vec3(0.06, 0.27, 0.58);
    vec3 normal = normalize(vNormal);
    vec3 viewDir = normalize(cameraPosition - vWorld);
    vec3 lightDir = normalize(vec3(-0.4, 0.86, -0.25));
    float deepness = smoothstep(12.0, 90.0, vDepth);
    vec3 color = mix(shallow, deep, deepness);
    float fresnel = pow(1.0 - clamp(dot(viewDir, normal), 0.0, 1.0), 2.4);
    color = mix(color, vec3(0.82, 0.92, 0.98), fresnel * 0.22);
    float diffuse = 0.86 + 0.14 * clamp(dot(normal, lightDir), 0.0, 1.0);
    float spec = pow(max(dot(normal, normalize(viewDir + lightDir)), 0.0), 28.0);
    color = color * diffuse + vec3(0.75, 0.88, 0.97) * spec * 0.18;
    gl_FragColor = vec4(color, 0.92);
  }
`;

let film = 0;
let playing = !reduced;
let parentVisible = true;
let userMoved = false;
let lastTick = 0;
let bounds = null;
let dem = null;
let flow = null;
let home = null;
let look = null;
let shots = [];
let tracks = [];
let river = [];
let releasePos = null;
let impactPos = null;
let bridgePos = null;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xb7c4ce);
scene.fog = new THREE.Fog(0xb7c4ce, 18000, 52000);

const camera = new THREE.PerspectiveCamera(40, 1, 6, 90000);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
view.appendChild(renderer.domElement);

const labels = new CSS2DRenderer();
labels.domElement.style.position = "absolute";
labels.domElement.style.inset = "0";
labels.domElement.style.pointerEvents = "none";
labels.domElement.style.zIndex = "1";
view.appendChild(labels.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.49;
controls.minDistance = 600;
controls.maxDistance = 42000;
controls.addEventListener("start", () => {
  userMoved = true;
});

const sun = new THREE.DirectionalLight(0xfff3e4, 2.8);
sun.position.set(-16000, 19000, -8000);
scene.add(sun);
scene.add(new THREE.HemisphereLight(0xd5e2ea, 0x8d7a64, 0.72));
scene.add(new THREE.AmbientLight(0xffffff, 0.18));

const stageTextures = [makeStageTexture(), makeStageTexture()];
const waterUniforms = {
  uStageA: { value: stageTextures[0] },
  uStageB: { value: stageTextures[1] },
  uMix: { value: 0 },
  uExag: { value: 1.15 },
  uAmount: { value: 0 },
  uTexel: { value: new THREE.Vector2(1 / 520, 1 / 337) },
  uSpan: { value: new THREE.Vector2(27468, 17722) }
};
const waterMaterial = new THREE.ShaderMaterial({
  uniforms: waterUniforms,
  vertexShader: WATER_VERT,
  fragmentShader: WATER_FRAG,
  transparent: true,
  depthWrite: true,
  side: THREE.DoubleSide,
  polygonOffset: true,
  polygonOffsetFactor: -2,
  polygonOffsetUnits: -2
});
let waterMesh = null;
let rings = [];
let crossing = null;
let loadedFrame = [-1, -1];

function makeStageTexture() {
  const data = new Float32Array(4);
  const texture = new THREE.DataTexture(data, 1, 1, THREE.RedFormat, THREE.FloatType);
  texture.flipY = true;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  texture.colorSpace = THREE.NoColorSpace;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.needsUpdate = true;
  return texture;
}

function mercY(lat) {
  return Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
}

function toWorld(lat, lon, elev) {
  const north = mercY(bounds.north);
  const south = mercY(bounds.south);
  const v = (north - mercY(lat)) / (north - south);
  const u = (lon - bounds.west) / (bounds.east - bounds.west);
  return new THREE.Vector3(
    -(u * bounds.width_m - bounds.width_m / 2),
    elev * bounds.exaggeration,
    (1 - v) * bounds.height_m - bounds.height_m / 2
  );
}

function sampleElev(lat, lon) {
  const north = mercY(bounds.north);
  const south = mercY(bounds.south);
  const v = (north - mercY(lat)) / (north - south);
  const u = (lon - bounds.west) / (bounds.east - bounds.west);
  const row = Math.min(bounds.rows - 1, Math.max(0, Math.round(v * bounds.rows - 0.5)));
  const col = Math.min(bounds.cols - 1, Math.max(0, Math.round(u * bounds.cols - 0.5)));
  return dem[row * bounds.cols + col];
}

function addLabel(title, detail, position) {
  const element = document.createElement("div");
  element.className = "d28-label";
  element.textContent = title;
  if (detail) {
    const small = document.createElement("small");
    small.textContent = detail;
    element.appendChild(small);
  }
  const object = new CSS2DObject(element);
  object.position.copy(position);
  scene.add(object);
}

function buildTerrain(imagery) {
  const rows = bounds.rows;
  const cols = bounds.cols;
  const positions = new Float32Array(rows * cols * 3);
  const uvs = new Float32Array(rows * cols * 2);
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const index = row * cols + col;
      const u = (col + 0.5) / cols;
      const v = (row + 0.5) / rows;
      positions[index * 3] = -(u * bounds.width_m - bounds.width_m / 2);
      positions[index * 3 + 1] = dem[index] * bounds.exaggeration;
      positions[index * 3 + 2] = (1 - v) * bounds.height_m - bounds.height_m / 2;
      uvs[index * 2] = u;
      uvs[index * 2 + 1] = 1 - v;
    }
  }
  const indices = new Uint32Array((rows - 1) * (cols - 1) * 6);
  let offset = 0;
  for (let row = 0; row < rows - 1; row += 1) {
    for (let col = 0; col < cols - 1; col += 1) {
      const a = row * cols + col;
      indices[offset] = a;
      indices[offset + 1] = a + cols;
      indices[offset + 2] = a + 1;
      indices[offset + 3] = a + 1;
      indices[offset + 4] = a + cols;
      indices[offset + 5] = a + cols + 1;
      offset += 6;
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
  geometry.setIndex(new THREE.BufferAttribute(indices, 1));
  geometry.computeVertexNormals();

  imagery.colorSpace = THREE.SRGBColorSpace;
  imagery.anisotropy = 4;
  const terrain = new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({ map: imagery, roughness: 0.94, metalness: 0 })
  );
  scene.add(terrain);

  waterMesh = new THREE.Mesh(geometry.clone(), waterMaterial);
  waterMesh.renderOrder = 2;
  scene.add(waterMesh);
}

function buildProps() {
  releasePos = toWorld(bounds.release.lat, bounds.release.lon, bounds.release.elev_m);
  bridgePos = toWorld(bounds.bridge.lat, bounds.bridge.lon, bounds.bridge.elev_m);
  if (bounds.impact) {
    impactPos = toWorld(bounds.impact.lat, bounds.impact.lon, bounds.impact.elev_m);
  } else {
    impactPos = releasePos.clone().lerp(bridgePos, 0.18);
    impactPos.y = releasePos.y * 0.72 + bridgePos.y * 0.28;
  }
  const summit = toWorld(bounds.summit.lat, bounds.summit.lon, bounds.summit.elev_m);
  const summitLabel = summit.clone().lerp(bridgePos, 0.1);
  summitLabel.y -= 1100;
  addLabel("Langtang Lirung", "7,227 m", summitLabel);
  addLabel("~5,200 m", "", releasePos.clone().setY(releasePos.y + 220));
  if (bounds.impact && bounds.impact.elev_m < 4600) {
    addLabel("Lhende Glacier", "", impactPos.clone().setY(impactPos.y + 260));
  }
  const kholaLon = bounds.bridge.lon + 0.045;
  const kholaElev = sampleElev(bounds.bridge.lat, kholaLon);
  const khola = toWorld(bounds.bridge.lat, kholaLon, kholaElev);
  addLabel("Lende Khola", "", khola.clone().setY(khola.y + 380));
  addLabel("Rasuwagadhi", "", bridgePos.clone().setY(bridgePos.y + 320));

  const offset = (point, west, up, north) => new THREE.Vector3(point.x + west, point.y + up, point.z + north);
  shots = [
    { t: 0, pos: offset(releasePos, 5200, 4400, 7400), target: releasePos.clone() },
    { t: 8, pos: offset(releasePos, 1800, 2000, 2600), target: releasePos.clone() }
  ];
  look = shots[0].target.clone();
  home = shots[0].pos.clone();
  camera.position.copy(home);
  controls.target.copy(look);
  tracks = buildTracks();
  river = traceRiver();

  rings = [0, 1, 2].map(() => {
    const mesh = new THREE.Mesh(
      new THREE.RingGeometry(180, 340, 64),
      new THREE.MeshBasicMaterial({
        color: 0xf7f1e4,
        transparent: true,
        opacity: 0.8,
        side: THREE.DoubleSide,
        depthWrite: false
      })
    );
    mesh.rotation.x = -Math.PI / 2;
    mesh.visible = false;
    mesh.position.copy(impactPos);
    mesh.position.y += 40;
    scene.add(mesh);
    return mesh;
  });

  crossing = new THREE.Group();
  const deck = new THREE.Mesh(
    new THREE.BoxGeometry(150, 8, 18),
    new THREE.MeshStandardMaterial({ color: 0xd7d8dc, roughness: 0.55 })
  );
  deck.position.y = 16;
  const road = new THREE.Mesh(
    new THREE.BoxGeometry(16, 3, 220),
    new THREE.MeshStandardMaterial({ color: 0x6e675e, roughness: 0.9 })
  );
  road.position.set(0, 6, -140);
  crossing.add(deck, road);
  [[70, 40], [-80, 20], [40, -70], [-30, -90]].forEach(([x, z], index) => {
    const height = 16 + (index % 3) * 8;
    const building = new THREE.Mesh(
      new THREE.BoxGeometry(22, height, 18),
      new THREE.MeshStandardMaterial({ color: index % 2 ? 0xcbb89a : 0x8e867c, roughness: 0.86 })
    );
    building.position.set(x, height / 2, z);
    crossing.add(building);
  });
  crossing.position.copy(bridgePos);
  scene.add(crossing);
}

let stages = null;

function resizeTextures() {
  const cells = bounds.flow_rows * bounds.flow_cols;
  stageTextures.forEach((texture) => {
    texture.image = {
      data: new Float32Array(cells),
      width: bounds.flow_cols,
      height: bounds.flow_rows
    };
    texture.needsUpdate = true;
  });
}

function uploadStage(slot, index) {
  if (loadedFrame[slot] === index || !stages) return;
  const cells = bounds.flow_rows * bounds.flow_cols;
  stageTextures[slot].image.data.set(stages.subarray(index * cells, (index + 1) * cells));
  stageTextures[slot].needsUpdate = true;
  loadedFrame[slot] = index;
}

function buildStages() {
  const rows = bounds.flow_rows;
  const cols = bounds.flow_cols;
  const cells = rows * cols;
  const frames = bounds.frame_times_s.length;
  const bed = new Float32Array(cells);
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      bed[row * cols + col] = elevAtUV((col + 0.5) / cols, (row + 0.5) / rows);
    }
  }
  stages = new Float32Array(frames * cells);
  const wet = new Uint8Array(cells);
  const thalweg = new Float32Array(cells);
  const next = new Float32Array(cells);
  for (let frame = 0; frame < frames; frame += 1) {
    const flowBase = frame * cells;
    for (let i = 0; i < cells; i += 1) wet[i] = flow[flowBase + i] * bounds.depth_scale_m >= 1 ? 1 : 0;
    for (let i = 0; i < cells; i += 1) thalweg[i] = wet[i] ? bed[i] : Infinity;
    for (let pass = 0; pass < 5; pass += 1) {
      for (let row = 0; row < rows; row += 1) {
        for (let col = 0; col < cols; col += 1) {
          const index = row * cols + col;
          if (!wet[index]) {
            next[index] = Infinity;
            continue;
          }
          let lowest = thalweg[index];
          for (let dRow = -1; dRow <= 1; dRow += 1) {
            const nearRow = row + dRow;
            if (nearRow < 0 || nearRow >= rows) continue;
            for (let dCol = -1; dCol <= 1; dCol += 1) {
              const nearCol = col + dCol;
              if (nearCol < 0 || nearCol >= cols) continue;
              const value = thalweg[nearRow * cols + nearCol];
              if (value < lowest) lowest = value;
            }
          }
          next[index] = lowest;
        }
      }
      thalweg.set(next);
    }
    const stage = stages.subarray(frame * cells, (frame + 1) * cells);
    for (let i = 0; i < cells; i += 1) stage[i] = wet[i] ? thalweg[i] + REPORTED_WAVE_M : 0;
    for (let pass = 0; pass < 6; pass += 1) {
      next.set(stage);
      for (let row = 0; row < rows; row += 1) {
        for (let col = 0; col < cols; col += 1) {
          const index = row * cols + col;
          if (stage[index] > 0) continue;
          let lowest = Infinity;
          for (let dRow = -1; dRow <= 1; dRow += 1) {
            const nearRow = row + dRow;
            if (nearRow < 0 || nearRow >= rows) continue;
            for (let dCol = -1; dCol <= 1; dCol += 1) {
              const nearCol = col + dCol;
              if (nearCol < 0 || nearCol >= cols) continue;
              const value = stage[nearRow * cols + nearCol];
              if (value > 0 && value < lowest) lowest = value;
            }
          }
          if (lowest < Infinity && bed[index] <= lowest) next[index] = lowest;
        }
      }
      stage.set(next);
    }
    for (let pass = 0; pass < 4; pass += 1) {
      for (let row = 0; row < rows; row += 1) {
        for (let col = 0; col < cols; col += 1) {
          const index = row * cols + col;
          if (stage[index] <= 0) {
            next[index] = 0;
            continue;
          }
          let sum = 0;
          let count = 0;
          for (let dRow = -1; dRow <= 1; dRow += 1) {
            const nearRow = row + dRow;
            if (nearRow < 0 || nearRow >= rows) continue;
            for (let dCol = -1; dCol <= 1; dCol += 1) {
              const nearCol = col + dCol;
              if (nearCol < 0 || nearCol >= cols) continue;
              const value = stage[nearRow * cols + nearCol];
              if (value > 0) {
                sum += value;
                count += 1;
              }
            }
          }
          next[index] = sum / count;
        }
      }
      stage.set(next);
    }
    next.set(stage);
    for (let row = 0; row < rows; row += 1) {
      for (let col = 0; col < cols; col += 1) {
        const index = row * cols + col;
        if (stage[index] > 0) continue;
        let sum = 0;
        let count = 0;
        for (let dRow = -1; dRow <= 1; dRow += 1) {
          const nearRow = row + dRow;
          if (nearRow < 0 || nearRow >= rows) continue;
          for (let dCol = -1; dCol <= 1; dCol += 1) {
            const nearCol = col + dCol;
            if (nearCol < 0 || nearCol >= cols) continue;
            const value = stage[nearRow * cols + nearCol];
            if (value > 0) {
              sum += value;
              count += 1;
            }
          }
        }
        if (count) next[index] = sum / count;
      }
    }
    stage.set(next);
  }
}

function phaseAt(time) {
  if (time < 5) return "before";
  if (time < 12) return "fail";
  if (time < 17) return "quake";
  if (time < 46) return "flow";
  if (time < 54) return "ruin";
  return "after";
}

function simSeconds(time) {
  const arrival = bounds.bridge_arrival_s == null ? bounds.simulated_seconds : bounds.bridge_arrival_s;
  const fall = 90;
  if (time < 5) return -1;
  if (time < 12) return ((time - 5) / 7) * fall;
  if (time < 17) return fall;
  if (time < 50) return fall + ((time - 17) / 33) * Math.max(0, arrival - fall);
  return Math.min(bounds.simulated_seconds, arrival + 160);
}

function smoothstep(value) {
  const t = Math.min(1, Math.max(0, value));
  return t * t * (3 - 2 * t);
}

function groundAt(world) {
  const u = 0.5 - world.x / bounds.width_m;
  const v = 0.5 - world.z / bounds.height_m;
  const col = Math.min(bounds.cols - 1, Math.max(0, Math.round(u * bounds.cols - 0.5)));
  const row = Math.min(bounds.rows - 1, Math.max(0, Math.round(v * bounds.rows - 0.5)));
  return dem[row * bounds.cols + col] * bounds.exaggeration;
}

function shotAt(time) {
  let index = 0;
  while (index < shots.length - 2 && shots[index + 1].t < time) index += 1;
  const from = shots[index];
  const to = shots[index + 1];
  const span = Math.max(0.001, to.t - from.t);
  const blend = smoothstep((time - from.t) / span);
  return {
    pos: from.pos.clone().lerp(to.pos, blend),
    target: from.target.clone().lerp(to.target, blend)
  };
}

function framePair(seconds) {
  const times = bounds.frame_times_s;
  if (seconds <= times[0]) return { i: 0, j: 0, mix: 0 };
  const last = times.length - 1;
  if (seconds >= times[last]) return { i: last, j: last, mix: 0 };
  let index = 0;
  while (index < last - 1 && times[index + 1] < seconds) index += 1;
  const span = times[index + 1] - times[index] || 1;
  return { i: index, j: index + 1, mix: (seconds - times[index]) / span };
}

function elevAtUV(u, v) {
  const col = Math.min(bounds.cols - 1, Math.max(0, Math.round(u * bounds.cols - 0.5)));
  const row = Math.min(bounds.rows - 1, Math.max(0, Math.round(v * bounds.rows - 0.5)));
  return dem[row * bounds.cols + col];
}

function buildTracks() {
  const rows = bounds.flow_rows;
  const cols = bounds.flow_cols;
  const cellCount = rows * cols;
  const frames = bounds.frame_times_s.length;
  const found = [];
  let previous = null;
  for (let frame = 0; frame < frames; frame += 1) {
    const base = frame * cellCount;
    const wet = [];
    let maxX = -Infinity;
    for (let row = 0; row < rows; row += 2) {
      for (let col = 0; col < cols; col += 2) {
        const depth = flow[base + row * cols + col] * bounds.depth_scale_m;
        if (depth < 2) continue;
        const u = (col + 0.5) / cols;
        const v = (row + 0.5) / rows;
        const point = {
          x: -(u * bounds.width_m - bounds.width_m / 2),
          y: elevAtUV(u, v) * bounds.exaggeration,
          z: (1 - v) * bounds.height_m - bounds.height_m / 2,
          depth
        };
        if (point.x > maxX) maxX = point.x;
        wet.push(point);
      }
    }
    if (!wet.length) {
      found.push(previous);
      continue;
    }
    const body = { x: 0, y: 0, z: 0, w: 0 };
    const snout = { x: 0, y: 0, z: 0, w: 0 };
    wet.forEach((point) => {
      body.x += point.x * point.depth;
      body.y += point.y * point.depth;
      body.z += point.z * point.depth;
      body.w += point.depth;
      if (point.x > maxX - 700) {
        snout.x += point.x * point.depth;
        snout.y += point.y * point.depth;
        snout.z += point.z * point.depth;
        snout.w += point.depth;
      }
    });
    previous = {
      body: new THREE.Vector3(body.x / body.w, body.y / body.w, body.z / body.w),
      snout: new THREE.Vector3(snout.x / snout.w, snout.y / snout.w, snout.z / snout.w)
    };
    found.push(previous);
  }
  return found;
}

function chaseAt(seconds) {
  const pair = framePair(Math.max(0, seconds));
  const from = tracks[pair.i] || tracks.find(Boolean);
  const to = tracks[pair.j] || from;
  const body = from.body.clone().lerp(to.body, pair.mix);
  const snout = from.snout.clone().lerp(to.snout, pair.mix);
  const travel = snout.clone().sub(body);
  travel.y = 0;
  if (travel.lengthSq() < 40000) travel.set(1, 0, 0);
  else travel.normalize();
  const side = new THREE.Vector3(-travel.z, 0, travel.x);
  const pos = snout.clone().addScaledVector(travel, -1600).addScaledVector(side, 2600);
  pos.y = snout.y + 3200;
  const clearance = groundAt(pos) + 600;
  if (pos.y < clearance) pos.y = clearance;
  const target = snout.clone().addScaledVector(travel, 900);
  target.y = snout.y + 30;
  return { pos, target };
}

function placeRings(time) {
  const active = time >= 12 && time < 17.5;
  rings.forEach((mesh, index) => {
    mesh.visible = active;
    if (!active) return;
    const age = Math.max(0, time - 12 - index * 0.45);
    const grow = age / 4.2;
    mesh.scale.setScalar(1 + grow * 18);
    mesh.material.opacity = Math.max(0, 0.75 * (1 - grow));
  });
}

function placeCrossing(time) {
  const amount = time < 46 ? 0 : Math.min(1, (time - 46) / 3.2);
  crossing.position.y = bridgePos.y - amount * 22;
  crossing.rotation.z = amount * 0.5;
  crossing.rotation.x = amount * -0.35;
  crossing.traverse((child) => {
    if (!child.isMesh) return;
    if (!child.userData.base) child.userData.base = child.material.color.clone();
    child.material.color.copy(child.userData.base).lerp(new THREE.Color(0x4a453f), amount);
  });
}

function cellUV(lat, lon) {
  const north = mercY(bounds.north);
  const south = mercY(bounds.south);
  const v = (north - mercY(lat)) / (north - south);
  const u = (lon - bounds.west) / (bounds.east - bounds.west);
  return {
    row: Math.min(bounds.rows - 1, Math.max(0, Math.round(v * bounds.rows - 0.5))),
    col: Math.min(bounds.cols - 1, Math.max(0, Math.round(u * bounds.cols - 0.5)))
  };
}

function traceRiver() {
  const start = cellUV(bounds.release.lat, bounds.release.lon);
  const rows = bounds.rows;
  const cols = bounds.cols;
  const path = [];
  let row = start.row;
  let col = start.col;
  const seen = new Set();
  const steps = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]];
  for (let guard = 0; guard < rows + cols; guard += 1) {
    const key = row * cols + col;
    if (seen.has(key)) break;
    seen.add(key);
    path.push({ u: (col + 0.5) / cols, v: (row + 0.5) / rows });
    let best = dem[key];
    let next = null;
    steps.forEach(([dRow, dCol]) => {
      const nextRow = row + dRow;
      const nextCol = col + dCol;
      if (nextRow < 0 || nextCol < 0 || nextRow >= rows || nextCol >= cols) return;
      const elev = dem[nextRow * cols + nextCol];
      if (elev < best) {
        best = elev;
        next = [nextRow, nextCol];
      }
    });
    if (!next) break;
    row = next[0];
    col = next[1];
  }
  const simple = [];
  for (let index = 0; index < path.length; index += 6) simple.push(path[index]);
  if (path.length) simple.push(path[path.length - 1]);
  return simple;
}

function closestRiver(u, v) {
  let best = 0;
  let bestDistance = Infinity;
  river.forEach((point, index) => {
    const east = (point.u - u) * bounds.width_m;
    const north = (point.v - v) * bounds.height_m;
    const distance = east * east + north * north;
    if (distance < bestDistance) {
      bestDistance = distance;
      best = index;
    }
  });
  return best;
}

function insetXY(point) {
  const padX = 28;
  const padY = 22;
  return [
    padX + point.u * (inset.width - padX * 2),
    padY + point.v * (inset.height - padY * 2)
  ];
}

function strokeRiver(points) {
  if (points.length < 2) return;
  insetCtx.beginPath();
  points.forEach((point, index) => {
    const [x, y] = insetXY(point);
    if (index) insetCtx.lineTo(x, y);
    else insetCtx.moveTo(x, y);
  });
  insetCtx.stroke();
}

function insetLabel(text, point, corner) {
  const [x, y] = insetXY(point);
  insetCtx.font = "20px Lato, sans-serif";
  insetCtx.textBaseline = "middle";
  const width = insetCtx.measureText(text).width;
  const textX = corner === "lower"
    ? (inset.width - width) / 2
    : corner === "ne" ? inset.width - width - 8 : 8;
  const textY = corner === "lower" ? inset.height * 0.76 : corner === "ne" ? 16 : inset.height - 14;
  const textEdge = corner === "lower" ? textX + width / 2 : corner === "ne" ? textX : textX + width;
  insetCtx.strokeStyle = "rgba(242, 239, 228, 0.45)";
  insetCtx.lineWidth = 1.5;
  insetCtx.beginPath();
  insetCtx.moveTo(x, y);
  insetCtx.lineTo(textEdge, textY);
  insetCtx.stroke();
  if (corner === "lower") {
    insetCtx.fillStyle = "rgba(14, 16, 18, 0.78)";
    insetCtx.fillRect(textX - 6, textY - 13, width + 12, 26);
  }
  insetCtx.fillStyle = "#f2efe4";
  insetCtx.fillText(text, textX, textY);
  insetCtx.fillStyle = "#8ec4ea";
  insetCtx.beginPath();
  insetCtx.arc(x, y, 4, 0, Math.PI * 2);
  insetCtx.fill();
}

function drawInset(time) {
  const phase = phaseAt(time);
  const on = phase === "flow" || phase === "ruin" || phase === "after";
  inset.classList.toggle("is-on", on);
  if (!on || river.length < 2) return;
  const seconds = simSeconds(time);
  let reach = 0;
  if (seconds >= 0 && tracks.some(Boolean)) {
    const pair = framePair(seconds);
    const from = tracks[pair.i] || tracks.find(Boolean);
    const to = tracks[pair.j] || from;
    const snout = from.snout.clone().lerp(to.snout, pair.mix);
    const u = 0.5 - snout.x / bounds.width_m;
    const v = 0.5 - snout.z / bounds.height_m;
    reach = closestRiver(u, v);
  }
  insetCtx.clearRect(0, 0, inset.width, inset.height);
  insetCtx.fillStyle = "rgba(14, 16, 18, 0.82)";
  insetCtx.fillRect(0, 0, inset.width, inset.height);
  insetCtx.lineJoin = "round";
  insetCtx.lineCap = "round";
  insetCtx.lineWidth = 3;
  insetCtx.strokeStyle = "rgba(242, 239, 228, 0.32)";
  strokeRiver(river);
  insetCtx.lineWidth = 5;
  insetCtx.strokeStyle = "#6aade0";
  strokeRiver(river.slice(0, Math.max(2, reach + 1)));
  const bridgeCell = cellUV(bounds.bridge.lat, bounds.bridge.lon);
  insetLabel("Glacier", river[0], "ne");
  insetLabel("Rasuwagadhi", river[closestRiver(
    (bridgeCell.col + 0.5) / bounds.cols,
    (bridgeCell.row + 0.5) / bounds.rows
  )], "lower");
}

function syncUi(time) {
  const phase = phaseAt(time);
  const copy = reduced && !playing
    ? ["26 August 2026", "Motion is paused on the flood at Rasuwagadhi. The sequence is the collapse, an M5.2 signal, the debris flow, and the crossing."]
    : COPY[phase];
  phaseEl.textContent = copy[0];
  lineEl.textContent = copy[1];
  const active = STEP_ORDER.indexOf(phase);
  steps.forEach((step, index) => {
    step.classList.toggle("is-now", index === active);
    step.classList.toggle("is-done", active === -1 ? phase === "after" : index < active);
  });
  const shown = Math.min(DURATION, Math.max(0, time));
  const seconds = Math.floor(shown);
  clockEl.textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  if (document.activeElement !== slider) slider.value = String(Math.round(shown * 10));
  drawInset(time);
}

function updateRose() {
  const origin = controls.target.clone();
  const north = origin.clone();
  north.z += 2000;
  const from = origin.clone().project(camera);
  const to = north.clone().project(camera);
  if (from.z > 1 || to.z > 1) return;
  const degrees = Math.atan2(to.x - from.x, to.y - from.y) * 180 / Math.PI;
  roseArrow.style.transform = `rotate(${degrees}deg)`;
}

function applyFilm(time) {
  const seconds = simSeconds(time);
  const amount = time < 5 ? 0 : time < 7 ? (time - 5) / 2 : 1;
  if (seconds < 0 || amount <= 0) {
    waterUniforms.uAmount.value = 0;
  } else {
    const pair = framePair(seconds);
    uploadStage(0, pair.i);
    uploadStage(1, pair.j);
    waterUniforms.uMix.value = pair.mix;
    waterUniforms.uAmount.value = amount;
  }
  placeRings(time);
  placeCrossing(time);
  if (!userMoved && shots.length) {
    let shot = shotAt(Math.min(time, 8));
    if (seconds >= 0 && time >= 6 && tracks.some(Boolean)) {
      const chase = chaseAt(seconds);
      const blend = time >= 9 ? 1 : smoothstep((time - 6) / 3);
      shot = {
        pos: shot.pos.lerp(chase.pos, blend),
        target: shot.target.lerp(chase.target, blend)
      };
    }
    const chasing = seconds >= 0 && time >= 9;
    const clearance = groundAt(shot.pos) + (chasing ? 400 : 1400);
    if (shot.pos.y < clearance) shot.pos.y = clearance;
    camera.position.copy(shot.pos);
    if (time >= 12 && time < 14.6) {
      const fade = 1 - (time - 12) / 2.6;
      camera.position.x += Math.sin(time * 42) * 140 * fade;
      camera.position.y += Math.cos(time * 31) * 60 * fade;
    }
    camera.lookAt(shot.target);
    controls.target.copy(shot.target);
  } else {
    controls.update();
  }
  updateRose();
  syncUi(time);
}

function resize() {
  const width = Math.max(1, view.clientWidth);
  const height = Math.max(1, view.clientHeight);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
  labels.setSize(width, height);
}

function tick(now) {
  requestAnimationFrame(tick);
  const visible = !document.hidden && parentVisible;
  if (!visible) {
    lastTick = 0;
    return;
  }
  if (playing && bounds) {
    if (!lastTick) lastTick = now;
    film += Math.min(0.3, ((now - lastTick) / 1000) * 1.35);
    lastTick = now;
    if (film >= DURATION) film = 0;
  } else {
    lastTick = now;
  }
  if (!bounds) return;
  applyFilm(film);
  renderer.render(scene, camera);
  labels.render(scene, camera);
}

function setPlaying(next) {
  playing = next;
  playButton.textContent = playing ? "Pause" : "Play";
  playButton.setAttribute("aria-pressed", playing ? "true" : "false");
  lastTick = 0;
}

slider.max = String(DURATION * 10);
playButton.addEventListener("click", () => setPlaying(!playing));
replayButton.addEventListener("click", () => {
  film = 0;
  userMoved = false;
  setPlaying(true);
});
slider.addEventListener("input", () => {
  film = Number(slider.value) / 10;
  setPlaying(false);
});
window.addEventListener("message", (event) => {
  if (!event.data || event.data.type !== "cts-embed-visible") return;
  parentVisible = Boolean(event.data.visible);
});
window.addEventListener("resize", resize);
new ResizeObserver(() => resize()).observe(view);

async function load() {
  lineEl.textContent = "Loading the valley…";
  const base = new URL("./", window.location.href);
  const [meta, terrainBuf, flowBuf, imagery] = await Promise.all([
    fetch(new URL("bounds.json", base)).then((response) => response.json()),
    fetch(new URL("terrain.bin", base)).then((response) => response.arrayBuffer()),
    fetch(new URL("flow.bin", base)).then((response) => response.arrayBuffer()),
    new Promise((resolve, reject) => {
      new THREE.TextureLoader().load(new URL("imagery.jpg", base).href, resolve, undefined, reject);
    })
  ]);
  bounds = meta;
  dem = new Float32Array(terrainBuf);
  flow = new Uint8Array(flowBuf);
  if (!bounds.flow_rows) {
    bounds.flow_rows = bounds.rows;
    bounds.flow_cols = bounds.cols;
  }
  const cells = bounds.flow_rows * bounds.flow_cols;
  if (flow.length !== cells * bounds.frame_times_s.length || dem.length !== bounds.rows * bounds.cols) {
    throw new Error("terrain files do not match bounds.json");
  }
  waterUniforms.uExag.value = bounds.exaggeration;
  waterUniforms.uTexel.value.set(1 / bounds.flow_cols, 1 / bounds.flow_rows);
  waterUniforms.uSpan.value.set(bounds.width_m, bounds.height_m);
  resizeTextures();
  buildStages();
  buildTerrain(imagery);
  buildProps();
  resize();
  const scrub = params.get("t");
  if (scrub !== null && scrub !== "") {
    film = Math.min(DURATION, Math.max(0, Number(scrub)));
    setPlaying(false);
  } else if (reduced) {
    film = 47;
    setPlaying(false);
  } else {
    setPlaying(true);
  }
  applyFilm(film);
  renderer.render(scene, camera);
  labels.render(scene, camera);
}

load().catch(() => {
  lineEl.textContent = "The valley did not load. Refresh the page.";
});
requestAnimationFrame(tick);
resize();
