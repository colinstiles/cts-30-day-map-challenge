#!/usr/bin/env python3
"""
Day 8 — Utopia: Tugalo Undammed (Lake Tugalo drained).

Fetches USGS 3DEP DEM, paints a "now" lake scene, carves a schematic restored
valley for utopia, then exports:
  - 2026/images/day-08-now.png
  - 2026/images/day-08-utopia.png
  - 2026/images/day-08.png          (static dual-panel)
  - 2026/images/day-08-bounds.json  (Leaflet imageOverlay bounds)

Usage
-----
  pip install -r 2026/08_utopia/requirements.txt
  python scripts/day08_tugalo_undammed.py

  # If USGS 3DEP is down, use OpenTopography global DEM (non-USGS):
  python scripts/day08_tugalo_undammed.py --source opentopo

  # Or pass a local GeoTIFF:
  python scripts/day08_tugalo_undammed.py --dem data/raw/tugalo_dem.tif

Corporate proxy: if HTTPS fails behind Zscaler, trust the local corporate
cert. Do not disable TLS for routine use.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEM_OUT = REPO_ROOT / "data" / "processed" / "tugalo_dem.tif"
DEFAULT_UTOPIA_DEM = REPO_ROOT / "data" / "processed" / "tugalo_utopia_dem.tif"
DEFAULT_NOW = REPO_ROOT / "2026" / "images" / "day-08-now.png"
DEFAULT_UTOPIA = REPO_ROOT / "2026" / "images" / "day-08-utopia.png"
DEFAULT_STATIC = REPO_ROOT / "2026" / "images" / "day-08.png"
DEFAULT_BOUNDS = REPO_ROOT / "2026" / "images" / "day-08-bounds.json"
OPENTOPO_URL = "https://portal.opentopography.org/API/globaldem"

# Landscape frame on the Lake Tugalo bowl (WGS84 west, south, east, north).
# Wide enough that the swipe fills a gallery card without cropping the arms.
BBOX = (-83.408, 34.700, -83.312, 34.766)
DAM = (-83.35183, 34.71396)  # lon, lat — Georgia Power Tugalo plant
POOL_ELEV_M = 271.73  # Georgia Power full-pool (masl)
DAM_TOE_M = 227.0  # approximate riverbed at dam (schematic)

# 3DEP water surface sits just under Georgia Power's published full-pool.
POOL_BAND = (264.0, 272.5)


def _require_imports(need_py3dep: bool = False) -> None:
    missing = []
    for name in ("numpy", "matplotlib", "scipy"):
        try:
            __import__(name if name != "matplotlib" else "matplotlib.pyplot")
        except ImportError:
            missing.append(name if name != "matplotlib" else "matplotlib")
    try:
        import rasterio  # noqa: F401
    except ImportError:
        missing.append("rasterio")
    try:
        import rioxarray  # noqa: F401
    except ImportError:
        missing.append("rioxarray")
    if need_py3dep:
        try:
            import py3dep  # noqa: F401
        except ImportError:
            missing.append("py3dep")
    if missing:
        raise SystemExit(
            "Missing packages: "
            + ", ".join(missing)
            + "\nInstall with: pip install -r 2026/08_utopia/requirements.txt"
        )


THREE_DEP_IMAGE_SERVICE = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"
)


def _dem_from_geotiff_bytes(payload: bytes):
    import rioxarray  # noqa: F401
    import xarray as xr
    from rasterio.io import MemoryFile

    if payload.lstrip().startswith(b"{"):
        raise RuntimeError(payload.decode("utf-8", errors="replace"))
    with MemoryFile(payload) as memfile, memfile.open() as dataset:
        values = dataset.read(1, masked=True).filled(np.nan).astype(np.float64)
        transform = dataset.transform
        x = transform.c + (np.arange(dataset.width) + 0.5) * transform.a
        y = transform.f + (np.arange(dataset.height) + 0.5) * transform.e
        dem = xr.DataArray(values, dims=("y", "x"), coords={"y": y, "x": x})
        dem = dem.rio.write_crs(dataset.crs or "EPSG:4326")
        return dem.rio.write_transform(transform)


def load_dem_file(path: Path):
    import rioxarray as rxr

    if not path.is_file():
        raise FileNotFoundError(path)
    dem = rxr.open_rasterio(path, masked=True).squeeze(drop=True)
    if dem.rio.crs is None:
        dem = dem.rio.write_crs("EPSG:4326")
    # Reproject / clip to project bbox if needed
    try:
        dem = dem.rio.clip_box(*BBOX)
    except Exception:  # noqa: BLE001 — keep full raster if clip fails
        pass
    print(f"Loaded local DEM {path}")
    return dem


def _export_size(bbox: tuple[float, float, float, float], max_px: int = 1400) -> tuple[int, int]:
    """Pixel size that keeps the 3DEP export cells close to square."""
    west, south, east, north = bbox
    width_m = (east - west) * 111_320 * math.cos(math.radians((south + north) / 2))
    height_m = (north - south) * 110_540
    if width_m >= height_m:
        return max_px, max(200, int(round(max_px * height_m / width_m)))
    return max(200, int(round(max_px * width_m / height_m))), max_px


def fetch_dem_rest(bbox: tuple[float, float, float, float], size: tuple[int, int] | None = None):
    """DEM via 3DEP ImageServer (same fallback pattern as Day 6)."""
    width, height = size or _export_size(bbox)
    params = {
        "bbox": ",".join(map(str, bbox)),
        "bboxSR": "4326",
        "imageSR": "4326",
        "size": f"{width},{height}",
        "format": "tiff",
        "pixelType": "F32",
        "interpolation": "RSP_BilinearInterpolation",
        "f": "image",
    }
    request = Request(
        f"{THREE_DEP_IMAGE_SERVICE}?{urlencode(params)}",
        headers={"User-Agent": "30-Day-Map-Challenge-Day-08"},
    )
    print("Fetching 3DEP DEM from ImageServer …")
    with urlopen(request, timeout=180) as response:  # noqa: S310 -- fixed USGS URL
        return _dem_from_geotiff_bytes(response.read())


def fetch_dem_py3dep(bbox: tuple[float, float, float, float], resolution: float):
    import py3dep

    print(f"Fetching 3DEP DEM via py3dep @ {resolution} m …")
    dem = py3dep.get_map(
        "DEM",
        geometry=bbox,
        resolution=resolution,
        geo_crs="EPSG:4326",
        crs="EPSG:4326",
    )
    if dem.rio.crs is None:
        dem = dem.rio.write_crs("EPSG:4326")
    return dem


def fetch_dem_opentopo(
    bbox: tuple[float, float, float, float],
    demtype: str = "SRTMGL1",
    api_key: str | None = None,
):
    """Global DEM via OpenTopography (does not depend on USGS 3DEP uptime)."""
    west, south, east, north = bbox
    key = api_key or os.environ.get("OPENTOPOGRAPHY_API_KEY") or "demoapikeyot2022"
    params = {
        "demtype": demtype,
        "west": west,
        "south": south,
        "east": east,
        "north": north,
        "outputFormat": "GTiff",
        "API_Key": key,
    }
    request = Request(
        f"{OPENTOPO_URL}?{urlencode(params)}",
        headers={"User-Agent": "30-Day-Map-Challenge-Day-08"},
    )
    print(f"Fetching OpenTopography {demtype} …")
    with urlopen(request, timeout=180) as response:  # noqa: S310 -- fixed OT URL
        return _dem_from_geotiff_bytes(response.read())


def fetch_dem(
    bbox: tuple[float, float, float, float],
    resolution: float,
    source: str = "auto",
    dem_path: Path | None = None,
    opentopo_type: str = "SRTMGL1",
):
    """Fetch DEM. source: auto | usgs | opentopo | local."""
    errors: list[str] = []

    if dem_path is not None or source == "local":
        if dem_path is None:
            raise SystemExit("--source local requires --dem path")
        return load_dem_file(dem_path)

    if source in ("auto", "usgs"):
        try:
            return fetch_dem_rest(bbox)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"ImageServer: {exc}")
            print(f"Warning: ImageServer DEM failed ({exc})")
        try:
            return fetch_dem_py3dep(bbox, resolution)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"py3dep: {exc}")
            print(f"Warning: py3dep DEM failed ({exc})")
        if source == "usgs":
            raise RuntimeError("USGS 3DEP unavailable:\n- " + "\n- ".join(errors))

    if source in ("auto", "opentopo"):
        try:
            return fetch_dem_opentopo(bbox, demtype=opentopo_type)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"OpenTopography: {exc}")
            print(f"Warning: OpenTopography DEM failed ({exc})")

    raise RuntimeError(
        "All DEM sources failed:\n- "
        + "\n- ".join(errors)
        + "\nRetry later, or pass --dem path/to.tif / --source opentopo"
    )


def hillshade(
    dem: np.ndarray,
    pixel_m: float = 10.0,
    azimuth: float = 315.0,
    altitude: float = 45.0,
) -> np.ndarray:
    """Simple GDAL-style hillshade from a DEM array (meters)."""
    filled = np.nan_to_num(dem, nan=np.nanmedian(dem))
    dy, dx = np.gradient(filled)
    slope = np.pi / 2.0 - np.arctan(np.hypot(dx / pixel_m, dy / pixel_m))
    aspect = np.arctan2(-dx, dy)
    az = np.radians(azimuth)
    alt = np.radians(altitude)
    shaded = np.sin(alt) * np.sin(slope) + np.cos(alt) * np.cos(slope) * np.cos(az - aspect)
    return np.clip(shaded, 0, 1)


def lonlat_grids(dem) -> tuple[np.ndarray, np.ndarray]:
    """Return lon/lat mesh for dem DataArray (y, x)."""
    x = dem.x.values
    y = dem.y.values
    lon, lat = np.meshgrid(x, y)
    return lon, lat


def pixel_size_m(dem) -> float:
    """Ground size of one cell in meters. DEM is EPSG:4326."""
    transform = dem.rio.transform()
    lat = float(np.mean(np.asarray(dem.y.values)))
    dx = abs(float(transform.a)) * 111_320 * math.cos(math.radians(lat))
    dy = abs(float(transform.e)) * 110_540
    return (dx + dy) / 2.0


def _largest_component(mask: np.ndarray) -> np.ndarray:
    from scipy import ndimage

    labels, n = ndimage.label(mask)
    if n == 0:
        return mask
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    return labels == int(np.argmax(counts))


def _fill_small_holes(mask: np.ndarray, max_hole: int = 40) -> np.ndarray:
    """Fill enclosed gaps small enough to be DEM speckle, keep real islands."""
    from scipy import ndimage

    holes, n = ndimage.label(~mask)
    if n == 0:
        return mask
    border = np.unique(np.concatenate([holes[0, :], holes[-1, :], holes[:, 0], holes[:, -1]]))
    out = mask.copy()
    for label in range(1, n + 1):
        if label in border:
            continue
        hole = holes == label
        if int(hole.sum()) <= max_hole:
            out[hole] = True
    return out


def lake_mask(lon: np.ndarray, lat: np.ndarray, dem: np.ndarray) -> np.ndarray:
    """Lake Tugalo from the flat 3DEP water surface, trimmed below the dam."""
    from scipy import ndimage

    low, high = POOL_BAND
    flat = (dem >= low) & (dem <= high) & np.isfinite(dem)
    mask = _largest_component(flat)
    if not mask.any():
        raise RuntimeError("No flat pool surface found in the DEM")
    mask = _fill_small_holes(mask)
    # Reservoir is upstream of the dam. Drop the tailrace shelf south of the plant.
    mask &= lat >= (DAM[1] - 0.0012)
    mask = _largest_component(mask)
    mask = ndimage.binary_dilation(mask, iterations=1)
    return mask


def _shore_distance(dem: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pixel distance to shore, and the nearest land elevation just outside the pool."""
    from scipy import ndimage

    dist_px, (iy, ix) = ndimage.distance_transform_edt(mask, return_indices=True)
    return dist_px, dem[iy, ix]


def _outlet_rc(mask: np.ndarray, lon: np.ndarray, lat: np.ndarray) -> tuple[int, int]:
    rows, cols = np.where(mask)
    dlon = (lon[rows, cols] - DAM[0]) * 111_320 * math.cos(math.radians(DAM[1]))
    dlat = (lat[rows, cols] - DAM[1]) * 110_540
    pick = int(np.argmin(dlon * dlon + dlat * dlat))
    return int(rows[pick]), int(cols[pick])


def _distance_from(mask: np.ndarray, start: tuple[int, int]) -> np.ndarray:
    """8-connected distance in pixels from start, -1 outside the mask."""
    from collections import deque

    dist = np.full(mask.shape, -1, dtype=np.int32)
    if not mask[start]:
        return dist
    dist[start] = 0
    queue: deque[tuple[int, int]] = deque([start])
    height, width = mask.shape
    while queue:
        row, col = queue.popleft()
        nxt = dist[row, col] + 1
        for drow, dcol in (
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ):
            rr, cc = row + drow, col + dcol
            if 0 <= rr < height and 0 <= cc < width and mask[rr, cc] and dist[rr, cc] < 0:
                dist[rr, cc] = nxt
                queue.append((rr, cc))
    return dist


def carve_utopia(
    dem: np.ndarray,
    mask: np.ndarray,
    dist_shore_px: np.ndarray,
    shore_z: np.ndarray,
    dist_out_px: np.ndarray,
) -> np.ndarray:
    """Schematic gorge under the pool: deep at the dam, shallow in the arms.

    Bed elevation is interpolated along the pool from the dam toe to just
    under the old water surface. Side slopes climb to the real bank.
    """
    from scipy import ndimage

    out = dem.copy()
    max_out = max(int(dist_out_px[mask].max()), 1)
    progress = np.clip(dist_out_px / max_out, 0, 1)
    head_bed = POOL_ELEV_M - 4.0
    bed = DAM_TOE_M + progress * (head_bed - DAM_TOE_M)
    # Rim is the old waterline. The 3DEP bank stays outside the pool.
    rim = np.minimum(shore_z, POOL_ELEV_M)
    bed = np.minimum(bed, rim - 4.0)
    # 0 at the shoreline, 1 on the center of that part of the pool.
    local_half = ndimage.maximum_filter(dist_shore_px, size=121)
    t = np.clip(dist_shore_px / np.maximum(local_half, 1.0), 0, 1)
    wall = rim - (rim - bed) * (t ** 2)
    wall = np.minimum(wall, dem)
    out[mask] = wall[mask]
    return out


def _trace_arms(
    mask: np.ndarray,
    dist_shore: np.ndarray,
    dist_out: np.ndarray,
) -> np.ndarray:
    """Continuous thread from each arm tip back to the dam, staying mid-channel."""
    from scipy import ndimage

    score = np.where(mask, dist_out, 0)
    local = ndimage.maximum_filter(score, size=45)
    tips, n = ndimage.label(mask & (dist_out >= local) & (dist_out > 25))
    seeds: list[tuple[int, int]] = []
    for label in range(1, n + 1):
        rows, cols = np.where(tips == label)
        keep = int(np.argmax(dist_out[rows, cols]))
        seeds.append((int(rows[keep]), int(cols[keep])))
    thread = np.zeros(mask.shape, dtype=bool)
    height, width = mask.shape
    steps = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
    for row, col in seeds:
        for _ in range(width + height):
            thread[row, col] = True
            if dist_out[row, col] <= 0:
                break
            best = None
            best_key = None
            for drow, dcol in steps:
                rr, cc = row + drow, col + dcol
                if not (0 <= rr < height and 0 <= cc < width and mask[rr, cc]):
                    continue
                if dist_out[rr, cc] >= dist_out[row, col]:
                    continue
                key = (int(dist_out[rr, cc]), -float(dist_shore[rr, cc]))
                if best_key is None or key < best_key:
                    best_key = key
                    best = (rr, cc)
            if best is None:
                break
            row, col = best
    return ndimage.binary_dilation(thread, iterations=1) & mask


def river_and_downstream(
    dem: np.ndarray,
    mask: np.ndarray,
    dist_shore_px: np.ndarray,
    dist_out: np.ndarray,
    outlet: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, list[tuple[int, int]]]:
    """Restored centerline inside the pool, plus the free river below the dam."""
    rivers = _trace_arms(mask, dist_shore_px, dist_out)

    below = np.zeros(mask.shape, dtype=bool)
    centers: list[tuple[int, int]] = []
    row, col = outlet
    height, width = dem.shape
    seen = {outlet}
    running_min = float(dem[row, col])
    for _ in range(140):
        best = None
        best_z = 1e18
        for drow in (-1, 0, 1):
            for dcol in (-1, 0, 1):
                if drow == 0 and dcol == 0:
                    continue
                rr, cc = row + drow, col + dcol
                if not (0 <= rr < height and 0 <= cc < width):
                    continue
                if (rr, cc) in seen or mask[rr, cc] or not np.isfinite(dem[rr, cc]):
                    continue
                elev = float(dem[rr, cc])
                # South-southeast is downstream on the Tugaloo. A small south
                # bias lets the trace cross a riffle without climbing the gorge wall.
                score = elev - 0.08 * drow
                if score < best_z:
                    best_z = score
                    best = (rr, cc)
        if best is None:
            break
        if float(dem[best]) > running_min + 18.0:
            break
        row, col = best
        running_min = min(running_min, float(dem[row, col]))
        seen.add(best)
        centers.append(best)
        below[row, col] = True
    if centers:
        from scipy import ndimage

        below = ndimage.binary_dilation(below, iterations=1)
    below[mask] = False
    return rivers, below, centers


def _widest_point(mask: np.ndarray, dist_shore: np.ndarray, lon: np.ndarray, lat: np.ndarray):
    score = np.where(mask, dist_shore, -1)
    row, col = np.unravel_index(int(np.argmax(score)), score.shape)
    return float(lat[row, col]), float(lon[row, col])


def _arm_point(spine: np.ndarray, values: np.ndarray, dist_shore: np.ndarray, high: bool):
    if not spine.any():
        return None
    picked = values[spine]
    threshold = np.quantile(picked, 0.86 if high else 0.14)
    arm = spine & (values >= threshold if high else values <= threshold)
    if not arm.any():
        arm = spine
    rows, cols = np.where(arm)
    keep = int(np.argmax(dist_shore[rows, cols]))
    return int(rows[keep]), int(cols[keep])


def _label_at(mask: np.ndarray, lon: np.ndarray, lat: np.ndarray, row_frac: float, col_frac: float):
    """A land label. Nudge off the pool if the anchor cell is water."""
    row = min(mask.shape[0] - 1, max(0, int(mask.shape[0] * row_frac)))
    col = min(mask.shape[1] - 1, max(0, int(mask.shape[1] * col_frac)))
    if mask[row, col]:
        height, width = mask.shape
        for radius in range(1, 90):
            r0, r1 = max(0, row - radius), min(height, row + radius + 1)
            c0, c1 = max(0, col - radius), min(width, col + radius + 1)
            window = ~mask[r0:r1, c0:c1]
            if window.any():
                found = np.argwhere(window)[0]
                row, col = int(found[0] + r0), int(found[1] + c0)
                break
    return float(lat[row, col]), float(lon[row, col])


def place_names(
    mask: np.ndarray,
    centers: list[tuple[int, int]],
    dist_shore: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
) -> list[dict]:
    """Soft labels. Chattooga is the north arm; Tallulah is the west arm."""
    from scipy import ndimage

    local = ndimage.maximum_filter(dist_shore, size=11)
    spine = mask & (dist_shore >= local - 0.51) & (dist_shore > 3)
    chat_rc = _arm_point(spine, lat, dist_shore, high=True)
    tall_rc = _arm_point(spine, lon, dist_shore, high=False)
    lake_lat, lake_lon = _widest_point(mask, dist_shore, lon, lat)
    places = [
        {"name": "Lake Tugalo", "lat": lake_lat, "lon": lake_lon, "side": "now"},
        # Text sits just upstream of the plant so it doesn't cover the outlet.
        {"name": "Tugalo Dam", "lat": DAM[1] + 0.004, "lon": DAM[0] - 0.002, "side": "now"},
    ]
    if chat_rc:
        row, col = chat_rc
        places.append(
            {
                "name": "Chattooga River",
                "lat": float(lat[row, col]) - 0.006,
                "lon": float(lon[row, col]) - 0.012,
                "side": "both",
            }
        )
    if tall_rc:
        row, col = tall_rc
        places.append(
            {"name": "Tallulah River", "lat": float(lat[row, col]), "lon": float(lon[row, col]), "side": "both"}
        )
    if centers:
        row, col = centers[min(len(centers) - 1, max(8, int(len(centers) * 0.55)))]
        places.append(
            {"name": "Tugaloo River", "lat": float(lat[row, col]), "lon": float(lon[row, col]), "side": "both"}
        )
    # Georgia west of the pool, South Carolina east of the Chattooga arm.
    ga_lat, ga_lon = _label_at(mask, lon, lat, 0.28, 0.08)
    sc_lat, sc_lon = _label_at(mask, lon, lat, 0.20, 0.80)
    places.append({"name": "Georgia", "lat": ga_lat, "lon": ga_lon, "side": "both"})
    places.append({"name": "South Carolina", "lat": sc_lat, "lon": sc_lon, "side": "both"})
    return places


def colorize_now(hs: np.ndarray, lake: np.ndarray, channel: np.ndarray) -> np.ndarray:
    """RGB uint8 hillshade with the reservoir and the river below the dam."""
    base = (hs * 255).astype(np.float32)
    rgb = np.stack([base * 0.92, base * 0.95, base * 0.88], axis=-1)
    water = np.array([42.0, 98.0, 148.0])
    depth = 0.55 + 0.35 * (1.0 - hs)
    for i in range(3):
        channel_px = rgb[..., i]
        channel_px[lake] = water[i] * depth[lake] + channel_px[lake] * 0.25
        rgb[..., i] = channel_px
    river = np.array([55.0, 125.0, 165.0])
    for i in range(3):
        channel_px = rgb[..., i]
        channel_px[channel] = river[i] * 0.82 + channel_px[channel] * 0.18
        rgb[..., i] = channel_px
    return np.clip(rgb, 0, 255).astype(np.uint8)


def colorize_utopia(hs: np.ndarray, rivers: np.ndarray, was_lake: np.ndarray, channel: np.ndarray) -> np.ndarray:
    base = (hs * 255).astype(np.float32)
    rgb = np.stack([base * 0.90, base * 0.96, base * 0.84], axis=-1)
    restored = was_lake & ~rivers
    rgb[restored, 0] = rgb[restored, 0] * 0.97 + 6
    rgb[restored, 1] = rgb[restored, 1] * 0.96 + 12
    rgb[restored, 2] = rgb[restored, 2] * 0.97 + 4
    water = np.array([48.0, 122.0, 168.0])
    wet = rivers | channel
    for i in range(3):
        channel_px = rgb[..., i]
        channel_px[wet] = water[i] * 0.88 + channel_px[wet] * 0.12
        rgb[..., i] = channel_px
    return np.clip(rgb, 0, 255).astype(np.uint8)


def save_png(path: Path, rgb: np.ndarray) -> None:
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(rgb.shape[1] / 100, rgb.shape[0] / 100), dpi=100)
    ax.imshow(rgb, interpolation="nearest")
    ax.set_axis_off()
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(path, dpi=100, pad_inches=0)
    plt.close(fig)
    print(f"Wrote {path}")


def _row_col(lon_row: np.ndarray, lat_col: np.ndarray, lon: float, lat: float) -> tuple[int, int]:
    col = int(np.argmin(np.abs(lon_row - lon)))
    row = int(np.argmin(np.abs(lat_col - lat)))
    return row, col


def save_static_dual(
    path: Path,
    now_rgb: np.ndarray,
    utopia_rgb: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
    places: list[dict],
) -> None:
    import matplotlib.pyplot as plt
    from matplotlib import patheffects as pe

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 7), facecolor="#10140f")
    titles = ("Now — Lake Tugalo", "Utopia — Tugalo undammed")
    stroke = [pe.withStroke(linewidth=2.4, foreground="#10140f")]
    lon_row = lon[0, :]
    lat_col = lat[:, 0]
    for ax, img, title, side in zip(axes, (now_rgb, utopia_rgb), titles, ("now", "utopia")):
        ax.imshow(img, interpolation="bilinear")
        ax.set_axis_off()
        ax.set_title(title, color="#f2efe4", fontsize=12, pad=8, fontfamily="serif")
        for place in places:
            if place["side"] not in (side, "both"):
                continue
            row, col = _row_col(lon_row, lat_col, place["lon"], place["lat"])
            ax.text(
                col,
                row,
                place["name"],
                color="#f4f0e4",
                fontsize=7,
                ha="center",
                va="center",
                fontfamily="serif",
                path_effects=stroke,
            )
    fig.suptitle(
        "Hidden Rapids of the Tallulah River",
        color="#ffe66d",
        fontsize=16,
        fontfamily="serif",
        y=0.98,
    )
    fig.text(
        0.5,
        0.02,
        "Lake outline from the 3DEP water surface. Restored valley is schematic, not surveyed bathymetry.",
        ha="center",
        color="#9a9688",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(path, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Wrote {path}")


def write_bounds(path: Path, dem, places: list[dict]) -> None:
    # Leaflet LatLngBounds: [[south, west], [north, east]]
    left, bottom, right, top = dem.rio.bounds()
    rounded_places = [
        {
            "name": place["name"],
            "lat": round(float(place["lat"]), 5),
            "lon": round(float(place["lon"]), 5),
            "side": place["side"],
        }
        for place in places
    ]
    payload = {
        "bounds": [[round(bottom, 6), round(left, 6)], [round(top, 6), round(right, 6)]],
        "dam": {"lat": DAM[1], "lon": DAM[0]},
        "places": rounded_places,
        "note": (
            "Lake Tugalo outline is the flat USGS 3DEP water surface. "
            "The undammed valley is a schematic carve, not surveyed bathymetry."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def save_geotiff(path: Path, dem) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dem.rio.to_raster(path)
    print(f"Wrote {path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--resolution", type=float, default=10.0, help="DEM resolution meters (py3dep path)")
    p.add_argument(
        "--source",
        choices=("auto", "usgs", "opentopo", "local"),
        default="auto",
        help="DEM source: auto tries USGS then OpenTopography",
    )
    p.add_argument("--dem", type=Path, default=None, help="Local GeoTIFF (skips download)")
    p.add_argument(
        "--opentopo-type",
        default="SRTMGL1",
        help="OpenTopography demtype (SRTMGL1, COP30, …)",
    )
    p.add_argument("--dem-out", type=Path, default=DEFAULT_DEM_OUT)
    p.add_argument("--utopia-dem-out", type=Path, default=DEFAULT_UTOPIA_DEM)
    p.add_argument("--now", type=Path, default=DEFAULT_NOW)
    p.add_argument("--utopia", type=Path, default=DEFAULT_UTOPIA)
    p.add_argument("--static", type=Path, default=DEFAULT_STATIC)
    p.add_argument("--bounds", type=Path, default=DEFAULT_BOUNDS)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = "local" if args.dem else args.source
    _require_imports(need_py3dep=source in ("auto", "usgs"))
    import rioxarray  # noqa: F401 — ensures accessor

    dem = fetch_dem(
        BBOX,
        args.resolution,
        source=source,
        dem_path=args.dem,
        opentopo_type=args.opentopo_type,
    )
    # Squeeze to 2D
    if dem.ndim == 3:
        dem = dem.squeeze(drop=True)
    dem_vals = np.array(dem.values, dtype=np.float64)
    lon, lat = lonlat_grids(dem)
    cell_m = pixel_size_m(dem)
    lake = lake_mask(lon, lat, dem_vals)
    print(f"Lake mask cells: {int(lake.sum())}  pixel_m: {cell_m:.2f}")

    water_elev = float(np.median(dem_vals[lake])) if lake.any() else POOL_ELEV_M
    dem_now = dem_vals.copy()
    dem_now[lake] = water_elev
    hs_now = hillshade(dem_now, pixel_m=cell_m)

    dist_shore, shore_z = _shore_distance(dem_vals, lake)
    outlet = _outlet_rc(lake, lon, lat)
    dist_out = _distance_from(lake, outlet)
    utopia_vals = carve_utopia(dem_vals, lake, dist_shore, shore_z, dist_out)
    hs_utopia = hillshade(utopia_vals, pixel_m=cell_m)
    rivers, below, centers = river_and_downstream(dem_vals, lake, dist_shore, dist_out, outlet)
    # A narrow slot so the restored channel reads in the hillshade, not only as paint.
    if rivers.any():
        from scipy import ndimage

        weight = ndimage.gaussian_filter(rivers.astype(np.float64), sigma=1.1)
        weight /= weight.max()
        utopia_vals = utopia_vals - weight * 8.0
        hs_utopia = hillshade(utopia_vals, pixel_m=cell_m)
    places = place_names(lake, centers, dist_shore, lon, lat)
    for place in places:
        print(f"  {place['name']}: {place['lat']:.5f}, {place['lon']:.5f} ({place['side']})")

    now_rgb = colorize_now(hs_now, lake, below)
    utopia_rgb = colorize_utopia(hs_utopia, rivers, lake, below)

    save_png(args.now, now_rgb)
    save_png(args.utopia, utopia_rgb)
    save_static_dual(args.static, now_rgb, utopia_rgb, lon, lat, places)
    write_bounds(args.bounds, dem, places)

    # Persist rasters
    utopia_da = dem.copy(data=utopia_vals)
    save_geotiff(args.dem_out, dem)
    save_geotiff(args.utopia_dem_out, utopia_da)
    return 0


if __name__ == "__main__":
    sys.exit(main())
