#!/usr/bin/env python3
"""
Day 6 — Vintage: historic USGS Chattanooga topo + modern 3DEP hillshade.

Open-source stack: py3dep (hillshade), rasterio/rioxarray (align), matplotlib (export).

Prerequisites
-------------
1. pip install -r 2026/06_vintage/requirements.txt
   (py3dep, rasterio, rioxarray, matplotlib)
2. Download an HTMC GeoTIFF from TopoView for Chattanooga, TN:
   https://ngmdb.usgs.gov/topoview/
   Preferred: Chattanooga 1:24,000 (1940 / printed 1956)
   Save to: data/raw/chattanooga_htmc.tif  (or pass --topo)

Corporate proxy: if HTTPS to USGS fails behind Zscaler, configure the
script/env to trust your local Zscaler certificate path. Do not disable
TLS verification for routine use.

Usage
-----
  python scripts/day06_vintage_chattanooga.py
  python scripts/day06_vintage_chattanooga.py --topo data/raw/chattanooga_htmc.tif
  python scripts/day06_vintage_chattanooga.py --layer "Hillshade Multidirectional" --blend soft-light
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from pathlib import Path

import numpy as np

import _env  # noqa: F401  (loads .env for SSL_CERT_FILE / REQUESTS_CA_BUNDLE)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOPO = REPO_ROOT / "data" / "raw" / "chattanooga_htmc.tif"
DEFAULT_HILL_OUT = REPO_ROOT / "data" / "processed" / "chattanooga_hillshade.tif"
DEFAULT_EXPORT = REPO_ROOT / "2026" / "images" / "day-06.png"
DEFAULT_HISTORIC_EXPORT = REPO_ROOT / "2026" / "images" / "day-06-historic.png"

# Approximate Chattanooga 7.5' quad (WGS84). Overridden by topo bounds when available.
DEFAULT_BBOX = (-85.375, 34.95, -85.20, 35.125)  # west, south, east, north
THREE_DEP_IMAGE_SERVICE = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"
)


def _require_imports(require_py3dep: bool = True):
    missing = []
    if require_py3dep:
        try:
            import py3dep  # noqa: F401
        except ImportError:
            missing.append("py3dep")
    try:
        import rasterio  # noqa: F401
    except ImportError:
        missing.append("rasterio")
    try:
        import rioxarray  # noqa: F401
    except ImportError:
        missing.append("rioxarray")
    try:
        import matplotlib.pyplot as plt  # noqa: F401
    except ImportError:
        missing.append("matplotlib")
    if missing:
        raise SystemExit(
            "Missing packages: "
            + ", ".join(missing)
            + "\nInstall with: pip install -r 2026/06_vintage/requirements.txt"
        )


def fetch_hillshade(bbox: tuple[float, float, float, float], layer: str, resolution: float):
    """Pull a 3DEP hillshade layer for bbox (west, south, east, north) in EPSG:4326."""
    import py3dep

    print(f"Fetching 3DEP '{layer}' @ {resolution} m for {bbox} …")
    hill = py3dep.get_map(
        layer,
        geometry=bbox,
        resolution=resolution,
        geo_crs="EPSG:4326",
        crs="EPSG:4326",
    )
    return hill


def fetch_hillshade_rest(
    bbox: tuple[float, float, float, float], layer: str, size: int = 2048
):
    """Fetch a rendered 3DEP hillshade from its REST image service.

    py3dep currently uses the service's WMS endpoint. Retain this small direct
    fallback because the WMS response can be unavailable while the official
    ImageServer remains available.
    """
    import rioxarray  # noqa: F401  -- registers the rio accessor on xarray
    import xarray as xr
    from rasterio.io import MemoryFile

    params = {
        "bbox": ",".join(map(str, bbox)),
        "bboxSR": "4326",
        "imageSR": "4326",
        "size": f"{size},{size}",
        "format": "tiff",
        "renderingRule": json.dumps({"rasterFunction": layer}),
        "f": "image",
    }
    request = Request(
        f"{THREE_DEP_IMAGE_SERVICE}?{urlencode(params)}",
        headers={"User-Agent": "30-Day-Map-Challenge-Day-06"},
    )
    print(f"Fetching 3DEP '{layer}' from ImageServer fallback …")
    with urlopen(request, timeout=120) as response:  # noqa: S310 -- fixed USGS URL
        payload = response.read()

    if payload.lstrip().startswith(b"{"):
        raise RuntimeError(payload.decode("utf-8", errors="replace"))

    with MemoryFile(payload) as memfile, memfile.open() as dataset:
        values = dataset.read(1, masked=True)
        transform = dataset.transform
        x = transform.c + (np.arange(dataset.width) + 0.5) * transform.a
        y = transform.f + (np.arange(dataset.height) + 0.5) * transform.e
        hill = xr.DataArray(values, dims=("y", "x"), coords={"y": y, "x": x})
        hill = hill.rio.write_crs(dataset.crs or "EPSG:4326")
        return hill.rio.write_transform(transform)


def get_hillshade(bbox: tuple[float, float, float, float], layer: str, resolution: float):
    """Fetch 3DEP hillshade from the reliable ImageServer endpoint."""
    try:
        return fetch_hillshade_rest(bbox, layer)
    except Exception as exc:  # noqa: BLE001 -- preserve a usable official 3DEP fallback
        print(f"Warning: ImageServer request failed ({exc}); trying py3dep WMS fallback.")
        return fetch_hillshade(bbox, layer, resolution)


def load_topo(path: Path):
    """Open HTMC GeoTIFF; return DataArray and (west, south, east, north) in EPSG:4326."""
    import rioxarray as rxr

    if not path.is_file():
        raise SystemExit(
            f"Topo GeoTIFF not found: {path}\n"
            "Download from TopoView (https://ngmdb.usgs.gov/topoview/) "
            "and save as data/raw/chattanooga_htmc.tif, or pass --topo."
        )

    topo = rxr.open_rasterio(path, masked=True)
    # Bounds in native CRS → WGS84 for py3dep
    bounds = topo.rio.bounds()  # left, bottom, right, top
    try:
        import pyproj
        from shapely.geometry import box
        from shapely.ops import transform

        src_crs = topo.rio.crs
        if src_crs is None:
            raise ValueError("Topo has no CRS")
        if src_crs.to_epsg() == 4326 or "4326" in str(src_crs):
            bbox = (bounds[0], bounds[1], bounds[2], bounds[3])
        else:
            project = pyproj.Transformer.from_crs(
                src_crs, "EPSG:4326", always_xy=True
            ).transform
            geom = transform(project, box(*bounds))
            minx, miny, maxx, maxy = geom.bounds
            bbox = (minx, miny, maxx, maxy)
    except Exception as exc:  # noqa: BLE001 — fall back to DEFAULT_BBOX
        print(f"Warning: could not derive WGS84 bbox from topo ({exc}); using default.")
        bbox = DEFAULT_BBOX

    return topo, bbox


def downsample_for_export(topo, max_dimension: int):
    """Limit a scan to a practical gallery-export resolution before alignment."""
    x_dim, y_dim = topo.rio.x_dim, topo.rio.y_dim
    longest_side = max(topo.sizes[x_dim], topo.sizes[y_dim])
    step = max(1, int(np.ceil(longest_side / max_dimension)))
    if step > 1:
        print(f"Downsampling historic scan by {step}× for gallery export …")
        topo = topo.isel({x_dim: slice(None, None, step), y_dim: slice(None, None, step)})
    return topo


def align_hill_to_topo(hill, topo):
    """Reproject hillshade DataArray onto the topo grid."""
    # Ensure CRS and write CRS if py3dep left it as 4326 without rio accessor metadata
    if not hasattr(hill, "rio"):
        raise SystemExit("Hillshade is not a rioxarray-compatible DataArray.")

    if hill.rio.crs is None:
        hill = hill.rio.write_crs("EPSG:4326")

    target_crs = topo.rio.crs
    if target_crs is None:
        raise SystemExit("Topo raster has no CRS; cannot align hillshade.")

    hill_matched = hill.rio.reproject_match(topo)
    return hill_matched


def _to_rgb01(arr: np.ndarray) -> np.ndarray:
    """Convert raster array to float RGB in [0, 1], shape (H, W, 3)."""
    a = np.asarray(arr, dtype=np.float64)
    if a.ndim == 3 and a.shape[0] in (1, 3, 4):
        # band-first
        a = np.moveaxis(a, 0, -1)
    if a.ndim == 2:
        a = np.stack([a, a, a], axis=-1)
    if a.shape[-1] == 4:
        a = a[..., :3]
    # Scale 0–255 or 0–1
    finite = a[np.isfinite(a)]
    if finite.size and finite.max() > 1.5:
        a = a / 255.0
    a = np.clip(np.nan_to_num(a, nan=1.0), 0.0, 1.0)
    return a


def _to_hill01(arr: np.ndarray) -> np.ndarray:
    """Hillshade to float [0, 1], shape (H, W)."""
    h = np.asarray(arr, dtype=np.float64)
    if h.ndim == 3:
        h = h[0] if h.shape[0] <= 4 else h[..., 0]
    finite = h[np.isfinite(h)]
    if finite.size == 0:
        return np.ones(h.shape, dtype=np.float64)
    lo, hi = np.nanpercentile(finite, [2, 98])
    if hi <= lo:
        lo, hi = float(np.nanmin(finite)), float(np.nanmax(finite))
    if hi <= lo:
        return np.ones_like(h)
    h = (h - lo) / (hi - lo)
    return np.clip(np.nan_to_num(h, nan=0.5), 0.0, 1.0)


def multiply_blend(topo_rgb: np.ndarray, hill: np.ndarray, topo_weight: float) -> np.ndarray:
    """Weighted multiply: keep paper look, add relief."""
    hill3 = hill[..., None]
    # Mix flat topo with shaded topo
    shaded = topo_rgb * (0.35 + 0.65 * hill3)
    out = topo_weight * shaded + (1.0 - topo_weight) * hill3
    return np.clip(out, 0.0, 1.0)


def soft_light_blend(topo_rgb: np.ndarray, hill: np.ndarray, topo_weight: float) -> np.ndarray:
    """Soft-light hillshade under topo."""
    base = hill[..., None]
    overlay = topo_rgb
    # Standard soft-light (Photoshop-ish), base = hill, overlay = topo
    soft = (1 - 2 * overlay) * base**2 + 2 * overlay * base
    out = topo_weight * soft + (1.0 - topo_weight) * base
    return np.clip(out, 0.0, 1.0)


def render(
    blended: np.ndarray,
    export_path: Path,
    title: str,
    subtitle: str,
    dpi: int,
) -> None:
    import matplotlib.pyplot as plt
    from matplotlib import patheffects as pe

    export_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 12), facecolor="#f3ecd8")
    ax.set_facecolor("#f3ecd8")
    ax.imshow(blended, interpolation="bilinear")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    stroke = [pe.withStroke(linewidth=3, foreground="#f3ecd8")]
    ax.text(
        0.02,
        0.98,
        title,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=18,
        fontfamily="serif",
        color="#2b2418",
        path_effects=stroke,
    )
    ax.text(
        0.02,
        0.945,
        subtitle,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        fontfamily="serif",
        color="#4a4030",
        path_effects=stroke,
    )
    ax.text(
        0.98,
        0.015,
        "USGS HTMC + USGS 3DEP (py3dep)  ·  #30DayMapChallenge Day 6 — Vintage",
        transform=ax.transAxes,
        va="bottom",
        ha="right",
        fontsize=7,
        fontfamily="serif",
        color="#5a5040",
    )

    fig.tight_layout(pad=0.4)
    fig.savefig(export_path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Wrote {export_path}")


def save_historic_preview(topo_rgb: np.ndarray, export_path: Path) -> None:
    """Write the unblended historic scan for the Day 6 swipe map."""
    import matplotlib.pyplot as plt

    export_path.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(export_path, topo_rgb)
    print(f"Wrote {export_path}")


def save_hillshade_geotiff(hill, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    hill.rio.to_raster(path)
    print(f"Wrote {path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--topo", type=Path, default=DEFAULT_TOPO, help="Path to HTMC GeoTIFF")
    p.add_argument(
        "--layer",
        default="Hillshade Gray",
        choices=["Hillshade Gray", "Hillshade Multidirectional", "GreyHillshade Elevation Fill"],
        help="3DEP hillshade layer name for py3dep.get_map",
    )
    p.add_argument("--resolution", type=float, default=10.0, help="Hillshade resolution in meters")
    p.add_argument(
        "--blend",
        choices=["multiply", "soft-light"],
        default="multiply",
        help="Composite mode",
    )
    p.add_argument(
        "--topo-weight",
        type=float,
        default=0.65,
        help="Weight of topo/paper look vs hillshade (0–1)",
    )
    p.add_argument("--title", default="Chattanooga, Tenn.")
    p.add_argument(
        "--subtitle",
        default="Historic USGS topographic sheet with modern 3DEP hillshade",
    )
    p.add_argument("--export", type=Path, default=DEFAULT_EXPORT)
    p.add_argument(
        "--historic-export",
        type=Path,
        default=DEFAULT_HISTORIC_EXPORT,
        help="Unblended historic image used by the Day 6 swipe map",
    )
    p.add_argument("--hill-out", type=Path, default=DEFAULT_HILL_OUT)
    p.add_argument("--dpi", type=int, default=200)
    p.add_argument(
        "--max-dimension",
        type=int,
        default=2400,
        help="Maximum historic-scan dimension used for the gallery export",
    )
    p.add_argument(
        "--bbox-only",
        action="store_true",
        help="Skip topo file; fetch hillshade for DEFAULT_BBOX and export grayscale only (smoke test)",
    )
    p.add_argument(
        "--historic-only",
        action="store_true",
        help="Write only the unblended historic preview used by the swipe map",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    _require_imports(require_py3dep=not args.historic_only)

    if args.bbox_only:
        hill = get_hillshade(DEFAULT_BBOX, args.layer, args.resolution)
        if hill.rio.crs is None:
            hill = hill.rio.write_crs("EPSG:4326")
        save_hillshade_geotiff(hill, args.hill_out)
        h = _to_hill01(hill.values)
        rgb = np.stack([h, h, h], axis=-1)
        render(
            rgb,
            args.export,
            args.title + " (hillshade only)",
            "Smoke test — add HTMC GeoTIFF for full vintage composite",
            args.dpi,
        )
        return 0

    topo, bbox = load_topo(args.topo)
    topo = downsample_for_export(topo, args.max_dimension)
    topo_rgb = _to_rgb01(topo.values)
    if args.historic_only:
        save_historic_preview(topo_rgb, args.historic_export)
        return 0

    hill = get_hillshade(bbox, args.layer, args.resolution)
    if getattr(hill, "rio", None) is not None and hill.rio.crs is None:
        hill = hill.rio.write_crs("EPSG:4326")

    hill_matched = align_hill_to_topo(hill, topo)
    save_hillshade_geotiff(hill_matched, args.hill_out)

    save_historic_preview(topo_rgb, args.historic_export)
    hill01 = _to_hill01(hill_matched.values)

    # Match spatial dims if band/y/x ordering left a slight off-by-one after match
    h, w = hill01.shape
    if topo_rgb.shape[0] != h or topo_rgb.shape[1] != w:
        # reproject_match should align; crop to intersection as safety
        h = min(h, topo_rgb.shape[0])
        w = min(w, topo_rgb.shape[1])
        topo_rgb = topo_rgb[:h, :w]
        hill01 = hill01[:h, :w]

    if args.blend == "soft-light":
        blended = soft_light_blend(topo_rgb, hill01, args.topo_weight)
    else:
        blended = multiply_blend(topo_rgb, hill01, args.topo_weight)

    render(blended, args.export, args.title, args.subtitle, args.dpi)
    return 0


if __name__ == "__main__":
    sys.exit(main())
