"""Build the Day 5 terrain grid for the Cherokee fire-tower viewshed.

The observer is Pinnacle Mountain Fire Tower on Buffalo Mountain in the
Cherokee National Forest. An earlier plan coordinate, 36.20845°N
82.38204°W, sits about 1.4 km down the slope; the lookout is the summit.

Elevations are sampled from USGS 3DEP in EPSG:4326 and resampled to a
local equirectangular grid in meters, centered on the tower. The viewshed
is a radial line-of-sight on a 30 m grid. Earth curvature is removed and
refraction uses k = 0.13. The page draws a coarser mesh and a baked mask.

The GeoTIFF is cached under data/raw/, which is gitignored. A corporate
proxy may need the local Zscaler CA on SSL_CERT_FILE. Do not disable TLS
verification.

Run from the repository root:

    python scripts/build_day05_terrain.py
"""

from __future__ import annotations

import base64
import json
import math
import struct
import urllib.request
from pathlib import Path

import numpy as np

import _env  # noqa: F401  (loads .env for SSL_CERT_FILE / REQUESTS_CA_BUNDLE)

# National Historic Lookout Register coordinate for Pinnacle Fire Tower.
TOWER_LAT = 36.21712
TOWER_LON = -82.37060
RADIUS_M = 27_000
MESH_M = 90
VIEW_M = 30
PAD_M = 1_500
# 40 ft steel tower plus about 1.7 m of eye height on the platform.
PLATFORM_HEIGHT_M = 14.0
GROUND_HEIGHT_M = 1.7
EARTH_RADIUS_M = 6_378_137.0
REFRACTION_K = 0.13

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "day05-3dep-pinnacle.tif"
OUT_PATH = ROOT / "assets" / "js" / "day05-terrain.js"
EXPORT_URL = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer/exportImage"
)

# Landmarks used as labels. Elevations are filled from the DEM at build time.
# Summits are the 3DEP high point, not a guidebook coordinate that misses the crest.
PLACES = [
    {"name": "Johnson City", "lat": 36.3134, "lon": -82.3535},
    {"name": "Erwin", "lat": 36.1451, "lon": -82.4168},
    {"name": "Unicoi", "lat": 36.2160, "lon": -82.3343},
    {"name": "Unaka Mountain", "lat": 36.1338, "lon": -82.2970},
    {"name": "Roan High Knob", "lat": 36.1045, "lon": -82.1225},
]


def meters_per_degree(lat: float) -> tuple[float, float]:
    """Return meters per degree of latitude and longitude."""
    m_lat = 111_132.92 - 559.82 * math.cos(2 * math.radians(lat))
    m_lon = 111_412.84 * math.cos(math.radians(lat))
    return m_lat, m_lon


def _tiff_values(data: bytes, tags: dict[int, tuple[int, int, int]], tag: int) -> tuple:
    type_size = {3: 2, 4: 4, 12: 8}
    fmt_char = {3: "H", 4: "I", 12: "d"}
    typ, count, valoff = tags[tag]
    nbytes = count * type_size[typ]
    fmt = "<" + fmt_char[typ] * count
    if nbytes <= 4:
        raw = struct.pack("<I", valoff)[:nbytes]
        return struct.unpack(fmt, raw)
    return struct.unpack_from(fmt, data, valoff)


def read_usgs_elevation(data: bytes) -> tuple[np.ndarray, float, float, float, float]:
    """Read an uncompressed tiled float32 3DEP GeoTIFF.

    The array is north-up. Edges are the outer edges of the raster, read
    from the GeoTIFF tiepoint rather than from the requested bbox.
    """
    if data[:2] != b"II" or struct.unpack_from("<H", data, 2)[0] != 42:
        raise ValueError("Expected a little-endian classic TIFF from 3DEP.")
    ifd = struct.unpack_from("<I", data, 4)[0]
    ntags = struct.unpack_from("<H", data, ifd)[0]
    tags: dict[int, tuple[int, int, int]] = {}
    for i in range(ntags):
        tag, typ, count, valoff = struct.unpack_from("<HHII", data, ifd + 2 + 12 * i)
        tags[tag] = (typ, count, valoff)

    if _tiff_values(data, tags, 259)[0] != 1:
        raise ValueError("Expected an uncompressed 3DEP TIFF.")
    if _tiff_values(data, tags, 339)[0] != 3:
        raise ValueError("Expected 32-bit float elevation samples.")

    width = _tiff_values(data, tags, 256)[0]
    height = _tiff_values(data, tags, 257)[0]
    tile_w = _tiff_values(data, tags, 322)[0]
    tile_h = _tiff_values(data, tags, 323)[0]
    offsets = _tiff_values(data, tags, 324)
    tiles_x = (width + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h
    if len(offsets) != tiles_x * tiles_y:
        raise ValueError("TIFF tile count does not match the image size.")

    grid = np.empty((height, width), dtype=np.float32)
    tile_bytes = tile_w * tile_h * 4
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            start = offsets[ty * tiles_x + tx]
            tile = np.frombuffer(data[start : start + tile_bytes], dtype="<f4")
            tile = tile.reshape(tile_h, tile_w)
            r0 = ty * tile_h
            c0 = tx * tile_w
            r1 = min(r0 + tile_h, height)
            c1 = min(c0 + tile_w, width)
            grid[r0:r1, c0:c1] = tile[: r1 - r0, : c1 - c0]

    scale_x, scale_y = _tiff_values(data, tags, 33550)[:2]
    tie_i, tie_j, _tie_k, tie_x, tie_y, _tie_z = _tiff_values(data, tags, 33922)
    west = tie_x - tie_i * scale_x
    north = tie_y + tie_j * scale_y
    east = west + width * scale_x
    south = north - height * scale_y
    return grid, west, south, east, north


def download_dem(west: float, south: float, east: float, north: float) -> bytes:
    m_lat, m_lon = meters_per_degree((south + north) / 2)
    cols = max(2, round((east - west) * m_lon / VIEW_M))
    rows = max(2, round((north - south) * m_lat / VIEW_M))
    query = (
        f"?bbox={west},{south},{east},{north}&bboxSR=4326&imageSR=4326"
        f"&size={cols},{rows}&format=tiff&pixelType=F32"
        "&interpolation=RSP_BilinearInterpolation&f=image"
    )
    request = urllib.request.Request(
        EXPORT_URL + query,
        headers={"User-Agent": "cts-30-day-map-challenge"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
        content_type = response.headers.get("Content-Type", "")
    if not payload.startswith(b"II") or "tiff" not in content_type:
        raise RuntimeError(f"3DEP did not return a TIFF ({content_type}, {len(payload)} bytes).")
    return payload


def sample_grid(
    dem: np.ndarray,
    west: float,
    north: float,
    scale_x: float,
    scale_y: float,
    n: int,
    cell_m: float,
) -> np.ndarray:
    """Bilinear sample of a north-up DEM onto the tower-centered metric grid."""
    center = (n - 1) / 2
    m_lat, m_lon = meters_per_degree(TOWER_LAT)
    east_m = (np.arange(n) - center) * cell_m
    north_m = (center - np.arange(n)) * cell_m
    lon = TOWER_LON + east_m / m_lon
    lat = TOWER_LAT + north_m / m_lat
    # Pixel centers are half a pixel in from the outer edges.
    col = (lon - west) / scale_x - 0.5
    row = (north - lat) / scale_y - 0.5
    if col.min() < 0 or row.min() < 0 or col.max() > dem.shape[1] - 1 or row.max() > dem.shape[0] - 1:
        raise ValueError("Metric grid extends outside the downloaded DEM.")
    c0 = np.floor(col).astype(np.int32)
    r0 = np.floor(row).astype(np.int32)
    c0 = np.clip(c0, 0, dem.shape[1] - 2)
    r0 = np.clip(r0, 0, dem.shape[0] - 2)
    dc = col - c0
    dr = (row - r0)[:, None]
    c0g = c0[None, :]
    r0g = r0[:, None]
    dcg = dc[None, :]
    z00 = dem[r0g, c0g]
    z01 = dem[r0g, c0g + 1]
    z10 = dem[r0g + 1, c0g]
    z11 = dem[r0g + 1, c0g + 1]
    return (z00 * (1 - dr) * (1 - dcg) + z01 * (1 - dr) * dcg + z10 * dr * (1 - dcg) + z11 * dr * dcg).astype(
        np.float32
    )


def mesh_viewshed(fine: np.ndarray, height_m: float, fine_m: float, step: int) -> np.ndarray:
    """Viewshed of every `step` cell, sampled along the fine grid.

    A point is in sight when its slope from the eye is at least the slope to
    every nearer sample. Curvature uses an effective Earth radius that includes
    refraction. The sample inside the target cell is not allowed to hide it.
    """
    n = fine.shape[0]
    if fine.shape != (n, n) or n % 2 == 0 or (n - 1) % step != 0:
        raise ValueError("Viewshed expects an odd square grid that the mesh divides.")
    center = (n - 1) // 2
    n_mesh = (n - 1) // step + 1
    z_obs = float(fine[center, center]) + height_m
    earth = EARTH_RADIUS_M / (1.0 - REFRACTION_K)
    mesh_r, mesh_c = np.indices((n_mesh, n_mesh))
    keep = ~((mesh_r == n_mesh // 2) & (mesh_c == n_mesh // 2))
    mesh_r = mesh_r[keep]
    mesh_c = mesh_c[keep]
    fine_r = mesh_r * step
    fine_c = mesh_c * step
    dr = fine_r - center
    dc = fine_c - center
    steps = np.maximum(np.abs(dr), np.abs(dc)).astype(np.int32)
    target_dist = np.hypot(dr, dc) * fine_m

    seen = np.empty(mesh_r.shape[0], dtype=bool)
    batch = 8192
    for start in range(0, mesh_r.shape[0], batch):
        stop = min(start + batch, mesh_r.shape[0])
        seen[start:stop] = _viewshed_batch(
            fine,
            dr[start:stop],
            dc[start:stop],
            steps[start:stop],
            target_dist[start:stop],
            fine_r[start:stop],
            fine_c[start:stop],
            z_obs,
            fine_m,
            earth,
            center,
        )

    visible = np.zeros((n_mesh, n_mesh), dtype=bool)
    visible[n_mesh // 2, n_mesh // 2] = True
    visible[mesh_r, mesh_c] = seen
    return visible


def _viewshed_batch(
    fine: np.ndarray,
    dr: np.ndarray,
    dc: np.ndarray,
    steps: np.ndarray,
    target_dist: np.ndarray,
    fine_r: np.ndarray,
    fine_c: np.ndarray,
    z_obs: float,
    fine_m: float,
    earth: float,
    center: int,
) -> np.ndarray:
    n = fine.shape[0]
    max_slope = np.full(dr.shape[0], -1e9)
    limit = int(steps.max())
    for s in range(1, limit):
        active = s < steps
        if not np.any(active):
            break
        rr = np.rint(center + dr * (s / np.maximum(steps, 1))).astype(np.int32)
        cc = np.rint(center + dc * (s / np.maximum(steps, 1))).astype(np.int32)
        np.clip(rr, 0, n - 1, out=rr)
        np.clip(cc, 0, n - 1, out=cc)
        dist = np.hypot(rr - center, cc - center) * fine_m
        # The last sample falls in the target cell and must not hide it.
        active &= target_dist - dist > fine_m
        safe = np.maximum(dist, 1.0)
        slope = (fine[rr, cc] - (safe * safe) / (2 * earth) - z_obs) / safe
        update = active & (slope > max_slope)
        max_slope[update] = slope[update]
    safe = np.maximum(target_dist, 1.0)
    slope = (fine[fine_r, fine_c] - (safe * safe) / (2 * earth) - z_obs) / safe
    return slope >= max_slope


def pack_bits(mask: np.ndarray) -> str:
    flat = np.ascontiguousarray(mask, dtype=np.uint8).ravel()
    out = np.zeros((flat.size + 7) // 8, dtype=np.uint8)
    index = np.arange(flat.size)
    np.add.at(out, index // 8, flat << (index % 8))
    return base64.b64encode(out.tobytes()).decode("ascii")


PEAKS = {"Unaka Mountain", "Roan High Knob"}


def place_records(elev: np.ndarray, visible: np.ndarray, cell_m: float) -> list[dict]:
    """Label towns at the given coordinate. Slide a peak onto the crest cell that is in sight."""
    n = elev.shape[0]
    center = (n - 1) / 2
    m_lat, m_lon = meters_per_degree(TOWER_LAT)
    records = []
    for place in PLACES:
        east_m = (place["lon"] - TOWER_LON) * m_lon
        north_m = (place["lat"] - TOWER_LAT) * m_lat
        if math.hypot(east_m, north_m) > RADIUS_M * math.sqrt(2):
            continue
        c = round(center + east_m / cell_m)
        r = round(center - north_m / cell_m)
        r = min(max(r, 0), n - 1)
        c = min(max(c, 0), n - 1)
        if place["name"] in PEAKS and not visible[r, c]:
            r, c = _visible_crest(elev, visible, r, c)
        lat = TOWER_LAT + (center - r) * cell_m / m_lat
        lon = TOWER_LON + (c - center) * cell_m / m_lon
        records.append(
            {
                "name": place["name"],
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "elev": round(float(elev[r, c])),
                "seen": bool(visible[r, c]),
            }
        )
    return records


def _visible_crest(elev: np.ndarray, visible: np.ndarray, r: int, c: int) -> tuple[int, int]:
    """Nearest in-sight cell within about 500 m that is still on this summit."""
    best = (r, c)
    best_dist = 10_000
    summit = float(elev[r, c])
    for rr in range(max(0, r - 6), min(elev.shape[0], r + 7)):
        for cc in range(max(0, c - 6), min(elev.shape[1], c + 7)):
            if not visible[rr, cc] or float(elev[rr, cc]) < summit - 15:
                continue
            dist = (rr - r) ** 2 + (cc - c) ** 2
            if dist < best_dist:
                best = (rr, cc)
                best_dist = dist
    return best


def write_terrain(
    mesh: np.ndarray,
    masks: dict[str, np.ndarray],
    ground: float,
    places: list[dict],
) -> None:
    rounded = np.rint(mesh).astype(np.uint16)
    if int(rounded.min()) < 0 or int(rounded.max()) > 4000:
        raise ValueError(f"Elevation outside 0–4000 m: {int(rounded.min())}–{int(rounded.max())}")
    payload = {
        "name": "Pinnacle Mountain Fire Tower",
        "lat": TOWER_LAT,
        "lon": TOWER_LON,
        "n": int(mesh.shape[0]),
        "cell": MESH_M,
        "radius": RADIUS_M,
        "viewCell": VIEW_M,
        "ground": round(ground, 1),
        "heights": {"ground": GROUND_HEIGHT_M, "platform": PLATFORM_HEIGHT_M},
        "refractionK": REFRACTION_K,
        "elev": base64.b64encode(np.ascontiguousarray(rounded).tobytes()).decode("ascii"),
        "masks": {key: pack_bits(mask) for key, mask in masks.items()},
        "places": places,
    }
    body = (
        "// Generated by scripts/build_day05_terrain.py. Do not edit by hand.\n"
        "// elev: uint16 meters, row 0 north. masks: one bit per cell, 1 = in sight.\n"
        "window.DAY05_TERRAIN = "
        + json.dumps(payload, separators=(",", ":"))
        + ";\n"
    )
    OUT_PATH.write_text(body, encoding="utf-8")


def self_check() -> None:
    """Flat ground is all visible, and a ridge hides the land behind it."""
    flat = np.zeros((11, 11), dtype=np.float32)
    if not mesh_viewshed(flat, 2, 100, 1).all():
        raise RuntimeError("Flat-ground viewshed self-check failed.")
    ridge = np.zeros((11, 11), dtype=np.float32)
    ridge[2, :] = 80
    seen = mesh_viewshed(ridge, 2, 100, 1)
    if not seen[2, 5] or seen[0, 5] or not seen[8, 5]:
        raise RuntimeError("Ridge viewshed self-check failed.")


def main() -> None:
    self_check()
    m_lat, m_lon = meters_per_degree(TOWER_LAT)
    pad_lat = (RADIUS_M + PAD_M) / m_lat
    pad_lon = (RADIUS_M + PAD_M) / m_lon
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not RAW_PATH.exists() or RAW_PATH.stat().st_size == 0:
        tiff = download_dem(
            TOWER_LON - pad_lon,
            TOWER_LAT - pad_lat,
            TOWER_LON + pad_lon,
            TOWER_LAT + pad_lat,
        )
        RAW_PATH.write_bytes(tiff)
    else:
        tiff = RAW_PATH.read_bytes()

    dem, west, south, east, north = read_usgs_elevation(tiff)
    scale_x = (east - west) / dem.shape[1]
    scale_y = (north - south) / dem.shape[0]
    n_view = int(RADIUS_M * 2 / VIEW_M) + 1
    n_mesh = int(RADIUS_M * 2 / MESH_M) + 1
    if (n_mesh - 1) * MESH_M != (n_view - 1) * VIEW_M:
        raise ValueError("Mesh grid does not share edges with the viewshed grid.")
    step = MESH_M // VIEW_M
    view = sample_grid(dem, west, north, scale_x, scale_y, n_view, VIEW_M)
    if not np.isfinite(view).all():
        raise ValueError("Sampled elevation grid contains non-finite values.")

    center = (n_view - 1) // 2
    ground = float(view[center, center])
    masks = {}
    for key, height in (("ground", GROUND_HEIGHT_M), ("platform", PLATFORM_HEIGHT_M)):
        masks[key] = mesh_viewshed(view, height, VIEW_M, step)
        print(f"{key:8} {height:4.1f} m  {masks[key].mean():.1%} of the mesh in sight", flush=True)

    mesh = view[::step, ::step]
    if mesh.shape != (n_mesh, n_mesh):
        raise ValueError(f"Unexpected mesh shape {mesh.shape}.")
    places = place_records(mesh, masks["platform"], MESH_M)
    for place in places:
        state = "in sight" if place["seen"] else "hidden"
        print(f"{place['name']:16} {place['elev']:4d} m  {state}")
    write_terrain(mesh, masks, ground, places)
    print(
        f"dem {dem.shape[1]}x{dem.shape[0]}  "
        f"viewshed {n_view}x{n_view} @ {VIEW_M} m  "
        f"mesh {n_mesh}x{n_mesh} @ {MESH_M} m"
    )
    print(f"tower ground {ground:.0f} m  elev {float(mesh.min()):.0f}–{float(mesh.max()):.0f} m")
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
