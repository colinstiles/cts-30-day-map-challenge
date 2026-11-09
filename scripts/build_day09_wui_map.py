"""Render the Day 9 static map: WUI structures in Hamilton County.

11 x 17 inch landscape poster. Structure centroids come from FEMA's
WUI Structures V2 service. Each footprint is classed by the Carlson
et al. 2022 building-based WUI raster (default: 100 m neighborhood):

    1  intermix, at least half the neighborhood is wildland vegetation
    2  interface, within 2.4 km of a large wildland patch
    0  not WUI

Both WUI classes also require at least 6.17 buildings per km². The
raster is read from the local USGS data release and is not copied into
the repo. The county extract is cached under data/processed/. A
corporate proxy may need the local Zscaler CA on SSL_CERT_FILE. Do not
disable TLS verification.

Run from the repository root:

    python scripts/build_day09_wui_map.py
    python scripts/build_day09_wui_map.py --neighborhood 500
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import requests
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path as MplPath
from matplotlib.patheffects import withStroke
from shapely.geometry import MultiPolygon, Polygon

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUT_PNG = ROOT / "2026" / "images" / "day-09.png"
OUT_PDF = ROOT / "2026" / "09_urban_rural" / "day-09-11x17.pdf"
COUNTY_PATH = RAW / "hamilton_county.geojson"
HILLSHADE_PATH = RAW / "day09_hillshade.png"
WUI_DIR = Path(
    r"G:\GIS\D_tin-topo\project_data\30_day_map_challenge\2026"
    r"\CONUS_building_footprint_WUI_data"
)
NEIGHBORHOODS = (100, 250, 500, 750, 1000, 1500)
# Metadata datum is WGS 84. Used only when the GeoTIFF has no CRS.
AEA_WGS84 = (
    "+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=23 +lon_0=-96 "
    "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
)

STRUCTURES = (
    "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/"
    "WUI_Structures_V2/FeatureServer/0/query"
)
COUNTY_SOURCES = (
    (
        "https://gis.hamiltontn.gov/server/rest/services/BaseMap/MapServer/16/query"
        "?where=1%3D1&outFields=COUNTY&outSR=4326&f=geojson"
    ),
    (
        "https://maps.cot.tn.gov/hosting/rest/services/Hosted/TN_Counties/FeatureServer/0/query"
        "?where=NAME%3D%27Hamilton%27&outFields=NAME&outSR=4326&f=geojson"
    ),
)
HILLSHADE = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer/exportImage"
)

FIG_W, FIG_H = 17.0, 11.0
DPI = 200
PAGE = 2000

BG = "#15150F"
CREAM = "#F2EFE4"
MUTED = "#B8B5A8"
OLIVE = "#9CBB74"
GOLD = "#E8C46A"
EMBER = "#E25C2A"
QUIET = "#8E967F"
LINE = "#3A3B2D"

# Label anchors are for the poster, not surveyed landmarks.
PLACES = (
    ("Chattanooga", -85.3097, 35.052, "center", "bottom"),
    ("Lookout Mtn", -85.358, 35.012, "right", "center"),
    ("Signal Mtn", -85.355, 35.140, "right", "bottom"),
    ("Soddy-Daisy", -85.185, 35.248, "left", "bottom"),
    ("Ooltewah", -85.055, 35.082, "left", "bottom"),
    ("East Ridge", -85.155, 34.992, "left", "top"),
    ("Sale Creek", -85.108, 35.382, "left", "bottom"),
)
RIVER = ("Tennessee River", -85.255, 35.078)

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "cts-30-day-map-challenge day-09 educational map"


def post_json(data: dict, tries: int = 5) -> dict:
    last_error: Exception | None = None
    for attempt in range(tries):
        try:
            response = SESSION.post(STRUCTURES, data=data, timeout=(30, 180))
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            time.sleep(2**attempt)
            continue
        if "error" in payload:
            raise RuntimeError(payload["error"])
        return payload
    raise RuntimeError(f"WUI query failed after {tries} tries: {last_error}")


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix(dest.suffix + ".part")
    with SESSION.get(url, timeout=(30, 300), stream=True) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_content(1 << 16):
                if chunk:
                    handle.write(chunk)
    temporary.replace(dest)


def looks_like_geojson(path: Path) -> bool:
    head = path.read_bytes()[:400].lstrip()
    return head.startswith(b"{") and b'"error"' not in head and b"Feature" in head


def load_county() -> gpd.GeoDataFrame:
    if COUNTY_PATH.exists() and not looks_like_geojson(COUNTY_PATH):
        COUNTY_PATH.unlink()
    if not COUNTY_PATH.exists():
        errors: list[str] = []
        saved = False
        for url in COUNTY_SOURCES:
            try:
                download(url, COUNTY_PATH)
            except requests.RequestException as exc:
                errors.append(f"{url} ({exc})")
                continue
            if looks_like_geojson(COUNTY_PATH):
                saved = True
                break
            COUNTY_PATH.unlink()
            errors.append(f"{url} (response was not GeoJSON)")
        if not saved:
            raise RuntimeError("County boundary download failed: " + "; ".join(errors))
        print(f"wrote {COUNTY_PATH.relative_to(ROOT)}", flush=True)
    county = gpd.read_file(COUNTY_PATH)
    if county.crs is None:
        county = county.set_crs(4326)
    else:
        county = county.to_crs(4326)
    west, south, east, north = county.total_bounds
    print(f"county bounds {west:.4f}, {south:.4f}, {east:.4f}, {north:.4f}", flush=True)
    return county


def county_geometry(county: gpd.GeoDataFrame):
    if len(county) == 1:
        return county.geometry.iloc[0]
    return county.geometry.union_all()


def envelope_query(bounds: tuple[float, float, float, float]) -> dict[str, str]:
    west, south, east, north = bounds
    return {
        "where": "1=1",
        "geometry": f"{west},{south},{east},{north}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "f": "json",
    }


def stack_features(features: list[dict]) -> dict[str, np.ndarray]:
    return {
        "lon": np.array([feature["centroid"]["x"] for feature in features], dtype=np.float64),
        "lat": np.array([feature["centroid"]["y"] for feature in features], dtype=np.float64),
    }


def fetch_structures(bounds: tuple[float, float, float, float]) -> dict[str, np.ndarray]:
    """Page structure centroids by object id so a long extract cannot skip rows."""
    base = envelope_query(bounds)
    expected = int(post_json({**base, "returnCountOnly": "true"})["count"])
    object_ids = post_json({**base, "returnIdsOnly": "true"}).get("objectIds") or []
    print(f"structures in county envelope: {expected:,}", flush=True)
    if len(object_ids) != expected:
        raise RuntimeError(f"Expected {expected:,} object ids and received {len(object_ids):,}.")

    parts: list[dict[str, np.ndarray]] = []
    fetched = 0
    for start in range(0, len(object_ids), PAGE):
        chunk = object_ids[start : start + PAGE]
        payload = post_json(
            {
                "objectIds": ",".join(str(object_id) for object_id in chunk),
                "outFields": "OBJECTID",
                "returnGeometry": "false",
                "returnCentroid": "true",
                "f": "json",
            }
        )
        features = payload.get("features") or []
        if len(features) != len(chunk):
            raise RuntimeError(f"Object-id page returned {len(features)} of {len(chunk)} structures.")
        parts.append(stack_features(features))
        fetched += len(features)
        print(f"  fetched {fetched:,} / {expected:,}", flush=True)

    return {key: np.concatenate([part[key] for part in parts]) for key in ("lon", "lat")}


def clip_to_county(points: dict[str, np.ndarray], county: gpd.GeoDataFrame) -> dict[str, np.ndarray]:
    series = gpd.GeoSeries(gpd.points_from_xy(points["lon"], points["lat"]), crs=4326)
    inside = series.within(county_geometry(county)).to_numpy()
    clipped = {key: value[inside] for key, value in points.items()}
    print(f"inside Hamilton County: {inside.sum():,}", flush=True)
    return clipped


def cache_path(neighborhood: int) -> Path:
    return PROCESSED / f"day09_hamilton_wui_{neighborhood}m.npz"


def sample_wui(lon: np.ndarray, lat: np.ndarray, raster: Path) -> np.ndarray:
    """Read only the pixels under the county footprints. Do not load the CONUS grid."""
    try:
        import rasterio
        from rasterio.warp import transform as rio_transform
    except ImportError as exc:
        raise SystemExit(
            "rasterio is required to read the Carlson WUI raster. "
            "Install it with: pip install -r 2026/08_utopia/requirements.txt"
        ) from exc
    with rasterio.open(raster) as src:
        crs = src.crs or rasterio.crs.CRS.from_proj4(AEA_WGS84)
        xs, ys = rio_transform("EPSG:4326", crs, lon.tolist(), lat.tolist())
        nodata = src.nodata
        sampled = np.fromiter(
            (value[0] for value in src.sample(zip(xs, ys), indexes=1)),
            dtype=np.float64,
            count=len(lon),
        )
    wui = np.full(len(lon), -1, dtype=np.int16)
    known = np.isfinite(sampled) & np.isin(sampled, (0, 1, 2))
    if nodata is not None:
        known &= sampled != nodata
    wui[known] = sampled[known].astype(np.int16)
    print(
        "WUI classes:"
        f" not {int((wui == 0).sum()):,},"
        f" intermix {int((wui == 1).sum()):,},"
        f" interface {int((wui == 2).sum()):,},"
        f" outside raster {int((wui < 0).sum()):,}",
        flush=True,
    )
    return wui


def load_structures(
    county: gpd.GeoDataFrame,
    raster: Path,
    neighborhood: int,
    refresh: bool,
) -> dict[str, np.ndarray]:
    cache = cache_path(neighborhood)
    if cache.exists() and not refresh:
        stored = np.load(cache)
        print(f"loaded {cache.name} ({len(stored['lon']):,} structures)", flush=True)
        return {key: stored[key] for key in ("lon", "lat", "wui")}
    west, south, east, north = county.total_bounds
    pad = 0.01
    points = fetch_structures((west - pad, south - pad, east + pad, north + pad))
    clipped = clip_to_county(points, county)
    clipped["wui"] = sample_wui(clipped["lon"], clipped["lat"], raster)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, **clipped)
    print(f"wrote {cache.relative_to(ROOT)}", flush=True)
    return clipped


def fetch_hillshade(bounds: tuple[float, float, float, float]) -> Path | None:
    if HILLSHADE_PATH.exists():
        return HILLSHADE_PATH
    west, south, east, north = bounds
    width = 1800
    height = max(1, int(round(width * (north - south) / (east - west))))
    rule = json.dumps(
        {
            "rasterFunction": "Hillshade",
            "rasterFunctionArguments": {"Azimuth": 315, "Altitude": 45},
        }
    )
    try:
        response = SESSION.get(
            HILLSHADE,
            params={
                "bbox": f"{west},{south},{east},{north}",
                "bboxSR": "4326",
                "imageSR": "4326",
                "size": f"{width},{height}",
                "format": "png",
                "interpolation": "RSP_BilinearInterpolation",
                "renderingRule": rule,
                "f": "image",
            },
            timeout=(30, 180),
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"hillshade skipped ({exc})", flush=True)
        return None
    if not response.content.startswith(b"\x89PNG"):
        print("hillshade skipped (USGS did not return a PNG)", flush=True)
        return None
    RAW.mkdir(parents=True, exist_ok=True)
    HILLSHADE_PATH.write_bytes(response.content)
    print(f"wrote {HILLSHADE_PATH.relative_to(ROOT)}", flush=True)
    return HILLSHADE_PATH


def geometry_path(geom) -> MplPath:
    polygons = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    vertices: list[np.ndarray] = []
    codes: list[np.ndarray] = []
    for polygon in polygons:
        if not isinstance(polygon, Polygon):
            continue
        for ring in (polygon.exterior, *polygon.interiors):
            coords = np.asarray(ring.coords)
            code = np.full(len(coords), MplPath.LINETO, dtype=np.uint8)
            code[0] = MplPath.MOVETO
            vertices.append(coords)
            codes.append(code)
    return MplPath(np.concatenate(vertices), np.concatenate(codes))


def tint_hillshade(image: np.ndarray) -> np.ndarray:
    gray = image[..., :3].mean(axis=-1) if image.ndim == 3 else image
    gray = gray.astype(np.float32)
    span = float(gray.max() - gray.min()) or 1.0
    gray = (gray - float(gray.min())) / span
    low = np.array([0.07, 0.09, 0.07], dtype=np.float32)
    high = np.array([0.34, 0.36, 0.27], dtype=np.float32)
    return low + (high - low) * np.power(gray, 0.9)[..., None]


def fit_map_box(bounds: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """Axes rectangle in inches: left, bottom, width, height."""
    west, south, east, north = bounds
    mid_lat = (south + north) / 2
    ground_w = (east - west) * np.cos(np.deg2rad(mid_lat))
    ground_h = north - south
    slot_w, slot_h = 10.55, 10.15
    scale = min(slot_w / ground_w, slot_h / ground_h)
    width = ground_w * scale
    height = ground_h * scale
    left = 0.38 + (slot_w - width) / 2
    bottom = 0.42 + (slot_h - height) / 2
    return left, bottom, width, height


def draw_scale(ax, bounds) -> None:
    west, south, east, north = bounds
    mid_lat = (south + north) / 2
    meters_per_degree = 111_320 * np.cos(np.deg2rad(mid_lat))
    miles = 5
    bar = miles * 1609.344 / meters_per_degree
    x = west + (east - west) * 0.06
    y = south + (north - south) * 0.045
    ax.plot([x, x + bar], [y, y], color=CREAM, lw=1.6, solid_capstyle="butt", zorder=6)
    ax.plot([x, x], [y - (north - south) * 0.006, y + (north - south) * 0.006], color=CREAM, lw=1.0, zorder=6)
    ax.plot(
        [x + bar, x + bar],
        [y - (north - south) * 0.006, y + (north - south) * 0.006],
        color=CREAM,
        lw=1.0,
        zorder=6,
    )
    ax.text(
        x + bar / 2,
        y + (north - south) * 0.012,
        "5 miles",
        color=CREAM,
        fontsize=8,
        ha="center",
        va="bottom",
        zorder=6,
        path_effects=[withStroke(linewidth=3, foreground=BG)],
    )


def draw_north(ax) -> None:
    ax.annotate(
        "",
        xy=(0.93, 0.16),
        xytext=(0.93, 0.075),
        xycoords="axes fraction",
        arrowprops={"arrowstyle": "-|>", "color": CREAM, "lw": 1.1, "mutation_scale": 10},
        zorder=6,
    )
    ax.text(
        0.93,
        0.175,
        "N",
        transform=ax.transAxes,
        color=CREAM,
        fontsize=11,
        ha="center",
        va="bottom",
        zorder=6,
        path_effects=[withStroke(linewidth=3, foreground=BG)],
    )


def render(
    points: dict[str, np.ndarray],
    county: gpd.GeoDataFrame,
    hillshade: Path | None,
    neighborhood: int,
) -> None:
    lon = points["lon"]
    lat = points["lat"]
    wui = points["wui"]
    west, south, east, north = county.total_bounds
    pad_x = (east - west) * 0.03
    pad_y = (north - south) * 0.03
    bounds = (west - pad_x, south - pad_y, east + pad_x, north + pad_y)
    geom = county_geometry(county)
    outline = geometry_path(geom)

    plt.rcParams["font.family"] = "DejaVu Sans"
    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI, facecolor=BG)
    left, bottom, width, height = fit_map_box(bounds)
    ax = fig.add_axes((left / FIG_W, bottom / FIG_H, width / FIG_W, height / FIG_H))
    ax.set_facecolor(BG)
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    ax.set_aspect(1 / np.cos(np.deg2rad((bounds[1] + bounds[3]) / 2)), adjustable="box")
    ax.set_axis_off()

    if hillshade is not None:
        shade = tint_hillshade(plt.imread(hillshade))
        image = ax.imshow(
            shade,
            extent=(west, east, south, north),
            origin="upper",
            interpolation="bilinear",
            zorder=0,
        )
        image.set_clip_path(outline, ax.transData)
    else:
        ax.add_patch(PathPatch(outline, facecolor="#1C2118", edgecolor="none", zorder=0))

    ax.add_patch(PathPatch(outline, facecolor="none", edgecolor=CREAM, linewidth=0.8, zorder=5))

    halo = [withStroke(linewidth=3, foreground=BG)]
    classes = (
        (0, QUIET, 1.6, 0.35, 2),
        (1, GOLD, 7.0, 0.90, 3),
        (2, EMBER, 7.0, 0.90, 4),
    )
    counts = {}
    for code, color, size, alpha, level in classes:
        mask = wui == code
        counts[code] = int(mask.sum())
        ax.scatter(
            lon[mask],
            lat[mask],
            s=size,
            c=color,
            alpha=alpha,
            linewidths=0,
            rasterized=True,
            zorder=level,
        )

    for name, x, y, ha, va in PLACES:
        if not geom.covers(gpd.points_from_xy([x], [y])[0]):
            continue
        ax.text(
            x,
            y,
            name,
            color=CREAM,
            fontsize=8,
            ha=ha,
            va=va,
            zorder=6,
            path_effects=halo,
        )
    river_name, river_x, river_y = RIVER
    ax.text(
        river_x,
        river_y,
        river_name,
        color="#D5E2EF",
        fontsize=8,
        fontstyle="italic",
        ha="center",
        va="center",
        zorder=6,
        path_effects=halo,
    )
    draw_scale(ax, bounds)
    draw_north(ax)

    rail_x = left + width + 0.42
    y = FIG_H - 0.55
    fig.text(
        rail_x / FIG_W,
        y / FIG_H,
        "Where the city\nmeets the woods",
        color=OLIVE,
        fontsize=26,
        va="top",
        ha="left",
        linespacing=1.15,
    )
    y -= 1.55
    fig.text(
        rail_x / FIG_W,
        y / FIG_H,
        "Hamilton County, Tennessee\nBuilding footprints classed as\nintermix or interface WUI.",
        color=CREAM,
        fontsize=11,
        va="top",
        ha="left",
        linespacing=1.45,
    )
    y -= 1.35
    fig.text(
        rail_x / FIG_W,
        y / FIG_H,
        f"Carlson et al. 2022, {neighborhood} m",
        color=MUTED,
        fontsize=9,
        va="top",
    )
    y -= 0.38
    legend = (
        (1, GOLD, "Intermix"),
        (2, EMBER, "Interface"),
        (0, QUIET, "Not WUI"),
    )
    for code, color, label in legend:
        fig.patches.append(
            Rectangle(
                (rail_x / FIG_W, (y - 0.07) / FIG_H),
                0.22 / FIG_W,
                0.14 / FIG_H,
                transform=fig.transFigure,
                facecolor=color,
                edgecolor="none",
                zorder=5,
            )
        )
        fig.text(
            (rail_x + 0.36) / FIG_W,
            y / FIG_H,
            f"{counts[code]:,}   {label}",
            color=CREAM,
            fontsize=10,
            va="center",
        )
        y -= 0.42

    y -= 0.15
    fig.text(
        rail_x / FIG_W,
        y / FIG_H,
        "Gold is intermix: wildland vegetation\n"
        "covers at least half the neighborhood.\n"
        "Ember is interface: within 2.4 km of\n"
        "a large wildland patch, with less\n"
        "vegetation mixed among the buildings.",
        color=MUTED,
        fontsize=10.5,
        va="top",
        linespacing=1.45,
    )

    outside = int((wui < 0).sum())
    outside_line = f"\n{outside:,} footprints fell outside the raster.\n" if outside else "\n"
    fig.text(
        rail_x / FIG_W,
        1.72 / FIG_H,
        "Both WUI classes need at least\n"
        "6.17 buildings per km². Footprints\n"
        "are current FEMA buildings. The class\n"
        "comes from the 2018 Microsoft\n"
        "footprints and 2016 land cover.\n"
        f"{outside_line}\n"
        "Carlson et al. 2022, USGS\n"
        "doi.org/10.5066/P94BT6Q7\n"
        "FEMA WUI Structures V2\n"
        "USGS 3DEP hillshade\n"
        "Hamilton County GIS boundary\n\n"
        "Created by Colin T. Stiles\n"
        "30 Day Map Challenge 2026\n"
        "Day 9  ·  Urban-rural\n"
        "11 × 17 in",
        color=MUTED,
        fontsize=8,
        va="bottom",
        linespacing=1.35,
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=DPI, facecolor=fig.get_facecolor())
    fig.savefig(OUT_PDF, dpi=DPI, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"wrote {OUT_PNG.relative_to(ROOT)}", flush=True)
    print(f"wrote {OUT_PDF.relative_to(ROOT)}", flush=True)
    for code, _, label in legend:
        print(f"  rating {code}: {counts[code]:,}  {label}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Day 9 Hamilton County WUI poster.")
    parser.add_argument("--refresh", action="store_true", help="Ignore the cached county extract.")
    parser.add_argument(
        "--neighborhood",
        type=int,
        default=100,
        choices=NEIGHBORHOODS,
        help="Carlson neighborhood radius in meters. 100 is the tightest edge.",
    )
    parser.add_argument("--raster", type=Path, help="Override the CONUS_WUI GeoTIFF path.")
    args = parser.parse_args()
    raster = args.raster or (WUI_DIR / f"CONUS_WUI_{args.neighborhood}m.tif")
    if not raster.exists():
        raise SystemExit(f"WUI raster not found: {raster}")
    county = load_county()
    points = load_structures(county, raster, args.neighborhood, args.refresh)
    west, south, east, north = county.total_bounds
    hillshade = fetch_hillshade((west, south, east, north))
    render(points, county, hillshade, args.neighborhood)


if __name__ == "__main__":
    main()
