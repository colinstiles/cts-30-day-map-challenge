"""Day 27 — New tool: HUC 06020001 in forge3d.

The frame is the USGS Watershed Boundary Dataset 8-digit unit
06020001, Middle Tennessee-Chickamauga. Elevations are USGS 3DEP.
Lakes, reservoirs, and the stream network are USGS NHD, rasterized
to a water mask and shaded by forge3d.

Cells outside the watershed are left non-finite so the model is the
basin, not a rectangle. The gallery sheet is one oblique frame. The
orbit is the same camera turned through a full circle.

The GeoTIFF and the hydrography GeoJSON are cached under data/raw/,
which is gitignored. A corporate proxy may need the local Zscaler CA
on SSL_CERT_FILE. Do not disable TLS verification.

Run from the repository root:

    python scripts/2026/build_day27_forge.py
    python scripts/2026/build_day27_forge.py --refresh
    python scripts/2026/build_day27_forge.py --frames 24
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import _env  # noqa: F401  (loads .env for SSL_CERT_FILE / REQUESTS_CA_BUNDLE)
from build_day05_terrain import meters_per_degree, read_usgs_elevation

HUC8 = "06020001"
WBD_LAYER = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query"
NHD_FLOW = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6/query"
NHD_WATER = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/12/query"
EXPORT_URL = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer/exportImage"
)

# Perennial stream, artificial path through a waterbody, and canal.
FLOW_CODES = (46006, 55800, 33600)
# Lake/pond and reservoir. Swamps stay on the terrain.
WATER_TYPES = (390, 436)
MIN_WATER_KM2 = 0.05
MIN_FLOW_KM = 1.0
PAGE = 2000

MAX_CELLS = 680
TARGET_CELL_M = 160.0
PAD_FRACTION = 0.012
HERO_AZIMUTH = 208.0
FRAME_COUNT = 24
FRAME_SIZE = (1200, 900)
HERO_SIZE = (1600, 1200)
# forge3d rejects a camera farther than 65,536 of its world units. The
# basin is wider than that in meters, so the model is scaled down and the
# heights move with it. The shape, including the exaggeration, is unchanged.
DISPLAY_SPAN_M = 48000.0

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DAY = ROOT / "2026" / "day-27"
RAW_HUC = RAW / "day27-huc-06020001.geojson"
RAW_FLOW = RAW / "day27-nhd-flowlines.geojson"
RAW_WATER = RAW / "day27-nhd-waterbodies.geojson"
RAW_DEM = RAW / "day27-3dep-06020001.tif"
MASK_NPY = PROCESSED / "day27-water-mask.npy"
FLY_DIR = PROCESSED / "day27-flythrough"
HERO_PNG = DAY / "day-27.png"
FRAMES = DAY / "frames"
ORBIT_JSON = DAY / "orbit.json"
BOUNDS_JSON = DAY / "bounds.json"

PAPER = (14, 14, 10)


def fetch(url: str, timeout: int, data: bytes | None = None) -> bytes:
    request = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "cts-30-day-map-challenge"},
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:  # noqa: BLE001 -- retry transient National Map failures
            last_error = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"Request failed after retries: {url}") from last_error


def post_query(url: str, params: dict[str, str]) -> dict:
    payload = fetch(url, timeout=180, data=urllib.parse.urlencode(params).encode())
    document = json.loads(payload)
    if document.get("error"):
        raise RuntimeError(document["error"])
    return document


def load_watershed(refresh: bool):
    from shapely.geometry import shape

    RAW.mkdir(parents=True, exist_ok=True)
    if refresh or not RAW_HUC.exists() or RAW_HUC.stat().st_size == 0:
        document = post_query(
            WBD_LAYER,
            {
                "where": f"huc8='{HUC8}'",
                "outFields": "huc8,name,areasqkm,states",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "geojson",
            },
        )
        RAW_HUC.write_text(json.dumps(document), encoding="utf-8")
    document = json.loads(RAW_HUC.read_text(encoding="utf-8"))
    features = document.get("features") or []
    if len(features) != 1:
        raise RuntimeError(f"Expected one HUC8 feature, found {len(features)}.")
    feature = features[0]
    props = feature.get("properties") or {}
    if props.get("huc8") != HUC8:
        raise RuntimeError(f"WBD returned {props.get('huc8')}, expected {HUC8}.")
    from shapely import make_valid

    geom = make_valid(shape(feature["geometry"]))
    if geom.geom_type == "GeometryCollection":
        from shapely import unary_union

        polygons = [part for part in geom.geoms if part.geom_type.endswith("Polygon")]
        geom = unary_union(polygons)
    if geom.is_empty or not geom.geom_type.endswith("Polygon"):
        raise RuntimeError(f"Watershed geometry is {geom.geom_type}.")
    minx, miny, maxx, maxy = geom.bounds
    if not (-86.2 < minx < -84 and 34 < miny < 36.2):
        raise RuntimeError(f"Watershed bounds are outside the Tennessee basin: {geom.bounds}.")
    print(
        f"watershed {props.get('name')} {props.get('areasqkm')} km2 {props.get('states')}",
        flush=True,
    )
    return geom, props


def frame_bounds(geom) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = geom.bounds
    pad_x = (maxx - minx) * PAD_FRACTION
    pad_y = (maxy - miny) * PAD_FRACTION
    return minx - pad_x, miny - pad_y, maxx + pad_x, maxy + pad_y


def choose_cell(west: float, south: float, east: float, north: float) -> float:
    m_lat, m_lon = meters_per_degree((south + north) / 2)
    long_m = max((east - west) * m_lon, (north - south) * m_lat)
    return max(TARGET_CELL_M, long_m / MAX_CELLS)


def download_dem(west: float, south: float, east: float, north: float, cell_m: float) -> None:
    if RAW_DEM.exists() and RAW_DEM.stat().st_size > 1000:
        return
    m_lat, m_lon = meters_per_degree((south + north) / 2)
    cols = max(2, min(MAX_CELLS, round((east - west) * m_lon / cell_m)))
    rows = max(2, min(MAX_CELLS, round((north - south) * m_lat / cell_m)))
    query = (
        f"?bbox={west},{south},{east},{north}&bboxSR=4326&imageSR=4326"
        f"&size={cols},{rows}&format=tiff&pixelType=F32"
        "&interpolation=RSP_BilinearInterpolation&f=image"
    )
    print(f"downloading 3DEP {cols}x{rows}", flush=True)
    payload = fetch(EXPORT_URL + query, timeout=240)
    if not payload.startswith(b"II"):
        raise RuntimeError(f"3DEP did not return a TIFF ({len(payload)} bytes).")
    RAW_DEM.write_bytes(payload)


def paged_features(url: str, where: str, bounds: tuple[float, float, float, float], fields: str) -> list[dict]:
    try:
        return _paged_features(url, where, bounds, fields)
    except RuntimeError:
        if "areasqkm" not in fields:
            raise
        print("retrying waterbody query without areasqkm", flush=True)
        return _paged_features(url, where, bounds, fields.replace(",areasqkm", ""))


def _paged_features(url: str, where: str, bounds: tuple[float, float, float, float], fields: str) -> list[dict]:
    west, south, east, north = bounds
    geometry = json.dumps(
        {
            "xmin": west,
            "ymin": south,
            "xmax": east,
            "ymax": north,
            "spatialReference": {"wkid": 4326},
        }
    )
    features: list[dict] = []
    offset = 0
    while True:
        document = post_query(
            url,
            {
                "where": where,
                "geometry": geometry,
                "geometryType": "esriGeometryEnvelope",
                "spatialRel": "esriSpatialRelIntersects",
                "inSR": "4326",
                "outFields": fields,
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "geojson",
                "resultOffset": str(offset),
                "resultRecordCount": str(PAGE),
                "maxAllowableOffset": "0.0007",
                "geometryPrecision": "5",
            },
        )
        page = document.get("features") or []
        features.extend(page)
        print(f"  {url.rsplit('/', 2)[-2]} +{len(page)} (total {len(features)})", flush=True)
        if len(page) < PAGE:
            break
        offset += PAGE
    return features


def clip_to_basin(frame, geom, kinds: tuple[str, ...]):
    """Clip to the watershed. A grid size avoids NHD topology errors."""
    from shapely import intersection

    if frame.empty:
        return frame
    frame = frame.copy()
    frame["geometry"] = frame.geometry.make_valid()
    frame["geometry"] = intersection(frame.geometry.values, geom, grid_size=1e-7)
    frame = frame.explode(index_parts=False)
    frame = frame[frame.geometry.type.isin(kinds)]
    return frame[~frame.geometry.is_empty]


def load_hydro(refresh: bool, geom, bounds: tuple[float, float, float, float]):
    import geopandas as gpd

    west, south, east, north = bounds
    # Reach codes begin with the HUC8. The envelope also clips the query
    # to this basin so the national layers are not scanned end to end.
    flow_where = (
        f"reachcode LIKE '{HUC8}%' AND fcode IN {FLOW_CODES} AND lengthkm >= {MIN_FLOW_KM}"
    )
    water_where = (
        f"reachcode LIKE '{HUC8}%' AND ftype IN {WATER_TYPES} AND areasqkm >= {MIN_WATER_KM2}"
    )
    if refresh or not RAW_FLOW.exists():
        print("querying NHD flowlines", flush=True)
        features = paged_features(
            NHD_FLOW,
            flow_where,
            (west, south, east, north),
            "gnis_name,fcode,lengthkm,reachcode",
        )
        RAW_FLOW.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    if refresh or not RAW_WATER.exists():
        print("querying NHD waterbodies", flush=True)
        features = paged_features(
            NHD_WATER,
            water_where,
            (west, south, east, north),
            "gnis_name,ftype,fcode,reachcode,areasqkm",
        )
        RAW_WATER.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")

    flow = gpd.read_file(RAW_FLOW)
    water = gpd.read_file(RAW_WATER)
    if flow.crs is None:
        flow = flow.set_crs(4326)
    if water.crs is None:
        water = water.set_crs(4326)
    flow = clip_to_basin(flow, geom, ("LineString", "MultiLineString"))
    water = clip_to_basin(water, geom, ("Polygon", "MultiPolygon"))
    if not water.empty:
        lat = (south + north) / 2
        m_lat, m_lon = meters_per_degree(lat)
        from shapely import area as geom_area

        area_km2 = geom_area(water.geometry.values) * m_lon * m_lat / 1_000_000
        water = water[area_km2 >= MIN_WATER_KM2]
    print(f"hydro flowlines {len(flow)} waterbodies {len(water)}", flush=True)
    return flow, water


def pixel_mask(elevation: np.ndarray, geom, west: float, south: float, east: float, north: float) -> np.ndarray:
    from shapely import contains_xy

    rows, cols = elevation.shape
    lons = west + (np.arange(cols) + 0.5) * (east - west) / cols
    lats = north - (np.arange(rows) + 0.5) * (north - south) / rows
    lon, lat = np.meshgrid(lons, lats)
    # Pixel centers. The watershed outline is the model edge.
    return contains_xy(geom, lon, lat)


def to_pixels(xs, ys, west, south, east, north, cols, rows):
    col = (np.asarray(xs) - west) / (east - west) * cols
    row = (north - np.asarray(ys)) / (north - south) * rows
    return list(zip(col.tolist(), row.tolist()))


def burn_water(flow, water, west, south, east, north, rows: int, cols: int) -> np.ndarray:
    """Raster water mask, north-up, aligned to the elevation grid."""
    image = Image.new("L", (cols, rows), 0)
    draw = ImageDraw.Draw(image)

    def paint_polygon(poly) -> None:
        shell = to_pixels(poly.exterior.xy[0], poly.exterior.xy[1], west, south, east, north, cols, rows)
        if len(shell) >= 3:
            draw.polygon(shell, fill=255)
        for hole in poly.interiors:
            ring = to_pixels(hole.xy[0], hole.xy[1], west, south, east, north, cols, rows)
            if len(ring) >= 3:
                draw.polygon(ring, fill=0)

    if water is not None and not water.empty:
        for geom in water.geometry:
            if geom.geom_type == "Polygon":
                paint_polygon(geom)
            elif geom.geom_type == "MultiPolygon":
                for part in geom.geoms:
                    paint_polygon(part)

    def paint_line(line, width: int) -> None:
        if line.geom_type == "MultiLineString":
            for part in line.geoms:
                paint_line(part, width)
            return
        if line.geom_type != "LineString" or len(line.coords) < 2:
            return
        xs, ys = zip(*((x, y) for x, y in line.coords))
        pts = to_pixels(xs, ys, west, south, east, north, cols, rows)
        draw.line(pts, fill=255, width=width)

    if flow is not None and not flow.empty:
        for _, row in flow.iterrows():
            name = str(row.get("gnis_name") or "")
            length = float(row.get("lengthkm") or 0)
            width = 1
            if "Tennessee" in name or length >= 25:
                width = 3
            elif length >= 8:
                width = 2
            paint_line(row.geometry, width)

    mask = np.asarray(image, dtype=np.float32) / 255.0
    return np.ascontiguousarray(mask)


def exaggeration(z: np.ndarray, cell_m: float) -> float:
    valid = z[np.isfinite(z)]
    relief = float(valid.max() - valid.min())
    span = max(z.shape) * cell_m
    if relief <= 0:
        return 1.0
    # A regional basin reads when the vertical is a few times the true relief,
    # and still short of the width.
    return float(np.clip(0.22 * span / relief, 2.0, 4.5))


def make_scene(z: np.ndarray, cell_m: float, exag: float, azimuth: float, size: tuple[int, int], path: Path):
    import forge3d as f3d

    rows, cols = z.shape
    # Uniform scale keeps the basin inside the renderer's world limit.
    scale = DISPLAY_SPAN_M / (max(rows, cols) * cell_m)
    shown = np.ascontiguousarray(z * scale, dtype=np.float32)
    step = cell_m * scale
    diagonal = max(rows, cols) * step
    scene = f3d.MapScene(
        terrain=f3d.TerrainSource(
            data=shown,
            # Local north-up meter grid. UTM 16N names the frame. The
            # in-memory samples are not reprojected.
            crs="EPSG:32616",
            metadata={
                "width": cols,
                "height": rows,
                "resolution": [step, step],
                "water": {"enabled": True, "mask_path": str(MASK_NPY)},
            },
            nodata_policy="preserve",
        ),
        camera=f3d.OrbitCamera(
            target=(0.0, 0.0, float(np.nanmean(shown))),
            distance=diagonal * 0.98,
            azimuth_deg=azimuth,
            elevation_deg=36.0,
            fov_deg=46.0,
        ),
        lighting=f3d.LightingPreset(
            name="default",
            intensity=1.28,
            settings={
                "exaggeration": exag,
                "sun": {"azimuth_deg": 318.0, "elevation_deg": 32.0},
                "camera": {"camera_mode": "mesh:zup"},
                "pom": False,
            },
        ),
        output=f3d.OutputSpec(width=size[0], height=size[1], path=str(path), samples=1),
    )
    return scene


def flatten(path: Path, dest: Path, jpeg: bool) -> None:
    image = Image.open(path).convert("RGBA")
    plate = Image.new("RGB", image.size, PAPER)
    plate.paste(image, mask=image.getchannel("A"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    if jpeg:
        plate.save(dest, quality=84, optimize=True)
    else:
        plate.save(dest, optimize=True)


def render(z: np.ndarray, cell_m: float, exag: float, frames: int) -> None:
    import forge3d as f3d

    if not f3d.has_gpu():
        raise RuntimeError("forge3d did not find a GPU.")
    MASK_NPY.parent.mkdir(parents=True, exist_ok=True)
    FLY_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    azimuths = [i * (360.0 / frames) for i in range(frames)]
    scenes = [
        make_scene(z, cell_m, exag, azimuth, FRAME_SIZE, FLY_DIR / f"frame_{i:08d}.png")
        for i, azimuth in enumerate(azimuths)
    ]
    print(f"rendering {frames} forge3d frames", flush=True)
    f3d.render_flythrough(scenes, base_seed=27, samples=1, out_dir=FLY_DIR)
    for i in range(frames):
        source = FLY_DIR / f"frame_{i:08d}.png"
        if not source.exists() or source.stat().st_size < 1000:
            raise RuntimeError(f"forge3d did not write {source.name}.")
        flatten(source, FRAMES / f"frame-{i:02d}.jpg", jpeg=True)
    hero_src = FLY_DIR / "hero.png"
    hero = make_scene(z, cell_m, exag, HERO_AZIMUTH, HERO_SIZE, hero_src)
    report = hero.validate()
    if report.render_blocked(hero.render_policy):
        raise RuntimeError(f"forge3d blocked the hero frame: {report}")
    print("rendering hero frame", flush=True)
    hero.render()
    flatten(hero_src, HERO_PNG, jpeg=False)
    ORBIT_JSON.write_text(
        json.dumps(
            {
                "frames": frames,
                "pattern": "frames/frame-{i}.jpg",
                "azimuth0": 0,
                "azimuthStep": 360.0 / frames,
                "heroAzimuth": HERO_AZIMUTH,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Ignore cached WBD, NHD, and 3DEP.")
    parser.add_argument("--frames", type=int, default=FRAME_COUNT, help="Orbit frames.")
    parser.add_argument("--no-render", action="store_true", help="Prepare the grids and skip forge3d.")
    args = parser.parse_args()
    if args.frames < 8:
        raise SystemExit("--frames must be at least 8.")

    geom, props = load_watershed(args.refresh)
    west, south, east, north = frame_bounds(geom)
    cell_m = choose_cell(west, south, east, north)
    if args.refresh and RAW_DEM.exists():
        RAW_DEM.unlink()
    download_dem(west, south, east, north, cell_m)
    elevation, west, south, east, north = read_usgs_elevation(RAW_DEM.read_bytes())
    rows, cols = elevation.shape
    m_lat, m_lon = meters_per_degree((south + north) / 2)
    cell_m = (((east - west) * m_lon / cols) + ((north - south) * m_lat / rows)) / 2
    inside = pixel_mask(elevation, geom, west, south, east, north)
    if int(inside.sum()) < 100:
        raise RuntimeError("The watershed mask covers almost no 3DEP cells.")
    kept = elevation.astype(np.float32)
    kept[~inside] = np.nan
    valid = kept[np.isfinite(kept)]
    flow, water = load_hydro(args.refresh, geom, (west, south, east, north))
    mask = burn_water(flow, water, west, south, east, north, *kept.shape)
    mask[~inside] = 0
    PROCESSED.mkdir(parents=True, exist_ok=True)
    np.save(MASK_NPY, np.ascontiguousarray(mask, dtype=np.float32))
    exag = exaggeration(kept, cell_m)
    rows, cols = kept.shape
    print(
        f"grid {cols}x{rows} cell {cell_m:.0f} m  "
        f"elev {valid.min():.0f}–{valid.max():.0f} m  "
        f"water {int((mask > 0).sum())} cells  exaggeration {exag:.2f}",
        flush=True,
    )
    DAY.mkdir(parents=True, exist_ok=True)
    BOUNDS_JSON.write_text(
        json.dumps(
            {
                "huc8": HUC8,
                "name": props.get("name"),
                "states": props.get("states"),
                "areasqkm": props.get("areasqkm"),
                "bbox": [west, south, east, north],
                "cell_m": cell_m,
                "grid": [cols, rows],
                "elevation_m": [float(valid.min()), float(valid.max())],
                "exaggeration": exag,
                "display_span_m": DISPLAY_SPAN_M,
                "water_cells": int((mask > 0).sum()),
                "flowlines": int(len(flow)),
                "waterbodies": int(len(water)),
                "crs": "EPSG:4326 samples on a local north-up meter grid labeled EPSG:32616",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if args.no_render:
        print("skipping forge3d", flush=True)
        return
    render(kept, cell_m, exag, args.frames)
    print(f"wrote {HERO_PNG.relative_to(ROOT)} and {args.frames} frames", flush=True)


if __name__ == "__main__":
    main()
