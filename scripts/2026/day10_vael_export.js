// Rebuild Vael's reusable frame and GeoJSON from assets/js/vael-world.js.
// Coordinates are Vael degrees (VAEL:2026), not Earth.
const fs = require("fs");
const path = require("path");

const Vael = require("../assets/js/vael-world.js");

const root = path.join(__dirname, "..");
const outDir = path.join(root, "2026", "10_prompting");
const geoPath = path.join(outDir, "vael.geojson");
const framePath = path.join(outDir, "vael-frame.json");

if (process.argv.includes("--ascii")) {
  console.log(Vael.ascii(92, 34));
  console.log("");
}

const report = Vael.audit();
report.lines.forEach((line) => console.log(line));

const collection = Vael.featureCollection();
const frame = Vael.frame();
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(geoPath, JSON.stringify(collection));
fs.writeFileSync(framePath, JSON.stringify(frame, null, 2) + "\n");

const bytes = fs.statSync(geoPath).size;
console.log("wrote " + path.relative(root, geoPath) + " (" + bytes + " bytes)");
console.log("wrote " + path.relative(root, framePath));
console.log("extent " + JSON.stringify(frame.mappedExtent));

if (!report.ok) process.exit(1);
