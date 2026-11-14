"""Day 15 — Inside out: North Chickamauga Creek Gorge, turned over.

The state-park polygon is TDEC's March 2024 boundary, TSP-0322. USGS 3DEP
elevations in that frame are reflected through their midpoint:

    inverted = highest + lowest - elevation

The creek bottom becomes the crest. The rims become the trough. The range
is unchanged. The gallery sheet is a matplotlib relief. forge3d, when it
imports and a GPU is available, writes a second plate under data/processed/.

The GeoTIFF and the park GeoJSON are cached under data/raw/, which is
gitignored. A corporate proxy may need the local Zscaler CA on
SSL_CERT_FILE. Do not disable TLS verification.

Run from the repository root:

    python scripts/build_day15_inside_out.py
    python scripts/build_day15_inside_out.py --refresh
    python scripts/build_day15_inside_out.py --no-forge
"""

from __future__ import annotations

import argparse
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

import _env  # noqa: F401  (loads .env for SSL_CERT_FILE / REQUESTS_CA_BUNDLE)
from build_day05_terrain import meters_per_degree, read_usgs_elevation

PARK_UID = "TSP-0322"
PARK_NAME = "North Chickamauga Creek Gorge State Park"
PARK_LAYER = (
    "https://services5.arcgis.com/bPacKTm9cauMXVfn/arcgis/rest/services/"
    "State_Park_Boundaries_Primary_March_2024_view2/FeatureServer/331/query"
)
EXPORT_URL = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer/exportImage"
)

PAD_M = 450.0
MAX_CELLS = 1000
TARGET_CELL_M = 15.0
SHEET_IN = (12.0, 9.0)  # 4:3, matching the gallery card
SHEET_DPI = 200

ROOT = Path(__file__).resolve().parents[1]
RAW_PARK = ROOT / "data" / "raw" / "day15-north-chickamauga-park.geojson"
RAW_DEM = ROOT / "data" / "raw" / "day15-3dep-north-chickamauga.tif"
OUT_IMAGE = ROOT / "2026" / "images" / "day-15.png"
OUT_META = ROOT / "2026" / "15_inside_out" / "bounds.json"
FORGE_PNG = ROOT / "data" / "processed" / "day15-forge3d.png"

PAPER = "#16130F"
INK = "#F3F0EA"
QUIET = "#C4B8A5"
CREST = np.array([0.965, 0.937, 0.890])
MID = np.array([0.620, 0.420, 0.250])
TROUGH = np.array([0.090, 0.075, 0.060])


def fetch(url: str, timeout: int) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "cts-30-day-map-challenge"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers.get("Content-Type", "")


def load_park(refresh: bool) -> dict:
    """One GeoJSON feature for the state park, in EPSG:4326."""
    RAW_PARK.parent.mkdir(parents=True, exist_ok=True)
    if refresh or not RAW_PARK.exists() or RAW_PARK.stat().st_size == 0:
        query = urllib.parse.urlencode(
            {
                "where": f"TSP_UID='{PARK_UID}'",
                "outFields": "PRIMARY_NAME__LONG_,TSP_UID,Website_URL",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "geojson",
            }
        )
        payload, _ = fetch(f"{PARK_LAYER}?{query}", timeout=120)
        RAW_PARK.write_bytes(payload)
    document = json.loads(RAW_PARK.read_text(encoding="utf-8"))
    features = document.get("features") or []
    if len(features) != 1:
        raise RuntimeError(f"Expected one park feature, found {len(features)}.")
    feature = features[0]
    name = (feature.get("properties") or {}).get("PRIMARY_NAME__LONG_")
    if name and name != PARK_NAME:
        print(f"Warning: layer name is {name!r}.", flush=True)
    return feature


def park_geometry(feature: dict):
    from shapely.geometry import shape

    geom = shape(feature["geometry"])
    if geom.is_empty or not geom.geom_type.endswith("Polygon"):
        raise RuntimeError(f"Park geometry is {geom.geom_type}, expected a polygon.")
    minx, miny, maxx, maxy = geom.bounds
    if not (-90 < minx < -80 and 34 < miny < 36):
        raise RuntimeError(f"Park bounds are not in the Hamilton County area: {geom.bounds}.")
    return geom


def frame_bounds(geom) -> tuple[float, float, float, float]:
    """Park bounds plus a slim pad, in degrees."""
    minx, miny, maxx, maxy = geom.bounds
    lat = (miny + maxy) / 2
    m_lat, m_lon = meters_per_degree(lat)
    pad_lat = PAD_M / m_lat
    pad_lon = PAD_M / m_lon
    return minx - pad_lon, miny - pad_lat, maxx + pad_lon, maxy + pad_lat


def download_dem(west: float, south: float, east: float, north: float, cell_m: float) -> bytes:
    m_lat, m_lon = meters_per_degree((south + north) / 2)
    cols = max(2, min(MAX_CELLS, round((east - west) * m_lon / cell_m)))
    rows = max(2, min(MAX_CELLS, round((north - south) * m_lat / cell_m)))
    query = (
        f"?bbox={west},{south},{east},{north}&bboxSR=4326&imageSR=4326"
        f"&size={cols},{rows}&format=tiff&pixelType=F32"
        "&interpolation=RSP_BilinearInterpolation&f=image"
    )
    print(f"downloading 3DEP {cols}x{rows}", flush=True)
    payload, content_type = fetch(EXPORT_URL + query, timeout=180)
    if not payload.startswith(b"II"):
        raise RuntimeError(f"3DEP did not return a TIFF ({content_type}, {len(payload)} bytes).")
    return payload


def choose_cell(west: float, south: float, east: float, north: float) -> float:
    m_lat, m_lon = meters_per_degree((south + north) / 2)
    long_m = max((east - west) * m_lon, (north - south) * m_lat)
    return max(TARGET_CELL_M, long_m / MAX_CELLS)


def invert(elevation: np.ndarray, inside: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Reflect elevation through the midpoint of the park samples."""
    sample = elevation[inside]
    sample = sample[np.isfinite(sample)]
    if sample.size == 0:
        raise RuntimeError("No 3DEP samples fall inside the park.")
    low = float(sample.min())
    high = float(sample.max())
    inverted = (high + low) - elevation
    return inverted.astype(np.float32), low, high


def hillshade(z: np.ndarray, cell_m: float, azimuth: float = 315.0, altitude: float = 32.0) -> np.ndarray:
    """ESRI hillshade. Row 0 is north, so a positive row step points south."""
    south, east = np.gradient(z.astype(np.float64), cell_m, cell_m)
    dz_north = -south
    slope = np.arctan(np.hypot(east, dz_north))
    aspect = np.arctan2(dz_north, -east)
    zenith = np.radians(90.0 - altitude)
    az = np.radians(360.0 - azimuth + 90.0)
    shaded = np.cos(zenith) * np.cos(slope) + np.sin(zenith) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(shaded, 0.0, 1.0)


def relief_rgb(z: np.ndarray, low: float, high: float) -> np.ndarray:
    """Light is the crest (former creek). Dark is the trough (former rim)."""
    span = high - low if high > low else 1.0
    t = np.clip((z - low) / span, 0.0, 1.0)[..., None]
    # Two stops: trough -> clay -> crest. t is already the inverted height.
    clay = MID
    low_stop = TROUGH + (t / 0.55) * (clay - TROUGH)
    high_stop = clay + ((t - 0.55) / 0.45) * (CREST - clay)
    rgb = np.where(t < 0.55, low_stop, high_stop)
    return np.clip(rgb, 0.0, 1.0)


def shade_rgb(rgb: np.ndarray, shade: np.ndarray) -> np.ndarray:
    """Keep the hypsometric hue and let the shade do the form."""
    weight = 0.42 + 0.58 * shade[..., None]
    return np.clip(rgb * weight, 0.0, 1.0)


def display_step(rows: int, cols: int, limit: int = 260) -> int:
    return max(1, math.ceil(max(rows, cols) / limit))


def exaggeration(z: np.ndarray, cell_m: float) -> float:
    """Lift the relief until the vertical span is about two-fifths of the width."""
    relief = float(np.nanmax(z) - np.nanmin(z))
    span = max(z.shape) * cell_m
    if relief <= 0:
        return 1.0
    return float(np.clip(0.40 * span / relief, 1.5, 6.0))


def try_forge(z: np.ndarray, cell_m: float, exag: float, samples: int) -> Path | None:
    """Path-trace the same grid. A flat or missing frame is treated as no render."""
    try:
        import forge3d as f3d
    except ImportError:
        print("forge3d is not installed; the sheet uses the matplotlib relief.", flush=True)
        return None

    FORGE_PNG.parent.mkdir(parents=True, exist_ok=True)
    rows, cols = z.shape
    diagonal = max(rows, cols) * cell_m
    try:
        scene = f3d.MapScene(
            terrain=f3d.TerrainSource(
                data=np.ascontiguousarray(z, dtype=np.float32),
                # Local north-up meter grid. UTM 16N names the frame so
                # validation can run. In-memory samples are not reprojected.
                crs="EPSG:32616",
                metadata={
                    "width": cols,
                    "height": rows,
                    "resolution": [cell_m, cell_m],
                },
                nodata_policy="fill",
            ),
            camera=f3d.OrbitCamera(
                target=(0.0, 0.0, float(np.nanmean(z))),
                # Far enough to hold the whole grid. The first pass, at
                # 1.25 times the long side, sat inside the relief.
                distance=diagonal * 3.2,
                azimuth_deg=210.0,
                elevation_deg=42.0,
                fov_deg=38.0,
            ),
            lighting=f3d.LightingPreset(
                name="default",
                intensity=1.35,
                settings={
                    "exaggeration": exag,
                    "sun": {"azimuth_deg": 315.0, "elevation_deg": 28.0},
                },
            ),
            output=f3d.OutputSpec(
                width=1800,
                height=1200,
                path=str(FORGE_PNG),
                samples=samples,
                denoiser="atrous",
            ),
        )
        report = scene.validate()
        if report.render_blocked(scene.render_policy):
            print(f"forge3d blocked the render: {report}", flush=True)
            return None
        print(f"rendering forge3d {samples} samples", flush=True)
        scene.render()
    except Exception as exc:  # noqa: BLE001 -- the matplotlib sheet is the fallback
        print(f"forge3d render failed ({type(exc).__name__}: {exc}).", flush=True)
        return None
    if not FORGE_PNG.exists() or FORGE_PNG.stat().st_size < 1000:
        print("forge3d did not write a frame.", flush=True)
        return None
    return FORGE_PNG


def forge_is_usable(path: Path) -> bool:
    from matplotlib.image import imread

    image = imread(path)
    if image.ndim == 3:
        image = image[..., :3]
    return float(image.std()) > 0.04


def font_family() -> str:
    from matplotlib import font_manager

    names = {face.name for face in font_manager.fontManager.ttflist}
    for candidate in ("Georgia", "Palatino Linotype", "Liberation Serif", "DejaVu Serif"):
        if candidate in names:
            return candidate
    return "DejaVu Serif"


def rings(geom):
    if geom.geom_type == "Polygon":
        yield geom.exterior
        yield from geom.interiors
    elif geom.geom_type == "MultiPolygon":
        for part in geom.geoms:
            yield from rings(part)


def draw_sheet(
    z: np.ndarray,
    west: float,
    south: float,
    east: float,
    north: float,
    cell_m: float,
    low: float,
    high: float,
    geom,
    exag: float,
    hero: Path | None,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.image import imread

    step = display_step(*z.shape)
    view = z[::step, ::step]
    view_cell = cell_m * step
    shade = hillshade(view, view_cell)
    rgb = shade_rgb(relief_rgb(view, low, high), shade)
    rows, cols = view.shape
    xs = (np.arange(cols) - (cols - 1) / 2.0) * view_cell
    ys = ((rows - 1) / 2.0 - np.arange(rows)) * view_cell
    east_m, north_m = np.meshgrid(xs, ys)
    drawn = view * exag

    face = font_family()
    fig = plt.figure(figsize=SHEET_IN, dpi=SHEET_DPI, facecolor=PAPER)
    fig.suptitle(
        "Inside Out",
        x=0.055,
        y=0.955,
        ha="left",
        va="top",
        fontsize=28,
        color=INK,
        fontfamily=face,
        fontweight="regular",
    )
    fig.text(
        0.055,
        0.905,
        PARK_NAME,
        ha="left",
        va="top",
        fontsize=13,
        color=QUIET,
        fontfamily=face,
    )
    fig.text(
        0.945,
        0.955,
        "Day 15  ·  Inside out",
        ha="right",
        va="top",
        fontsize=11,
        color=QUIET,
        fontfamily=face,
    )

    if hero is not None:
        ax = fig.add_axes((0.05, 0.16, 0.68, 0.70))
        ax.imshow(imread(hero))
        ax.set_axis_off()
        ax.set_facecolor(PAPER)
    else:
        ax = fig.add_axes((0.02, 0.12, 0.70, 0.74), projection="3d")
        rgba = np.concatenate([rgb, np.ones(rgb.shape[:2] + (1,))], axis=2)
        faces = (rgba[:-1, :-1] + rgba[:-1, 1:] + rgba[1:, :-1] + rgba[1:, 1:]) * 0.25
        ax.plot_surface(
            east_m,
            north_m,
            drawn,
            facecolors=faces,
            rstride=1,
            cstride=1,
            linewidth=0,
            antialiased=False,
            shade=False,
        )
        ax.view_init(elev=26, azim=-58)
        try:
            ax.set_proj_type("ortho")
        except AttributeError:
            pass
        span_x = float(xs[-1] - xs[0])
        span_y = float(ys[0] - ys[-1])
        span_z = float(drawn.max() - drawn.min())
        box = (span_x, span_y, max(span_z, 1.0))
        try:
            ax.set_box_aspect(box, zoom=1.45)
        except TypeError:
            ax.set_box_aspect(box)
        ax.set_xlim(xs[0], xs[-1])
        ax.set_ylim(ys[-1], ys[0])
        ax.set_zlim(float(drawn.min()), float(drawn.max()))
        ax.set_axis_off()
        ax.set_facecolor(PAPER)
        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            axis.pane.fill = False
            axis.pane.set_edgecolor((0, 0, 0, 0))

    inset = fig.add_axes((0.72, 0.40, 0.24, 0.44))
    plan = shade_rgb(relief_rgb(z, low, high), hillshade(z, cell_m))
    inset.imshow(plan, extent=(west, east, south, north), origin="upper", interpolation="bilinear")
    m_lat, m_lon = meters_per_degree((south + north) / 2)
    for ring in rings(geom):
        coords = np.asarray(ring.coords)
        inset.plot(coords[:, 0], coords[:, 1], color=INK, linewidth=0.7, solid_capstyle="round")
    inset.set_xlim(west, east)
    inset.set_ylim(south, north)
    inset.set_aspect(m_lat / m_lon)
    inset.set_axis_off()
    bar_m = 1000.0 if (east - west) * m_lon < 5000 else 2000.0
    bar_deg = bar_m / m_lon
    x0 = west + 0.06 * (east - west)
    y0 = south + 0.07 * (north - south)
    inset.plot([x0, x0 + bar_deg], [y0, y0], color=PAPER, linewidth=2.6, solid_capstyle="butt")
    inset.plot([x0, x0 + bar_deg], [y0, y0], color=INK, linewidth=1.2, solid_capstyle="butt")
    inset.text(
        x0,
        y0 + 0.025 * (north - south),
        f"{bar_m / 1000:.0f} km",
        color=INK,
        fontsize=8,
        fontfamily=face,
        ha="left",
        va="bottom",
    )
    inset.annotate(
        "",
        xy=(east - 0.08 * (east - west), north - 0.08 * (north - south)),
        xytext=(east - 0.08 * (east - west), north - 0.20 * (north - south)),
        arrowprops={"arrowstyle": "-|>", "color": INK, "lw": 0.8},
    )
    inset.text(
        east - 0.08 * (east - west),
        north - 0.055 * (north - south),
        "N",
        color=INK,
        fontsize=8,
        fontfamily=face,
        ha="center",
        va="bottom",
    )

    legend = fig.add_axes((0.74, 0.16, 0.016, 0.18))
    ramp = np.linspace(high, low, 256)[:, None]
    legend.imshow(relief_rgb(ramp, low, high), aspect="auto", origin="upper", extent=(0, 1, low, high))
    legend.set_xlim(0, 1)
    legend.set_xticks([])
    legend.set_yticks([])
    for spine in legend.spines.values():
        spine.set_visible(False)

    # Original elevations. The light end is the creek; the dark end is the rim.
    fig.text(
        0.77,
        0.345,
        f"crest · creek, {low:.0f} m",
        color=QUIET,
        fontsize=8,
        fontfamily=face,
        ha="left",
        va="bottom",
    )
    fig.text(
        0.77,
        0.150,
        f"trough · rim, {high:.0f} m",
        color=QUIET,
        fontsize=8,
        fontfamily=face,
        ha="left",
        va="top",
    )
    fig.text(
        0.055,
        0.075,
        "Elevation reflected through the midpoint of the park. The plan at right is the same surface, north up.",
        color=QUIET,
        fontsize=9,
        fontfamily=face,
        ha="left",
    )
    fig.text(
        0.055,
        0.042,
        "USGS 3DEP  ·  TDEC State Park Boundaries, March 2024  ·  15 November 2026",
        color=QUIET,
        fontsize=8.5,
        fontfamily=face,
        ha="left",
    )

    OUT_IMAGE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_IMAGE, dpi=SHEET_DPI, facecolor=fig.get_facecolor())
    plt.close(fig)


def write_meta(
    west: float,
    south: float,
    east: float,
    north: float,
    cell_m: float,
    low: float,
    high: float,
    exag: float,
    renderer: str,
    shape: tuple[int, int],
) -> None:
    OUT_META.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "park": PARK_NAME,
        "tspUid": PARK_UID,
        "west": round(west, 5),
        "south": round(south, 5),
        "east": round(east, 5),
        "north": round(north, 5),
        "cellM": round(cell_m, 2),
        "rows": shape[0],
        "cols": shape[1],
        "parkMinM": round(low, 1),
        "parkMaxM": round(high, 1),
        "inversion": "highest + lowest - elevation, using samples inside the park",
        "exaggeration": round(exag, 2),
        "renderer": renderer,
        "padM": PAD_M,
    }
    OUT_META.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Ignore the cached park GeoJSON and 3DEP GeoTIFF.")
    parser.add_argument("--no-forge", action="store_true", help="Draw the matplotlib relief and skip forge3d.")
    parser.add_argument("--samples", type=int, default=4, help="forge3d samples per pixel.")
    args = parser.parse_args()
    if args.samples < 1:
        raise SystemExit("--samples must be at least 1.")

    feature = load_park(args.refresh)
    geom = park_geometry(feature)
    west, south, east, north = frame_bounds(geom)
    cell_m = choose_cell(west, south, east, north)
    RAW_DEM.parent.mkdir(parents=True, exist_ok=True)
    if args.refresh or not RAW_DEM.exists() or RAW_DEM.stat().st_size == 0:
        RAW_DEM.write_bytes(download_dem(west, south, east, north, cell_m))
    elevation, west, south, east, north = read_usgs_elevation(RAW_DEM.read_bytes())
    if not np.isfinite(elevation).all():
        fill = float(np.nanmedian(elevation))
        elevation = np.where(np.isfinite(elevation), elevation, fill)
    scale_x = (east - west) / elevation.shape[1]
    scale_y = (north - south) / elevation.shape[0]
    m_lat, m_lon = meters_per_degree((south + north) / 2)
    cell_m = (scale_x * m_lon + scale_y * m_lat) / 2.0

    from shapely import contains_xy

    rows, cols = elevation.shape
    lon = west + (np.arange(cols) + 0.5) * scale_x
    lat = north - (np.arange(rows) + 0.5) * scale_y
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    inside = contains_xy(geom, lon_grid, lat_grid)
    if int(inside.sum()) < 10:
        raise RuntimeError("The park polygon missed the elevation grid.")

    inverted, low, high = invert(elevation, inside)
    exag = exaggeration(inverted, cell_m)
    print(
        f"park {low:.0f}–{high:.0f} m over {inverted.shape[1]}x{inverted.shape[0]} at {cell_m:.1f} m, "
        f"exaggeration {exag:.2f}",
        flush=True,
    )

    renderer = "matplotlib"
    if not args.no_forge:
        rendered = try_forge(inverted, cell_m, exag, args.samples)
        if rendered is not None and forge_is_usable(rendered):
            renderer = "matplotlib+forge3d"
            print(f"forge3d frame {rendered.relative_to(ROOT)}", flush=True)
        elif rendered is not None:
            print("forge3d frame had no relief; the sheet uses the matplotlib model.", flush=True)

    # The gallery sheet is the matplotlib relief so the plan, the model, and
    # the legend share one ramp. The forge3d frame is a separate plate.
    draw_sheet(inverted, west, south, east, north, cell_m, low, high, geom, exag, None)
    write_meta(west, south, east, north, cell_m, low, high, exag, renderer, inverted.shape)
    print(f"wrote {OUT_IMAGE.relative_to(ROOT)} ({renderer})", flush=True)


if __name__ == "__main__":
    main()
