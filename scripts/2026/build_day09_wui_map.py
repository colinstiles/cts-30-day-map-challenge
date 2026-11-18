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

import _env  # noqa: F401  (loads .env for SSL_CERT_FILE / REQUESTS_CA_BUNDLE)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUT_PNG = ROOT / "2026" / "images" / "day-09.png"
OUT_PRINT_PNG = ROOT / "2026" / "09_urban_rural" / "day-09-11x17.png"
OUT_PDF = ROOT / "2026" / "09_urban_rural" / "day-09-11x17.pdf"
COUNTY_PATH = RAW / "hamilton_county.geojson"
TENNESSEE_PATH = RAW / "tennessee_counties.geojson"
# maxAllowableOffset makes this service return HTTP 500. geometryPrecision is the
# generalization it will accept, and the county name field is lowercase.
TENNESSEE_QUERIES = (
    (
        "https://maps.cot.tn.gov/hosting/rest/services/Hosted/TN_Counties/FeatureServer/0/query"
        "?where=1%3D1&outFields=name&outSR=4326&geometryPrecision=4&f=geojson"
    ),
    (
        "https://maps.cot.tn.gov/hosting/rest/services/Hosted/TN_Counties/FeatureServer/0/query"
        "?where=1%3D1&outFields=name&outSR=4326&f=geojson"
    ),
)
HILLSHADE_PATH = RAW / "day09_hillshade.png"
_WUI_DIR_WINDOWS = (
    r"G:\GIS\D_tin-topo\project_data\30_day_map_challenge\2026"
    r"\CONUS_building_footprint_WUI_data"
)
WUI_DIR = _env.resolve_existing_path(
    Path(_WUI_DIR_WINDOWS),
    _env.windows_drive_to_wsl(_WUI_DIR_WINDOWS),
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
    ("East Ridge", -85.155, 35.004, "left", "bottom"),
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
    """True for a GeoJSON object. ArcGIS writes coordinates before \"type\": \"Feature\"."""
    head = path.read_bytes()[:500].lstrip().lower()
    if not head.startswith(b"{") or b'"error"' in head:
        return False
    return b'"features"' in head or b'"type"' in head[:120]


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


def load_tennessee() -> gpd.GeoDataFrame:
    if TENNESSEE_PATH.exists() and not looks_like_geojson(TENNESSEE_PATH):
        TENNESSEE_PATH.unlink()
    if not TENNESSEE_PATH.exists():
        errors: list[str] = []
        saved = False
        for url in TENNESSEE_QUERIES:
            try:
                download(url, TENNESSEE_PATH)
            except requests.RequestException as exc:
                errors.append(f"{url} ({exc})")
                continue
            if looks_like_geojson(TENNESSEE_PATH):
                saved = True
                break
            TENNESSEE_PATH.unlink()
            errors.append(f"{url} (response was not GeoJSON)")
        if not saved:
            raise RuntimeError("Tennessee county download failed: " + "; ".join(errors))
        print(f"wrote {TENNESSEE_PATH.relative_to(ROOT)}", flush=True)
    state = gpd.read_file(TENNESSEE_PATH)
    if state.crs is None:
        state = state.set_crs(4326)
    else:
        state = state.to_crs(4326)
    return state


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


def class_land_shares(county: gpd.GeoDataFrame, raster: Path) -> dict[int, float]:
    """Percent of mapped county land in each WUI class. Nodata, mostly water, is excluded."""
    try:
        import rasterio
        from rasterio.features import geometry_mask
        from rasterio.windows import from_bounds
    except ImportError as exc:
        raise SystemExit(
            "rasterio is required to read the Carlson WUI raster. "
            "Install it with: pip install -r 2026/08_utopia/requirements.txt"
        ) from exc
    from shapely.geometry import mapping

    with rasterio.open(raster) as src:
        crs = src.crs or rasterio.crs.CRS.from_proj4(AEA_WGS84)
        projected = county.to_crs(crs)
        geom = projected.geometry.iloc[0] if len(projected) == 1 else projected.geometry.union_all()
        minx, miny, maxx, maxy = geom.bounds
        window = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
        window = window.round_offsets().round_lengths()
        fill = src.nodata if src.nodata is not None else -1
        data = src.read(1, window=window, boundless=True, fill_value=fill)
        transform = src.window_transform(window)
        inside = geometry_mask(
            [mapping(geom)],
            transform=transform,
            invert=True,
            out_shape=data.shape,
        )
        known = inside & np.isin(data, (0, 1, 2))
        total = int(known.sum())
        if total == 0:
            raise RuntimeError("No classified WUI pixels fall inside Hamilton County.")
        shares = {code: 100.0 * int((known & (data == code)).sum()) / total for code in (0, 1, 2)}
        pixel_km2 = abs(float(src.res[0]) * float(src.res[1])) / 1_000_000
        print(f"mapped county land {total * pixel_km2:,.1f} km²", flush=True)
        for code, name in ((1, "intermix"), (2, "interface"), (0, "not WUI")):
            print(f"  {name}: {shares[code]:.1f}% of county land", flush=True)
        return shares


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


def draw_scale(ax, county_bounds, frame_bounds) -> None:
    """Five-mile bar in the margin under the county, clear of the place names."""
    west, south, east, north = frame_bounds
    c_west, c_south, c_east, _c_north = county_bounds
    mid_lat = (south + north) / 2
    meters_per_degree = 111_320 * np.cos(np.deg2rad(mid_lat))
    bar = 5 * 1609.344 / meters_per_degree
    x = (c_west + c_east) / 2 - bar / 2
    y = c_south - (c_south - south) * 0.55
    tick = (c_south - south) * 0.12
    ax.plot([x, x + bar], [y, y], color=CREAM, lw=1.6, solid_capstyle="butt", zorder=6)
    ax.plot([x, x], [y - tick, y + tick], color=CREAM, lw=1.0, zorder=6)
    ax.plot([x + bar, x + bar], [y - tick, y + tick], color=CREAM, lw=1.0, zorder=6)
    ax.text(x + bar / 2, y + tick * 1.4, "5 miles", color=CREAM, fontsize=8, ha="center", va="bottom", zorder=6)


def draw_north(ax, county_bounds, frame_bounds) -> None:
    """North arrow in the margin east of the county."""
    _west, _south, east, _north = frame_bounds
    _c_west, c_south, c_east, c_north = county_bounds
    span = c_north - c_south
    x = c_east + (east - c_east) * 0.48
    y0 = c_north - span * 0.08
    y1 = y0 + span * 0.055
    ax.annotate(
        "",
        xy=(x, y1),
        xytext=(x, y0),
        arrowprops={"arrowstyle": "-|>", "color": CREAM, "lw": 1.2, "mutation_scale": 12},
        zorder=6,
    )
    ax.text(x, y1 + span * 0.012, "N", color=CREAM, fontsize=11, ha="center", va="bottom", zorder=6)


def draw_inset(fig, tennessee: gpd.GeoDataFrame, left_in: float, top_in: float) -> float:
    """Locator under the title. Returns the inch coordinate just below the caption."""
    west, south, east, north = tennessee.total_bounds
    mid = (south + north) / 2
    ground_w = (east - west) * np.cos(np.deg2rad(mid))
    ground_h = north - south
    width_in = 4.85
    height_in = width_in * ground_h / ground_w
    bottom_in = top_in - height_in
    inset = fig.add_axes((left_in / FIG_W, bottom_in / FIG_H, width_in / FIG_W, height_in / FIG_H))
    inset.set_facecolor(BG)
    pad_x = (east - west) * 0.015
    pad_y = (north - south) * 0.06
    inset.set_xlim(west - pad_x, east + pad_x)
    inset.set_ylim(south - pad_y, north + pad_y)
    inset.set_axis_off()
    columns = {column.lower(): column for column in tennessee.columns}
    name_col = columns.get("name", str(tennessee.columns[0]))
    for _, row in tennessee.iterrows():
        hamilton = str(row[name_col]).lower().startswith("hamilton")
        inset.add_patch(
            PathPatch(
                geometry_path(row.geometry),
                facecolor=EMBER if hamilton else "#23281E",
                edgecolor=CREAM if hamilton else "#4E5346",
                linewidth=0.8 if hamilton else 0.25,
                zorder=2 if hamilton else 1,
            )
        )
    caption_y = bottom_in - 0.22
    fig.text(
        left_in / FIG_W,
        caption_y / FIG_H,
        "Hamilton County in Tennessee",
        color=MUTED,
        fontsize=8,
        va="top",
    )
    return caption_y - 0.28


def render(
    points: dict[str, np.ndarray],
    county: gpd.GeoDataFrame,
    tennessee: gpd.GeoDataFrame,
    hillshade: Path | None,
    neighborhood: int,
    shares: dict[int, float],
) -> None:
    lon = points["lon"]
    lat = points["lat"]
    wui = points["wui"]
    west, south, east, north = county.total_bounds
    county_bounds = (west, south, east, north)
    # Extra room below and to the east so the scale bar and north arrow sit off the county.
    bounds = (
        west - (east - west) * 0.035,
        south - (north - south) * 0.11,
        east + (east - west) * 0.08,
        north + (north - south) * 0.04,
    )
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
    draw_scale(ax, county_bounds, bounds)
    draw_north(ax, county_bounds, bounds)

    rail_x = left + width + 0.38
    y = FIG_H - 0.48
    fig.text(
        rail_x / FIG_W,
        y / FIG_H,
        "Wildland-Urban Interface\nof Hamilton County, Tennessee",
        color=OLIVE,
        fontsize=18,
        va="top",
        ha="left",
        linespacing=1.2,
    )
    y -= 1.05
    fig.text(
        rail_x / FIG_W,
        y / FIG_H,
        "Where buildings stand among, or against, wildland vegetation.",
        color=CREAM,
        fontsize=10,
        va="top",
        ha="left",
    )
    y -= 0.32
    y = draw_inset(fig, tennessee, rail_x, y)
    fig.text(
        rail_x / FIG_W,
        y / FIG_H,
        f"Share of county land, {neighborhood} m neighborhood",
        color=MUTED,
        fontsize=8.5,
        va="top",
    )
    y -= 0.36
    legend = (
        (1, GOLD, "Intermix", "Wildland vegetation covers at least half the surrounding ground."),
        (2, EMBER, "Interface", "Within 2.4 km of a wildland patch of at least 5 km²."),
        (0, QUIET, "Not WUI", "Outside both classes."),
    )
    for code, color, label, definition in legend:
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
            f"{label}   {shares[code]:.1f}% of county land",
            color=CREAM,
            fontsize=11,
            va="center",
        )
        y -= 0.28
        fig.text(
            rail_x / FIG_W,
            y / FIG_H,
            definition,
            color=MUTED,
            fontsize=8.5,
            va="top",
        )
        y -= 0.38

    outside = int((wui < 0).sum())
    outside_line = f"{outside:,} footprints fell outside the raster.\n" if outside else ""
    fig.text(
        rail_x / FIG_W,
        0.42 / FIG_H,
        "Percents are each class's share of mapped county land.\n"
        "Unclassified ground, mostly water, is left out of the total.\n"
        "Both WUI classes also have at least 6.17 buildings per km².\n\n"
        "Building locations: FEMA WUI Structures V2.\n"
        f"WUI class: Carlson et al. 2022, USGS, {neighborhood} m neighborhood,\n"
        "from 2018 Microsoft footprints and 2016 NLCD.\n"
        "doi.org/10.5066/P94BT6Q7\n"
        f"{outside_line}"
        "Hillshade: USGS 3DEP.  Boundary: Hamilton County GIS.\n\n"
        "Created by Colin T. Stiles\n"
        "30 Day Map Challenge 2026  ·  Day 9  ·  Urban-rural\n"
        "11 × 17 in",
        color=MUTED,
        fontsize=8,
        va="bottom",
        linespacing=1.35,
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=DPI, facecolor=fig.get_facecolor())
    fig.savefig(OUT_PRINT_PNG, dpi=DPI, facecolor=fig.get_facecolor())
    fig.savefig(OUT_PDF, dpi=DPI, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"wrote {OUT_PNG.relative_to(ROOT)}", flush=True)
    print(f"wrote {OUT_PRINT_PNG.relative_to(ROOT)}", flush=True)
    print(f"wrote {OUT_PDF.relative_to(ROOT)}", flush=True)
    for code, _, label, _definition in legend:
        print(f"  {label}: {shares[code]:.1f}% of county land, {counts[code]:,} buildings", flush=True)


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
    tennessee = load_tennessee()
    points = load_structures(county, raster, args.neighborhood, args.refresh)
    shares = class_land_shares(county, raster)
    west, south, east, north = county.total_bounds
    hillshade = fetch_hillshade((west, south, east, north))
    render(points, county, tennessee, hillshade, args.neighborhood, shares)


if __name__ == "__main__":
    main()
