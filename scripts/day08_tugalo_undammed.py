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

# Tight frame on Lake Tugalo bowl (WGS84 west, south, east, north)
BBOX = (-83.415, 34.698, -83.318, 34.778)
DAM = (-83.35183, 34.71396)  # lon, lat — Georgia Power Tugalo plant
POOL_ELEV_M = 271.73  # Georgia Power full-pool (masl)
DAM_TOE_M = 227.0  # approximate riverbed at dam (schematic)

# Schematic Lake Tugalo shoreline (lon, lat) — not cadastral
LAKE_RING = [
    (-83.3525, 34.7128),
    (-83.3480, 34.7135),
    (-83.3455, 34.7180),
    (-83.3460, 34.7280),
    (-83.3505, 34.7400),
    (-83.3550, 34.7520),
    (-83.3605, 34.7620),
    (-83.3680, 34.7685),
    (-83.3760, 34.7660),
    (-83.3820, 34.7550),
    (-83.3880, 34.7420),
    (-83.3920, 34.7300),
    (-83.3900, 34.7205),
    (-83.3820, 34.7160),
    (-83.3700, 34.7145),
    (-83.3600, 34.7135),
    (-83.3525, 34.7128),
]

# Restored thalwegs (lon, lat): Chattooga arm, Tallulah arm → dam
CHATTOOGA_THALWEG = [
    (-83.3650, 34.7700),
    (-83.3580, 34.7550),
    (-83.3530, 34.7380),
    (-83.3510, 34.7250),
    DAM,
]
TALLULAH_THALWEG = [
    (-83.3950, 34.7350),
    (-83.3800, 34.7280),
    (-83.3650, 34.7220),
    (-83.3550, 34.7180),
    DAM,
]


def _require_imports(need_py3dep: bool = False) -> None:
    missing = []
    for name in ("numpy", "matplotlib"):
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


def point_in_ring(lon: float, lat: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        if (y1 > lat) != (y2 > lat):
            x_int = (x2 - x1) * (lat - y1) / (y2 - y1 + 1e-15) + x1
            if lon < x_int:
                inside = not inside
    return inside


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


def fetch_dem_rest(bbox: tuple[float, float, float, float], size: int = 1200):
    """DEM via 3DEP ImageServer (same fallback pattern as Day 6)."""
    params = {
        "bbox": ",".join(map(str, bbox)),
        "bboxSR": "4326",
        "imageSR": "4326",
        "size": f"{size},{size}",
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


def hillshade(dem: np.ndarray, azimuth: float = 315.0, altitude: float = 45.0) -> np.ndarray:
    """Simple GDAL-style hillshade from a DEM array (meters)."""
    dy, dx = np.gradient(np.nan_to_num(dem, nan=np.nanmedian(dem)))
    # rough cell size in meters for geographic data near 34.7°N
    cell = 10.0
    slope = np.pi / 2.0 - np.arctan(np.hypot(dx / cell, dy / cell))
    aspect = np.arctan2(-dx, dy)
    az = np.radians(azimuth)
    alt = np.radians(altitude)
    shaded = np.sin(alt) * np.sin(slope) + np.cos(alt) * np.cos(slope) * np.cos(az - aspect)
    shaded = np.clip(shaded, 0, 1)
    return shaded


def lonlat_grids(dem) -> tuple[np.ndarray, np.ndarray]:
    """Return lon/lat mesh for dem DataArray (y, x)."""
    x = dem.x.values
    y = dem.y.values
    lon, lat = np.meshgrid(x, y)
    return lon, lat


def lake_mask(lon: np.ndarray, lat: np.ndarray, dem: np.ndarray) -> np.ndarray:
    mask = np.zeros(dem.shape, dtype=bool)
    # Vectorized-ish loop on coarse grid is fine at ~10 m / small bbox
    for r in range(dem.shape[0]):
        for c in range(dem.shape[1]):
            if point_in_ring(float(lon[r, c]), float(lat[r, c]), LAKE_RING):
                # Prefer wet cells near/below pool, but keep polygon even if DEM is noisy
                if dem[r, c] <= POOL_ELEV_M + 8.0 or math.isnan(float(dem[r, c])):
                    mask[r, c] = True
                elif dem[r, c] <= POOL_ELEV_M + 25.0:
                    # shallow shoreline fringe inside polygon
                    mask[r, c] = True
    # Fill any interior holes lightly by also marking very flat low cells near dam
    return mask


def _polyline_length(pts: list[tuple[float, float]]) -> list[float]:
    dists = [0.0]
    for i in range(1, len(pts)):
        lon0, lat0 = pts[i - 1]
        lon1, lat1 = pts[i]
        # equirectangular meters
        mx = (lon1 - lon0) * 111_320 * math.cos(math.radians((lat0 + lat1) / 2))
        my = (lat1 - lat0) * 110_540
        dists.append(dists[-1] + math.hypot(mx, my))
    return dists


def _project_to_polyline(
    lon: float, lat: float, pts: list[tuple[float, float]], cum: list[float]
) -> tuple[float, float, float]:
    """Return (along_m, dist_to_line_m, elev_along) for nearest segment."""
    best_d = 1e18
    best_along = 0.0
    best_t = 0.0
    total = cum[-1] or 1.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        vx, vy = x1 - x0, y1 - y0
        wx, wy = lon - x0, lat - y0
        seg2 = vx * vx + vy * vy
        t = 0.0 if seg2 == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / seg2))
        px, py = x0 + t * vx, y0 + t * vy
        mx = (lon - px) * 111_320 * math.cos(math.radians(lat))
        my = (lat - py) * 110_540
        d = math.hypot(mx, my)
        if d < best_d:
            best_d = d
            best_along = cum[i] + t * (cum[i + 1] - cum[i])
            best_t = best_along / total
    # Bed elevation: linear drop from head (~pool) toward dam toe
    elev = POOL_ELEV_M - 8.0 + best_t * (DAM_TOE_M - (POOL_ELEV_M - 8.0))
    # Actually: head of lake arms near pool surface; bed deepens toward dam
    head_bed = POOL_ELEV_M - 5.0
    elev = head_bed + best_t * (DAM_TOE_M - head_bed)
    return best_along, best_d, elev


def carve_utopia(dem: np.ndarray, lon: np.ndarray, lat: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Replace lake cells with a schematic valley + river corridor."""
    out = dem.copy()
    chat_cum = _polyline_length(CHATTOOGA_THALWEG)
    tall_cum = _polyline_length(TALLULAH_THALWEG)
    valley_half_width = 180.0  # meters

    rows, cols = np.where(mask)
    for r, c in zip(rows, cols):
        lo, la = float(lon[r, c]), float(lat[r, c])
        _, d1, e1 = _project_to_polyline(lo, la, CHATTOOGA_THALWEG, chat_cum)
        _, d2, e2 = _project_to_polyline(lo, la, TALLULAH_THALWEG, tall_cum)
        if d1 <= d2:
            dist, bed = d1, e1
        else:
            dist, bed = d2, e2
        # Parabolic valley walls up toward pool rim
        t = min(1.0, dist / valley_half_width)
        wall = bed + t * t * (POOL_ELEV_M - bed)
        # Keep a bit below surrounding DEM rim when outside core channel
        rim = float(dem[r, c]) if not math.isnan(float(dem[r, c])) else POOL_ELEV_M
        carved = min(wall, rim - 1.0) if t > 0.85 else wall
        out[r, c] = carved
    return out


def river_mask(lon: np.ndarray, lat: np.ndarray, width_m: float = 35.0) -> np.ndarray:
    mask = np.zeros(lon.shape, dtype=bool)
    chat_cum = _polyline_length(CHATTOOGA_THALWEG)
    tall_cum = _polyline_length(TALLULAH_THALWEG)
    for r in range(lon.shape[0]):
        for c in range(lon.shape[1]):
            lo, la = float(lon[r, c]), float(lat[r, c])
            _, d1, _ = _project_to_polyline(lo, la, CHATTOOGA_THALWEG, chat_cum)
            _, d2, _ = _project_to_polyline(lo, la, TALLULAH_THALWEG, tall_cum)
            if min(d1, d2) <= width_m:
                mask[r, c] = True
    return mask


def colorize_now(hs: np.ndarray, lake: np.ndarray) -> np.ndarray:
    """RGB uint8 hillshade with blue lake."""
    base = (hs * 255).astype(np.float32)
    rgb = np.stack([base * 0.92, base * 0.95, base * 0.88], axis=-1)
    # Lake tint
    water = np.array([42.0, 98.0, 148.0])
    depth = 0.55 + 0.35 * (1.0 - hs)
    for i in range(3):
        channel = rgb[..., i]
        channel[lake] = water[i] * depth[lake] + channel[lake] * (1.0 - 0.75)
        rgb[..., i] = channel
    return np.clip(rgb, 0, 255).astype(np.uint8)


def colorize_utopia(hs: np.ndarray, rivers: np.ndarray, was_lake: np.ndarray) -> np.ndarray:
    base = (hs * 255).astype(np.float32)
    # Slightly greener restored bowl
    rgb = np.stack([base * 0.85, base * 0.95, base * 0.78], axis=-1)
    restored = was_lake & ~rivers
    rgb[restored, 0] = rgb[restored, 0] * 0.9 + 40
    rgb[restored, 1] = rgb[restored, 1] * 0.85 + 70
    rgb[restored, 2] = rgb[restored, 2] * 0.75 + 35
    water = np.array([55.0, 130.0, 170.0])
    for i in range(3):
        ch = rgb[..., i]
        ch[rivers] = water[i] * 0.85 + ch[rivers] * 0.15
        rgb[..., i] = ch
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


def save_static_dual(path: Path, now_rgb: np.ndarray, utopia_rgb: np.ndarray) -> None:
    import matplotlib.pyplot as plt
    from matplotlib import patheffects as pe

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 7), facecolor="#10140f")
    titles = ("Now — Lake Tugalo", "Utopia — Tugalo undammed")
    for ax, img, title in zip(axes, (now_rgb, utopia_rgb), titles):
        ax.imshow(img, interpolation="bilinear")
        ax.set_axis_off()
        ax.set_title(title, color="#f2efe4", fontsize=12, pad=8, fontfamily="serif")
    stroke = [pe.withStroke(linewidth=3, foreground="#10140f")]
    fig.suptitle(
        "Utopia: Tugalo Undammed",
        color="#ffe66d",
        fontsize=16,
        fontfamily="serif",
        y=0.98,
    )
    fig.text(
        0.5,
        0.02,
        "Schematic restored valley (not surveyed bathymetry). DEM: USGS 3DEP. Dam: Georgia Power Tugalo.",
        ha="center",
        color="#9a9688",
        fontsize=8,
        path_effects=stroke,
    )
    # Dam marker approx on both panels
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(path, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Wrote {path}")


def write_bounds(path: Path, dem) -> None:
    # Leaflet LatLngBounds: [[south, west], [north, east]]
    left, bottom, right, top = dem.rio.bounds()
    payload = {
        "bounds": [[bottom, left], [top, right]],
        "dam": {"lat": DAM[1], "lon": DAM[0]},
        "note": "Schematic Lake Tugalo / utopia carve for Day 8 swipe overlays",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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
    lake = lake_mask(lon, lat, dem_vals)
    print(f"Lake mask cells: {int(lake.sum())}")

    hs_now = hillshade(dem_vals)
    # Flatten lake surface for "now" hillshade feel
    dem_now = dem_vals.copy()
    dem_now[lake] = POOL_ELEV_M
    hs_now = hillshade(dem_now)

    utopia_vals = carve_utopia(dem_vals, lon, lat, lake)
    hs_utopia = hillshade(utopia_vals)
    rivers = river_mask(lon, lat) & lake  # rivers only where lake was / confluence bowl
    # Extend river slightly beyond mask along thalweg
    rivers = river_mask(lon, lat)

    now_rgb = colorize_now(hs_now, lake)
    utopia_rgb = colorize_utopia(hs_utopia, rivers, lake)

    save_png(args.now, now_rgb)
    save_png(args.utopia, utopia_rgb)
    save_static_dual(args.static, now_rgb, utopia_rgb)
    write_bounds(args.bounds, dem)

    # Persist rasters
    utopia_da = dem.copy(data=utopia_vals)
    save_geotiff(args.dem_out, dem)
    save_geotiff(args.utopia_dem_out, utopia_da)
    return 0


if __name__ == "__main__":
    sys.exit(main())
