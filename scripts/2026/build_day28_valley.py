"""Day 28 — Lende Khola debris flood on a real elevation model.

The view is a fine AWS Terrain grid (Mapzen / SRTM) for the north
side of Langtang Lirung. The flood is routed on a coarser copy of
that surface, from the 26 August 2026 release to Rasuwagadhi.
Imagery is Esri World Imagery, lightly shaded by the same grid.

The flood is a 2D diffusive-wave routing: Manning's equation on the
water-surface slope, with a limit so a step cannot overshoot a level
surface. It is not a calibrated debris-flow model and it does not
claim a measured volume. Pits in the DEM are filled so the wave can
follow the valley.

Tiles are cached under data/raw/day28/, which is gitignored. A
corporate proxy may need the local Zscaler CA on SSL_CERT_FILE.
Do not disable TLS verification.

Run from the repository root:

    python scripts/2026/build_day28_valley.py
    python scripts/2026/build_day28_valley.py --refresh
"""

from __future__ import annotations

import argparse
import json
import math
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import numpy as np
import requests
from PIL import Image

import _env  # noqa: F401  (loads .env for SSL_CERT_FILE / REQUESTS_CA_BUNDLE)

# Release and the border crossing. The release is the ice-tongue
# coordinate published from PlanetScope; the bridge is the Friendship
# Bridge at Rasuwagadhi.
RELEASE_LAT = 28.2877
RELEASE_LON = 85.5272
BRIDGE_LAT = 28.2787
BRIDGE_LON = 85.3781
SUMMIT_LAT = 28.2558
SUMMIT_LON = 85.5114

WEST, SOUTH, EAST, NORTH = 85.30, 28.20, 85.58, 28.36
ZOOM = 13
DISPLAY_SIDE = 900
SIM_SIDE = 520
DEPTH_SCALE_M = 1.0
MANNINGS_N = 0.045
VELOCITY_CAP_M_S = 32.0
SIM_SECONDS = 3600.0
SAVE_EVERY_S = 60.0
GRAVITY = 9.81

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "day28"
OUT = ROOT / "2026" / "day-28"
TERRAIN_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
IMAGERY_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "cts-30-day-map-challenge day-28 terrain build"


def mercator_y(lat: float) -> float:
    """Web-Mercator y, radians, increasing north."""
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def tile_lat(y_tile: int, zoom: int) -> float:
    """Latitude of the north edge of a web-mercator tile."""
    n = 2**zoom
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y_tile / n))))


def tile_range(zoom: int) -> tuple[range, range]:
    """Inclusive tile x/y covering the study window."""
    n = 2**zoom
    x0 = math.floor((WEST + 180) / 360 * n)
    x1 = math.floor((EAST + 180) / 360 * n)
    y0 = math.floor((1 - mercator_y(NORTH) / math.pi) / 2 * n)
    y1 = math.floor((1 - mercator_y(SOUTH) / math.pi) / 2 * n)
    return range(x0, x1 + 1), range(y0, y1 + 1)


def fetch(url: str, dest: Path, refresh: bool) -> bytes:
    """Read a cached tile, or download it."""
    if dest.exists() and dest.stat().st_size > 800 and not refresh:
        return dest.read_bytes()
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = SESSION.get(url, timeout=45)
    response.raise_for_status()
    dest.write_bytes(response.content)
    return response.content


def load_tiles(zoom: int, refresh: bool) -> tuple[np.ndarray, np.ndarray, dict]:
    """Mosaic elevation (meters) and RGB imagery. Row 0 is north."""
    xs, ys = tile_range(zoom)
    print(f"tiles z{zoom}: {len(xs)} x {len(ys)}", flush=True)
    jobs = []
    for y in ys:
        for x in xs:
            jobs.append((x, y))

    def one(xy: tuple[int, int]) -> tuple[int, int, np.ndarray, np.ndarray]:
        x, y = xy
        elev_bytes = fetch(
            TERRAIN_URL.format(z=zoom, x=x, y=y),
            RAW / f"terrarium-{zoom}-{x}-{y}.png",
            refresh,
        )
        rgb_bytes = fetch(
            IMAGERY_URL.format(z=zoom, x=x, y=y),
            RAW / f"imagery-{zoom}-{x}-{y}.jpg",
            refresh,
        )
        elev_im = np.asarray(Image.open(BytesIO(elev_bytes)).convert("RGB"), dtype=np.float32)
        elev = elev_im[:, :, 0] * 256.0 + elev_im[:, :, 1] + elev_im[:, :, 2] / 256.0 - 32768.0
        rgb = np.asarray(Image.open(BytesIO(rgb_bytes)).convert("RGB"), dtype=np.uint8)
        return x, y, elev, rgb

    found: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for x, y, elev, rgb in pool.map(one, jobs):
            found[(x, y)] = (elev, rgb)

    tile = 256
    elev = np.zeros((len(ys) * tile, len(xs) * tile), dtype=np.float32)
    rgb = np.zeros((len(ys) * tile, len(xs) * tile, 3), dtype=np.uint8)
    for row, y in enumerate(ys):
        for col, x in enumerate(xs):
            elev_tile, rgb_tile = found[(x, y)]
            elev[row * tile : (row + 1) * tile, col * tile : (col + 1) * tile] = elev_tile
            rgb[row * tile : (row + 1) * tile, col * tile : (col + 1) * tile] = rgb_tile

    north = tile_lat(ys[0], zoom)
    south = tile_lat(ys[-1] + 1, zoom)
    n = 2**zoom
    west = xs[0] / n * 360 - 180
    east = (xs[-1] + 1) / n * 360 - 180
    meta = {"west": west, "south": south, "east": east, "north": north}
    return elev, rgb, meta


def crop_window(elev: np.ndarray, rgb: np.ndarray, meta: dict) -> tuple[np.ndarray, np.ndarray, dict]:
    """Cut the mosaic to the study window. Pixels stay in web mercator."""
    height, width = elev.shape
    north_m = mercator_y(meta["north"])
    south_m = mercator_y(meta["south"])

    def col(lon: float) -> int:
        return int(round((lon - meta["west"]) / (meta["east"] - meta["west"]) * (width - 1)))

    def row(lat: float) -> int:
        y = mercator_y(lat)
        return int(round((north_m - y) / (north_m - south_m) * (height - 1)))

    c0, c1 = sorted((col(WEST), col(EAST)))
    r0, r1 = sorted((row(NORTH), row(SOUTH)))
    c0, r0 = max(0, c0), max(0, r0)
    c1, r1 = min(width - 1, c1), min(height - 1, r1)
    cropped_elev = elev[r0 : r1 + 1, c0 : c1 + 1]
    cropped_rgb = rgb[r0 : r1 + 1, c0 : c1 + 1]
    # Pixel edges of the crop, still mercator-linear in x and in mercator y.
    west = meta["west"] + c0 / (width - 1) * (meta["east"] - meta["west"])
    east = meta["west"] + c1 / (width - 1) * (meta["east"] - meta["west"])
    north = math.degrees(
        math.atan(math.sinh(north_m - r0 / (height - 1) * (north_m - south_m)))
    )
    south = math.degrees(
        math.atan(math.sinh(north_m - r1 / (height - 1) * (north_m - south_m)))
    )
    return cropped_elev, cropped_rgb, {"west": west, "south": south, "east": east, "north": north}


def resize_grid(values: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    """Bilinear resize. Works for a 2D grid or an HxWx3 image."""
    ys = np.linspace(0, values.shape[0] - 1, out_h)
    xs = np.linspace(0, values.shape[1] - 1, out_w)
    y0 = np.floor(ys).astype(np.int32)
    x0 = np.floor(xs).astype(np.int32)
    y1 = np.clip(y0 + 1, 0, values.shape[0] - 1)
    x1 = np.clip(x0 + 1, 0, values.shape[1] - 1)
    wy = (ys - y0)[:, None]
    wx = (xs - x0)[None, :]
    if values.ndim == 2:
        top = values[y0][:, x0] * (1 - wx) + values[y0][:, x1] * wx
        bot = values[y1][:, x0] * (1 - wx) + values[y1][:, x1] * wx
        return (top * (1 - wy) + bot * wy).astype(values.dtype, copy=False)
    channels = []
    for band in range(values.shape[2]):
        plane = values[:, :, band].astype(np.float32)
        top = plane[y0][:, x0] * (1 - wx) + plane[y0][:, x1] * wx
        bot = plane[y1][:, x0] * (1 - wx) + plane[y1][:, x1] * wx
        channels.append(top * (1 - wy) + bot * wy)
    return np.stack(channels, axis=2)


def cell_lonlat(rows: int, cols: int, meta: dict) -> tuple[np.ndarray, np.ndarray]:
    """Latitude for each row (north first) and longitude for each column."""
    north_m = mercator_y(meta["north"])
    south_m = mercator_y(meta["south"])
    fracs = (np.arange(rows) + 0.5) / rows
    lats = np.degrees(np.arctan(np.sinh(north_m - fracs * (north_m - south_m))))
    lons = meta["west"] + (np.arange(cols) + 0.5) / cols * (meta["east"] - meta["west"])
    return lats.astype(np.float64), lons.astype(np.float64)


def fill_voids(elev: np.ndarray) -> np.ndarray:
    """Replace missing Himalayan samples with the mean of valid neighbors."""
    filled = elev.copy()
    bad = (filled < 200) | (filled > 9000) | ~np.isfinite(filled)
    if not bad.any():
        return filled
    filled[bad] = np.nan
    for _ in range(12):
        if not np.isnan(filled).any():
            break
        padded = np.pad(filled, 1, mode="edge")
        stack = np.stack(
            [
                padded[0:-2, 1:-1],
                padded[2:, 1:-1],
                padded[1:-1, 0:-2],
                padded[1:-1, 2:],
            ]
        )
        guess = np.nanmean(stack, axis=0)
        holes = np.isnan(filled) & np.isfinite(guess)
        filled[holes] = guess[holes]
    filled[~np.isfinite(filled)] = float(np.nanmedian(elev[elev > 200]))
    return filled.astype(np.float32)


def fill_depressions(elev: np.ndarray) -> np.ndarray:
    """Priority-flood fill so closed pits cannot trap the wave."""
    import heapq

    rows, cols = elev.shape
    filled = np.full(elev.shape, np.inf, dtype=np.float32)
    seen = np.zeros(elev.shape, dtype=bool)
    heap: list[tuple[float, int, int]] = []
    for i in range(rows):
        for j in (0, cols - 1):
            filled[i, j] = elev[i, j]
            seen[i, j] = True
            heapq.heappush(heap, (float(elev[i, j]), i, j))
    for j in range(cols):
        for i in (0, rows - 1):
            if seen[i, j]:
                continue
            filled[i, j] = elev[i, j]
            seen[i, j] = True
            heapq.heappush(heap, (float(elev[i, j]), i, j))
    neighbors = ((-1, 0), (1, 0), (0, -1), (0, 1))
    while heap:
        height, i, j = heapq.heappop(heap)
        for di, dj in neighbors:
            ni, nj = i + di, j + dj
            if ni < 0 or nj < 0 or ni >= rows or nj >= cols or seen[ni, nj]:
                continue
            seen[ni, nj] = True
            # A few centimeters of tilt keeps filled flats from becoming
            # ponds with no slope for Manning's equation to run on.
            filled[ni, nj] = max(float(elev[ni, nj]), height + 0.02)
            heapq.heappush(heap, (float(filled[ni, nj]), ni, nj))
    return filled


def hillshade(elev: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Unitless shade in 0..1 from a sun in the southeast, 40 degrees up."""
    padded = np.pad(elev, 1, mode="edge")
    dzdx = (padded[1:-1, 2:] - padded[1:-1, 0:-2]) / (2 * dx)
    dzdy = (padded[0:-2, 1:-1] - padded[2:, 1:-1]) / (2 * dy)
    slope = np.arctan(np.hypot(dzdx, dzdy))
    aspect = np.arctan2(dzdy, -dzdx)
    zenith = math.radians(50)
    azimuth = math.radians(135)
    shade = np.cos(zenith) * np.cos(slope) + np.sin(zenith) * np.sin(slope) * np.cos(
        azimuth - aspect
    )
    return np.clip(shade, 0, 1).astype(np.float32)


def colorize(rgb: np.ndarray | None, elev: np.ndarray, shade: np.ndarray) -> np.ndarray:
    """Drape imagery on the hillshade. Fall back to a hypsometric ramp."""
    relief = 0.74 + 0.26 * shade
    if rgb is not None:
        image = rgb.astype(np.float32) * relief[:, :, None]
        return np.clip(image, 0, 255).astype(np.uint8)
    ramp = np.zeros(elev.shape + (3,), dtype=np.float32)
    stops = [
        (1500, (70, 92, 64)),
        (2800, (120, 108, 86)),
        (4200, (150, 142, 132)),
        (5200, (186, 186, 188)),
        (6500, (246, 246, 248)),
    ]
    for index in range(len(stops) - 1):
        z0, c0 = stops[index]
        z1, c1 = stops[index + 1]
        weight = np.clip((elev - z0) / (z1 - z0), 0, 1)
        band = (elev >= z0) & (elev <= z1)
        for channel in range(3):
            color = c0[channel] + (c1[channel] - c0[channel]) * weight
            ramp[:, :, channel][band] = color[band]
    ramp[elev < stops[0][0]] = stops[0][1]
    ramp[elev > stops[-1][0]] = stops[-1][1]
    return np.clip(ramp * relief[:, :, None], 0, 255).astype(np.uint8)


def grid_size(shape: tuple[int, int], max_side: int) -> tuple[int, int]:
    """Output rows and columns, limited on the long side."""
    height, width = shape
    scale = min(1.0, max_side / max(height, width))
    return max(80, int(round(height * scale))), max(80, int(round(width * scale)))


def nearest_cell(lats: np.ndarray, lons: np.ndarray, lat: float, lon: float) -> tuple[int, int]:
    """Row and column of the cell closest to a coordinate."""
    row = int(np.argmin(np.abs(lats - lat)))
    col = int(np.argmin(np.abs(lons - lon)))
    return row, col


def source_mask(elev: np.ndarray, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Cells of the hanging ice and rock that enter the valley."""
    dlat = (lats[:, None] - RELEASE_LAT) * 111_320.0
    dlon = (lons[None, :] - RELEASE_LON) * 111_320.0 * math.cos(math.radians(RELEASE_LAT))
    distance = np.hypot(dlat, dlon)
    mask = (distance < 900) & (elev > 4700) & (elev < 5900)
    if int(mask.sum()) < 12:
        mask = (distance < 1600) & (elev > 4300)
    return mask


def valley_mask(bed: np.ndarray, bridge: tuple[int, int], radius: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Cells that drain through the bridge, plus any of those cells that leave the grid.

    Side basins that never reach Rasuwagadhi stay dry. The simulated reach ends
    at the crossing. A border cell on that path can still drain out of the window.
    """
    rows, cols = bed.shape
    padded = np.pad(bed, 1, mode="constant", constant_values=-1.0e9)
    center = padded[1:-1, 1:-1]
    best_drop = np.zeros(bed.shape, dtype=np.float32)
    best_i = np.full(bed.shape, -1, dtype=np.int16)
    best_j = np.full(bed.shape, -1, dtype=np.int16)
    ii_base = np.arange(rows, dtype=np.int16)[:, None]
    jj_base = np.arange(cols, dtype=np.int16)[None, :]
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            dist = 1.41421356 if di and dj else 1.0
            neighbor = padded[1 + di : 1 + di + rows, 1 + dj : 1 + dj + cols]
            drop = (center - neighbor) / dist
            take = drop > best_drop
            ii = ii_base + di
            jj = jj_base + dj
            inside = (ii >= 0) & (ii < rows) & (jj >= 0) & (jj < cols)
            best_drop = np.where(take, drop, best_drop)
            best_i = np.where(take & inside, ii, np.where(take, np.int16(-1), best_i))
            best_j = np.where(take & inside, jj, np.where(take, np.int16(-1), best_j))

    state = np.zeros(bed.shape, dtype=np.int8)
    bridge_row, bridge_col = bridge

    def hits(row: int, col: int) -> bool:
        trail: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        found = False
        while 0 <= row < rows and 0 <= col < cols and (row, col) not in seen:
            if state[row, col] == 1:
                found = True
                break
            if state[row, col] == 2:
                break
            seen.add((row, col))
            trail.append((row, col))
            if max(abs(row - bridge_row), abs(col - bridge_col)) <= radius:
                found = True
                break
            nxt_row = int(best_i[row, col])
            nxt_col = int(best_j[row, col])
            if nxt_row < 0:
                break
            row, col = nxt_row, nxt_col
        mark = np.int8(1 if found else 2)
        for trail_row, trail_col in trail:
            state[trail_row, trail_col] = mark
        return found

    for row in range(rows):
        for col in range(cols):
            if state[row, col] == 0:
                hits(row, col)
    valley = state == 1
    border = np.zeros(bed.shape, dtype=bool)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    outlet = valley & border & (best_i < 0)
    return valley, outlet


def route_flood(
    bed: np.ndarray,
    dx: float,
    source: np.ndarray,
    bridge: tuple[int, int],
    valley: np.ndarray,
    outlet: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Diffusive-wave routing. Returns uint8 frames, arrival seconds, and stats."""
    rows, cols = bed.shape
    h = np.zeros_like(bed)
    qx = np.zeros((rows, cols - 1), dtype=np.float32)
    qy = np.zeros((rows - 1, cols), dtype=np.float32)
    h[source] = 28.0
    volume0 = float(h.sum() * dx * dx)
    arrival = np.full(bed.shape, np.nan, dtype=np.float32)
    frames: list[np.ndarray] = []
    times: list[float] = []
    clock = 0.0
    next_save = 0.0
    impact = None
    bridge_time = None
    source_elev = float(bed[source].mean()) if source.any() else float(bed.mean())
    wet_bridge = bridge

    def store() -> None:
        depth = np.clip(h / DEPTH_SCALE_M, 0, 255).astype(np.uint8)
        frames.append(depth)
        times.append(round(clock, 2))

    store()
    steps = 0
    while clock < SIM_SECONDS and steps < 48000:
        h_max = float(max(h.max(), 0.2))
        dt = 0.32 * dx / (math.sqrt(GRAVITY * h_max) + VELOCITY_CAP_M_S)
        dt = float(min(dt, 1.25, SIM_SECONDS - clock))
        if dt <= 0:
            break

        # Diffusive wave: Manning flux down the water-surface slope, limited
        # so one step cannot overshoot a level surface. qx > 0 flows east.
        drop_x = (bed[:, :-1] + h[:, :-1]) - (bed[:, 1:] + h[:, 1:])
        up_x = np.where(drop_x >= 0, h[:, :-1], h[:, 1:])
        slope_x = np.abs(drop_x) / dx
        speed_x = (1.0 / MANNINGS_N) * np.maximum(up_x, 0) ** (2.0 / 3.0) * np.sqrt(slope_x)
        speed_x = np.minimum(speed_x, VELOCITY_CAP_M_S)
        qx = np.sign(drop_x) * speed_x * up_x
        level_x = 0.62 * np.abs(drop_x) * dx / dt
        qx = np.clip(qx, -level_x, level_x).astype(np.float32)
        qx = np.where((up_x < 0.05) | (np.abs(drop_x) < 0.015), 0, qx)

        drop_y = (bed[:-1, :] + h[:-1, :]) - (bed[1:, :] + h[1:, :])
        up_y = np.where(drop_y >= 0, h[:-1, :], h[1:, :])
        slope_y = np.abs(drop_y) / dx
        speed_y = (1.0 / MANNINGS_N) * np.maximum(up_y, 0) ** (2.0 / 3.0) * np.sqrt(slope_y)
        speed_y = np.minimum(speed_y, VELOCITY_CAP_M_S)
        qy = np.sign(drop_y) * speed_y * up_y
        level_y = 0.62 * np.abs(drop_y) * dx / dt
        qy = np.clip(qy, -level_y, level_y).astype(np.float32)
        qy = np.where((up_y < 0.05) | (np.abs(drop_y) < 0.015), 0, qy)
        # A cell may not give away more water than it holds. Clipping a
        # negative depth would create volume on the receiving side.
        leaving = np.zeros_like(h)
        leaving[:, :-1] += np.maximum(qx, 0) * dt / dx
        leaving[:, 1:] += np.maximum(-qx, 0) * dt / dx
        leaving[:-1, :] += np.maximum(qy, 0) * dt / dx
        leaving[1:, :] += np.maximum(-qy, 0) * dt / dx
        scale = np.ones_like(h)
        over = leaving > h * 0.9
        scale[over] = np.where(leaving[over] > 0, (h[over] * 0.9) / leaving[over], 1)
        give_x = np.ones_like(qx)
        east = qx > 0
        give_x[east] = scale[:, :-1][east]
        give_x[~east] = scale[:, 1:][~east]
        qx *= give_x
        give_y = np.ones_like(qy)
        south = qy > 0
        give_y[south] = scale[:-1, :][south]
        give_y[~south] = scale[1:, :][~south]
        qy *= give_y
        outside = ~valley
        qx = np.where((qx > 0) & outside[:, 1:], 0, qx)
        qx = np.where((qx < 0) & outside[:, :-1], 0, qx)
        qy = np.where((qy > 0) & outside[1:, :], 0, qy)
        qy = np.where((qy < 0) & outside[:-1, :], 0, qy)

        change = np.zeros_like(h)
        change[:, :-1] -= qx * dt / dx
        change[:, 1:] += qx * dt / dx
        change[:-1, :] -= qy * dt / dx
        change[1:, :] += qy * dt / dx
        h = np.maximum(h + change, 0).astype(np.float32)
        h[outlet] *= 0.82
        clock += dt
        steps += 1

        newly = (h > 1.0) & np.isnan(arrival)
        arrival[newly] = clock
        if impact is None:
            fallen = (h > 4.0) & (bed < 4100.0)
            if fallen.any():
                idx = np.argwhere(fallen)[0]
                impact = {"row": int(idx[0]), "col": int(idx[1]), "time_s": round(clock, 1)}
        if bridge_time is None and h[wet_bridge] > 1.5:
            bridge_time = round(clock, 1)
        if clock >= next_save:
            store()
            next_save += SAVE_EVERY_S
            if steps % 1 == 0 and len(times) % 4 == 0:
                print(
                    f"  t={clock:6.0f}s  max depth {h.max():5.1f} m  "
                    f"wet {(h > 0.5).sum()}  volume {h.sum() * dx * dx / 1e6:.2f} Mm3",
                    flush=True,
                )
        if bridge_time is not None and clock > bridge_time + 240:
            break

    if not times or times[-1] < clock - 5:
        store()
    stack = np.stack(frames, axis=0)
    stats = {
        "steps": steps,
        "seconds": round(clock, 1),
        "volume_m3": round(volume0),
        "volume_end_m3": round(float(h.sum() * dx * dx)),
        "max_depth_m": round(float(h.max()), 2),
        "source_cells": int(source.sum()),
        "source_elev_m": round(source_elev, 1),
        "impact": impact,
        "bridge_arrival_s": bridge_time,
        "frame_times_s": times,
    }
    return stack, arrival, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Day 28 DEM flood.")
    parser.add_argument("--refresh", action="store_true", help="Redownload tiles.")
    args = parser.parse_args()

    elev, rgb, mosaic_meta = load_tiles(ZOOM, args.refresh)
    elev = fill_voids(elev)
    elev, rgb, meta = crop_window(elev, rgb, mosaic_meta)
    print(
        f"crop {elev.shape[1]}x{elev.shape[0]}  "
        f"elev {elev.min():.0f}-{elev.max():.0f} m",
        flush=True,
    )
    disp_h, disp_w = grid_size(elev.shape, DISPLAY_SIDE)
    sim_h, sim_w = grid_size(elev.shape, SIM_SIDE)
    disp_elev = resize_grid(elev, disp_h, disp_w).astype(np.float32)
    disp_rgb = np.clip(resize_grid(rgb.astype(np.float32), disp_h, disp_w), 0, 255).astype(np.uint8)
    print(f"display {disp_w}x{disp_h}  filling pits", flush=True)
    disp_bed = fill_depressions(disp_elev)
    bed = fill_depressions(resize_grid(disp_bed, sim_h, sim_w).astype(np.float32))
    lats, lons = cell_lonlat(sim_h, sim_w, meta)
    disp_lats, disp_lons = cell_lonlat(disp_h, disp_w, meta)
    mid_lat = float(lats[sim_h // 2])
    meters_lat = 111_132.92 - 559.82 * math.cos(2 * math.radians(mid_lat))
    meters_lon = 111_412.84 * math.cos(math.radians(mid_lat))
    height_m = float((meta["north"] - meta["south"]) * meters_lat)
    width_m = float((meta["east"] - meta["west"]) * meters_lon)
    dx = width_m / sim_w
    dy = height_m / sim_h
    cell = float((dx + dy) / 2)
    print(
        f"route {sim_w}x{sim_h}  cell {cell:.1f} m  "
        f"domain {width_m/1000:.1f} x {height_m/1000:.1f} km",
        flush=True,
    )

    shade = hillshade(disp_bed, width_m / disp_w, height_m / disp_h)
    image = colorize(disp_rgb, disp_bed, shade)
    mask = source_mask(bed, lats, lons)
    bridge = nearest_cell(lats, lons, BRIDGE_LAT, BRIDGE_LON)
    valley, outlet = valley_mask(bed, bridge)
    kept = mask & valley
    print(
        f"valley cells {int(valley.sum())}  outlets {int(outlet.sum())}  "
        f"release kept {int(kept.sum())} of {int(mask.sum())}",
        flush=True,
    )
    if int(kept.sum()) >= 12:
        mask = kept
    release = nearest_cell(lats, lons, RELEASE_LAT, RELEASE_LON)
    summit = nearest_cell(disp_lats, disp_lons, SUMMIT_LAT, SUMMIT_LON)
    # The surveyed summit may sit off the highest DEM cell nearby.
    window = disp_bed[
        max(0, summit[0] - 12) : summit[0] + 13,
        max(0, summit[1] - 12) : summit[1] + 13,
    ]
    if window.size:
        local = np.argwhere(window == window.max())[0]
        summit = (
            max(0, summit[0] - 12) + int(local[0]),
            max(0, summit[1] - 12) + int(local[1]),
        )
    print(
        f"release cell elev {bed[release]:.0f} m on {int(mask.sum())} cells; "
        f"bridge elev {bed[bridge]:.0f} m; summit {disp_bed[summit]:.0f} m",
        flush=True,
    )
    print("routing", flush=True)
    frames, _arrival, stats = route_flood(bed, cell, mask, bridge, valley, outlet)
    print(json.dumps({k: v for k, v in stats.items() if k != "frame_times_s"}, indent=2), flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "terrain.bin").write_bytes(np.ascontiguousarray(disp_bed, dtype="<f4").tobytes())
    (OUT / "flow.bin").write_bytes(np.ascontiguousarray(frames).tobytes())
    Image.fromarray(image, "RGB").save(OUT / "imagery.jpg", quality=86, optimize=True)

    def place_xy(name: str, lat: float, lon: float, extra: dict | None = None) -> dict:
        row, col = nearest_cell(disp_lats, disp_lons, lat, lon)
        item = {
            "name": name,
            "lat": round(float(lat), 5),
            "lon": round(float(lon), 5),
            "row": row,
            "col": col,
            "elev_m": round(float(disp_bed[row, col])),
        }
        if extra:
            item.update(extra)
        return item

    impact_place = None
    if stats["impact"]:
        impact_lat = float(lats[stats["impact"]["row"]])
        impact_lon = float(lons[stats["impact"]["col"]])
        impact_place = place_xy(
            "Impact",
            impact_lat,
            impact_lon,
            {"time_s": stats["impact"]["time_s"]},
        )
    summit_lat = float(disp_lats[summit[0]])
    summit_lon = float(disp_lons[summit[1]])
    payload = {
        "rows": disp_h,
        "cols": disp_w,
        "flow_rows": sim_h,
        "flow_cols": sim_w,
        "west": meta["west"],
        "south": meta["south"],
        "east": meta["east"],
        "north": meta["north"],
        "width_m": round(width_m, 1),
        "height_m": round(height_m, 1),
        "cell_m": round(width_m / disp_w, 2),
        "flow_cell_m": round(cell, 2),
        "exaggeration": 1.15,
        "depth_scale_m": DEPTH_SCALE_M,
        "frame_times_s": stats["frame_times_s"],
        "volume_m3": stats["volume_m3"],
        "max_depth_m": stats["max_depth_m"],
        "bridge_arrival_s": stats["bridge_arrival_s"],
        "simulated_seconds": stats["seconds"],
        "release": place_xy("~5,200 m", RELEASE_LAT, RELEASE_LON, {"cells": stats["source_cells"]}),
        "bridge": place_xy("Rasuwagadhi", BRIDGE_LAT, BRIDGE_LON, {"arrival_s": stats["bridge_arrival_s"]}),
        "summit": place_xy("Langtang Lirung", summit_lat, summit_lon, {"surveyed_m": 7227}),
        "impact": impact_place,
        "model": (
            "2D diffusive-wave routing, Manning's equation on the water-surface slope, "
            f"n={MANNINGS_N}, velocity cap {VELOCITY_CAP_M_S:.0f} m/s. "
            "Water is kept in the drainage that passes Rasuwagadhi. The simulated reach ends at the crossing. "
            "Uncalibrated. Initial depth on the release cells is 28 m."
        ),
        "dem": "AWS Terrain tiles, zoom 13, mostly SRTM. Pits filled so the valley drains.",
        "imagery": "Esri World Imagery, lightly hillshaded from the DEM.",
    }
    (OUT / "bounds.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'bounds.json'}", flush=True)


if __name__ == "__main__":
    main()
