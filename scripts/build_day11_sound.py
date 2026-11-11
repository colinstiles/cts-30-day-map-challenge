"""Map a terrain-shadowed audible-reach proxy for Day 11.

Three representative points stand in for the guns, not for surveyed batteries:

- Chickamauga, the centroid of the main battlefield unit (Sept 19–20, 1863)
- Lookout Mountain, the high ground at the north end (Nov 24, 1863)
- Missionary Ridge, the crest of the largest ridge reservation (Nov 25, 1863)

The proxy is a distance fade times a ridge penalty. On open ground it is
still strong at 10 miles, where Chickamauga's guns were heard in the city,
and it fades out at 15 miles. Terrain above the straight path reduces it.
Earth curvature is included. Atmospheric refraction is not: cannon sound
ducts with the weather, and this map does not pretend to model that.

No decibels. The colors are a relative reach, not a measured level.

Distances use a local equirectangular scale (EPSG:4326) at the map center.
The GeoTIFF and downloads are cached under data/raw/, which is gitignored.
A corporate proxy may need the local Zscaler CA on SSL_CERT_FILE. Do not
disable TLS verification.

Run from the repository root:

    python scripts/build_day11_sound.py
    python scripts/build_day11_sound.py --refresh
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import _env  # noqa: F401  (loads .env for SSL_CERT_FILE / REQUESTS_CA_BUNDLE)
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.patheffects import withStroke
from PIL import Image
from shapely import contains_xy
from shapely.geometry import Point, shape
from shapely.ops import unary_union

OPEN_MILES = 15.0
HEARD_MILES = 10.0
# Open-ground proxy remaining at HEARD_MILES. Zero at OPEN_MILES.
HEARD_LEVEL = 0.60
# Meters of terrain above the path that multiply the proxy by 1/e.
BARRIER_SCALE_M = 90.0
SOURCE_H_M = 2.0
EAR_H_M = 1.5
EARTH_RADIUS_M = 6_371_000.0
DEM_M = 40.0
GRID_M = 100.0
MILE_M = 1609.344

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DAY = ROOT / "2026" / "11_sound"
OUT_PNG = ROOT / "2026" / "images" / "day-11.png"
BOUNDARY_PATH = RAW / "day11_chch_boundary.geojson"
CEMETERY_PATH = RAW / "day11_cemetery.geojson"
CITY_PATH = RAW / "day11_city.json"
DEM_PATH = RAW / "day11-3dep.tif"
DEM_META = RAW / "day11-3dep.json"
GRID_PATH = PROCESSED / "day11_audibility.npz"

USER_AGENT = "cts-30-day-map-challenge"
EXPORT_URL = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer/exportImage"
)
NPS_QUERY = (
    "https://services1.arcgis.com/fBc8EJBxQRMcHlei/ArcGIS/rest/services/"
    "NPS_Land_Resources_Division_Boundary_and_Tract_Data_Service/"
    "FeatureServer/2/query"
)
ESRI_EXPORT = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "Canvas/World_Dark_Gray_Base/MapServer/export"
)
OVERPASS = "https://overpass-api.de/api/interpreter"
NOMINATIM = "https://nominatim.openstreetmap.org/search"

BG = "#14140F"
INK = "#F3EFE4"
MUTED = "#B7B3A6"
LINE = "#3A3B2D"
CHICK = "#E2A04A"
LOOK = "#7EB0C4"
MISS = "#D2644A"
COLORS = {"chickamauga": CHICK, "lookout": LOOK, "missionary": MISS}


def meters_per_degree(lat: float) -> tuple[float, float]:
    """Return meters per degree of latitude and longitude."""
    m_lat = 111_132.92 - 559.82 * math.cos(2 * math.radians(lat))
    m_lon = 111_412.84 * math.cos(math.radians(lat))
    return m_lat, m_lon


def miles_between(lat0: float, lon0: float, lat1: float, lon1: float) -> float:
    """Equirectangular miles. Fine for a Chattanooga-sized extent."""
    m_lat, m_lon = meters_per_degree((lat0 + lat1) / 2)
    return math.hypot((lat1 - lat0) * m_lat, (lon1 - lon0) * m_lon) / MILE_M


def distance_term(distance_m: np.ndarray) -> np.ndarray:
    """Open-ground fade. Strong through 10 miles, gone at 15."""
    heard_m = HEARD_MILES * MILE_M
    open_m = OPEN_MILES * MILE_M
    d = np.asarray(distance_m, dtype=np.float64)
    term = np.empty(d.shape, dtype=np.float64)
    near = d <= heard_m
    term[near] = 1.0 - (1.0 - HEARD_LEVEL) * (d[near] / heard_m)
    term[~near] = HEARD_LEVEL * (open_m - d[~near]) / (open_m - heard_m)
    return np.clip(term, 0.0, 1.0)


def _get(url: str, data: bytes | None = None, timeout: int = 180) -> bytes:
    request = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


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

    Same layout as the Day 5 export. The array is north-up. Edges are the
    outer edges of the raster, from the GeoTIFF tiepoint.
    """
    if data[:2] != b"II" or struct.unpack_from("<H", data, 2)[0] != 42:
        raise ValueError("Expected a little-endian classic TIFF from 3DEP.")
    ifd = struct.unpack_from("<I", data, 4)[0]
    ntags = struct.unpack_from("<H", data, ifd)[0]
    tags: dict[int, tuple[int, int, int]] = {}
    for i in range(ntags):
        entry = struct.unpack_from("<HHII", data, ifd + 2 + 12 * i)
        tags[entry[0]] = (entry[1], entry[2], entry[3])
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
            r0, c0 = ty * tile_h, tx * tile_w
            r1, c1 = min(r0 + tile_h, height), min(c0 + tile_w, width)
            grid[r0:r1, c0:c1] = tile[: r1 - r0, : c1 - c0]

    scale_x, scale_y = _tiff_values(data, tags, 33550)[:2]
    tie_i, tie_j, _k, tie_x, tie_y, _z = _tiff_values(data, tags, 33922)
    west = tie_x - tie_i * scale_x
    north = tie_y + tie_j * scale_y
    east = west + width * scale_x
    south = north - height * scale_y
    return grid, west, south, east, north


def download_json(url: str) -> dict:
    payload = _get(url)
    info = json.loads(payload)
    if "error" in info and "features" not in info:
        raise RuntimeError(info["error"])
    return info


def load_boundary(refresh: bool):
    """NPS legislated boundary for Chickamauga and Chattanooga NMP."""
    if BOUNDARY_PATH.exists() and not refresh:
        info = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
    else:
        query = urllib.parse.urlencode(
            {
                "where": "UNIT_CODE='CHCH'",
                "outFields": "UNIT_CODE,UNIT_NAME",
                "returnGeometry": "true",
                "outSR": "4326",
                "geometryPrecision": "5",
                "maxAllowableOffset": "0.0003",
                "f": "geojson",
            }
        )
        info = download_json(f"{NPS_QUERY}?{query}")
        BOUNDARY_PATH.write_text(json.dumps(info), encoding="utf-8")
        print(f"wrote {BOUNDARY_PATH.name}", flush=True)
    features = info.get("features") or []
    if len(features) != 1:
        raise RuntimeError(f"Expected one CHCH boundary feature, got {len(features)}.")
    geom = shape(features[0]["geometry"])
    if geom.geom_type == "Polygon":
        parts = [geom]
    elif geom.geom_type == "MultiPolygon":
        parts = list(geom.geoms)
    else:
        raise RuntimeError(f"Unexpected boundary type {geom.geom_type}.")
    repaired = []
    for poly in parts:
        if not poly.is_valid:
            poly = poly.buffer(0)
        pieces = []
        if poly.geom_type == "Polygon":
            pieces = [poly]
        elif poly.geom_type == "MultiPolygon":
            pieces = list(poly.geoms)
        for piece in pieces:
            if piece.is_empty or piece.area <= 0:
                continue
            repaired.append(piece)
    return features[0], repaired


def _way_polygon(element: dict):
    coords = [(pt["lon"], pt["lat"]) for pt in element.get("geometry", [])]
    if len(coords) < 4:
        return None
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    poly = shape({"type": "Polygon", "coordinates": [coords]})
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty or poly.geom_type not in {"Polygon", "MultiPolygon"}:
        return None
    return poly


def _overpass(query: str) -> dict | None:
    try:
        payload = _get(OVERPASS, data=query.encode("utf-8"), timeout=60)
    except (urllib.error.URLError, TimeoutError):
        print("Overpass request failed; using the fallback source.", flush=True)
        return None
    return json.loads(payload)


def _overpass_polygons(query: str):
    info = _overpass(query)
    if info is None:
        return []
    polygons = []
    for element in info.get("elements", []):
        if element.get("type") == "way":
            poly = _way_polygon(element)
            if poly is not None:
                polygons.append(poly)
    return polygons


def load_cemetery(refresh: bool):
    """Chattanooga National Cemetery polygon from OpenStreetMap."""
    if CEMETERY_PATH.exists() and not refresh:
        info = json.loads(CEMETERY_PATH.read_text(encoding="utf-8"))
        return shape(info["features"][0]["geometry"])
    query = """
[out:json][timeout:40];
way["name"="Chattanooga National Cemetery"];
out geom;
"""
    polygons = _overpass_polygons(query)
    if not polygons:
        params = urllib.parse.urlencode(
            {
                "q": "Chattanooga National Cemetery",
                "format": "jsonv2",
                "polygon_geojson": 1,
                "limit": 1,
            }
        )
        hits = json.loads(_get(f"{NOMINATIM}?{params}", timeout=60))
        if not hits or "geojson" not in hits[0]:
            raise RuntimeError("Chattanooga National Cemetery was not found.")
        geom = shape(hits[0]["geojson"])
    else:
        geom = unary_union(polygons)
    feature = {
        "type": "Feature",
        "properties": {
            "name": "Chattanooga National Cemetery",
            "source": "OpenStreetMap",
        },
        "geometry": geom.__geo_interface__,
    }
    collection = {"type": "FeatureCollection", "features": [feature]}
    CEMETERY_PATH.write_text(json.dumps(collection), encoding="utf-8")
    print(f"wrote {CEMETERY_PATH.name}", flush=True)
    return geom


def load_city(refresh: bool) -> tuple[float, float]:
    """OSM place node for Chattanooga."""
    if CITY_PATH.exists() and not refresh:
        info = json.loads(CITY_PATH.read_text(encoding="utf-8"))
        return float(info["lat"]), float(info["lon"])
    query = """
[out:json][timeout:40];
node["name"="Chattanooga"]["place"="city"];
out;
"""
    payload = _overpass(query) or {}
    nodes = [el for el in payload.get("elements", []) if el.get("type") == "node"]
    if not nodes:
        params = urllib.parse.urlencode(
            {"q": "Chattanooga, Tennessee", "format": "jsonv2", "limit": 5}
        )
        hits = json.loads(_get(f"{NOMINATIM}?{params}", timeout=60))
        city_hits = [
            hit for hit in hits if hit.get("type") in {"city", "administrative"}
        ]
        chosen = city_hits[0] if city_hits else (hits[0] if hits else None)
        if chosen is None:
            raise RuntimeError("Chattanooga place node was not found.")
        info = {
            "lat": float(chosen["lat"]),
            "lon": float(chosen["lon"]),
            "id": chosen.get("osm_id"),
            "source": "OpenStreetMap",
        }
        CITY_PATH.write_text(json.dumps(info), encoding="utf-8")
        print(f"wrote {CITY_PATH.name}", flush=True)
        return info["lat"], info["lon"]
    # The city node is unique. Take the first if a mirror ever returns two.
    node = nodes[0]
    info = {
        "lat": node["lat"],
        "lon": node["lon"],
        "id": node["id"],
        "source": "OpenStreetMap",
    }
    CITY_PATH.write_text(json.dumps(info), encoding="utf-8")
    print(f"wrote {CITY_PATH.name}", flush=True)
    return float(node["lat"]), float(node["lon"])


def part_area_km2(poly) -> float:
    lat = poly.centroid.y
    m_lat, m_lon = meters_per_degree(lat)
    return abs(poly.area) * m_lat * m_lon / 1_000_000.0


def choose_parts(parts: list):
    """Pick the three battlefield units out of the multipart park boundary."""
    ranked = sorted(parts, key=part_area_km2, reverse=True)
    print("largest park parts (km2, lat, lon):", flush=True)
    for poly in ranked[:8]:
        center = poly.centroid
        print(
            f"  {part_area_km2(poly):7.3f}  {center.y:8.4f}  {center.x:9.4f}",
            flush=True,
        )

    chick = ranked[0]
    chick_area = part_area_km2(chick)
    if chick_area < 10 or chick.centroid.y > 34.98:
        raise RuntimeError("The largest park part is not the Chickamauga field.")

    lookout_mass = max(
        (poly for poly in parts if poly.centroid.x < -85.30),
        key=part_area_km2,
    )
    if part_area_km2(lookout_mass) < 5:
        raise RuntimeError("Lookout Mountain unit was not found west of -85.30.")

    ridge = [
        poly
        for poly in parts
        if poly.centroid.x > -85.29
        and poly.centroid.y > 35.00
        and part_area_km2(poly) > 0.05
    ]
    if not ridge:
        raise RuntimeError("No Missionary Ridge reservation was found east of -85.29.")
    missionary = max(ridge, key=part_area_km2)
    return chick, lookout_mass, missionary


def expand_bounds(polys: list, margin_m: float) -> tuple[float, float, float, float]:
    minx = min(poly.bounds[0] for poly in polys)
    miny = min(poly.bounds[1] for poly in polys)
    maxx = max(poly.bounds[2] for poly in polys)
    maxy = max(poly.bounds[3] for poly in polys)
    m_lat, m_lon = meters_per_degree((miny + maxy) / 2)
    pad_lat = margin_m / m_lat
    pad_lon = margin_m / m_lon
    return minx - pad_lon, miny - pad_lat, maxx + pad_lon, maxy + pad_lat


def load_dem(bounds: tuple[float, float, float, float], refresh: bool):
    west, south, east, north = bounds
    meta = {"west": west, "south": south, "east": east, "north": north, "dem_m": DEM_M}
    cached = False
    if DEM_PATH.exists() and DEM_META.exists() and not refresh:
        stored = json.loads(DEM_META.read_text(encoding="utf-8"))
        cached = all(abs(stored[key] - meta[key]) < 1e-4 for key in meta)
    if not cached:
        m_lat, m_lon = meters_per_degree((south + north) / 2)
        cols = max(2, round((east - west) * m_lon / DEM_M))
        rows = max(2, round((north - south) * m_lat / DEM_M))
        query = (
            f"?bbox={west},{south},{east},{north}&bboxSR=4326&imageSR=4326"
            f"&size={cols},{rows}&format=tiff&pixelType=F32"
            "&interpolation=RSP_BilinearInterpolation&f=image"
        )
        print(f"downloading 3DEP {cols}x{rows}", flush=True)
        payload = _get(EXPORT_URL + query)
        if not payload.startswith(b"II"):
            raise RuntimeError(f"3DEP did not return a TIFF ({len(payload)} bytes).")
        DEM_PATH.write_bytes(payload)
        DEM_META.write_text(json.dumps(meta), encoding="utf-8")
        print(f"wrote {DEM_PATH.name} ({len(payload) / 1e6:.1f} MB)", flush=True)
    else:
        print(f"using cached {DEM_PATH.name}", flush=True)
        payload = DEM_PATH.read_bytes()
    grid, west, south, east, north = read_usgs_elevation(payload)
    if not np.isfinite(grid).all():
        bad = int(np.size(grid) - np.isfinite(grid).sum())
        raise RuntimeError(f"DEM has {bad} non-finite samples.")
    print(
        f"DEM {grid.shape[1]}x{grid.shape[0]}  "
        f"elev {float(grid.min()):.0f}–{float(grid.max()):.0f} m",
        flush=True,
    )
    return grid, (west, south, east, north)


def _axes(bounds: tuple[float, float, float, float], shape: tuple[int, int]):
    west, south, east, north = bounds
    nrows, ncols = shape
    lat = north - (np.arange(nrows) + 0.5) * (north - south) / nrows
    lon = west + (np.arange(ncols) + 0.5) * (east - west) / ncols
    return lat, lon


def _highest_cell(
    poly, elev, lat, lon, lat_min: float | None = None
) -> tuple[int, int]:
    if poly.geom_type == "MultiPolygon":
        cells = [
            _highest_cell(part, elev, lat, lon, lat_min)
            for part in poly.geoms
            if not part.is_empty
        ]
        return max(cells, key=lambda rc: float(elev[rc]))
    if poly.geom_type == "GeometryCollection":
        pieces = [
            part for part in poly.geoms if part.geom_type in {"Polygon", "MultiPolygon"}
        ]
        cells = [_highest_cell(part, elev, lat, lon, lat_min) for part in pieces]
        return max(cells, key=lambda rc: float(elev[rc]))
    minx, miny, maxx, maxy = poly.bounds
    cols = np.nonzero((lon >= minx) & (lon <= maxx))[0]
    rows = np.nonzero((lat >= miny) & (lat <= maxy))[0]
    if lat_min is not None:
        rows = rows[lat[rows] >= lat_min]
    if cols.size == 0 or rows.size == 0:
        raise RuntimeError("Polygon falls outside the DEM.")
    cc, rr = np.meshgrid(cols, rows)
    inside = contains_xy(poly, lon[cc], lat[rr])
    if not np.any(inside):
        point = poly.representative_point()
        r = int(np.argmin(np.abs(lat - point.y)))
        c = int(np.argmin(np.abs(lon - point.x)))
        return r, c
    values = np.where(inside, elev[rr, cc], -1e9)
    pick = np.unravel_index(int(np.argmax(values)), values.shape)
    return int(rr[pick]), int(cc[pick])


def _nearest_cell(lat0: float, lon0: float, lat, lon) -> tuple[int, int]:
    return int(np.argmin(np.abs(lat - lat0))), int(np.argmin(np.abs(lon - lon0)))


def locate_sources(chick, look_mass, missionary, parts, elev, bounds):
    lat, lon = _axes(bounds, elev.shape)
    chick_c = chick.centroid
    cr, cc = _nearest_cell(chick_c.y, chick_c.x, lat, lon)

    # The Nov 24 fight was at the north end, not the high point farther south.
    miny, maxy = look_mass.bounds[1], look_mass.bounds[3]
    north_cut = maxy - 0.25 * (maxy - miny)
    look_cells = [_highest_cell(look_mass, elev, lat, lon, lat_min=north_cut)]
    reservations = [
        poly
        for poly in parts
        if poly.centroid.x < -85.32
        and poly.centroid.y > 35.005
        and part_area_km2(poly) < 2
    ]
    look_cells.extend(_highest_cell(geom, elev, lat, lon) for geom in reservations)
    lr, lc = max(look_cells, key=lambda rc: float(elev[rc]))

    mr, mc = _highest_cell(missionary, elev, lat, lon)
    sources = [
        {
            "id": "chickamauga",
            "name": "Chickamauga",
            "date": "Sept 19–20, 1863",
            "row": cr,
            "col": cc,
            "lat": float(lat[cr]),
            "lon": float(lon[cc]),
            "elev_m": float(elev[cr, cc]),
            "note": "Centroid of the main battlefield unit",
        },
        {
            "id": "lookout",
            "name": "Lookout Mountain",
            "date": "Nov 24, 1863",
            "row": lr,
            "col": lc,
            "lat": float(lat[lr]),
            "lon": float(lon[lc]),
            "elev_m": float(elev[lr, lc]),
            "note": "Highest 3DEP cell at the north end of the mountain unit",
        },
        {
            "id": "missionary",
            "name": "Missionary Ridge",
            "date": "Nov 25, 1863",
            "row": mr,
            "col": mc,
            "lat": float(lat[mr]),
            "lon": float(lon[mc]),
            "elev_m": float(elev[mr, mc]),
            "note": "Highest 3DEP cell in the largest ridge reservation",
        },
    ]
    for source in sources:
        print(
            f"{source['id']:12} {source['lat']:.5f}, {source['lon']:.5f}  "
            f"{source['elev_m']:.0f} m",
            flush=True,
        )
    return sources


def stride_grid(elev: np.ndarray, bounds, sources: list[dict]):
    """Sample the DEM onto a coarser grid for the ray march."""
    west, south, east, north = bounds
    m_lat, m_lon = meters_per_degree((south + north) / 2)
    cell_y = (north - south) * m_lat / elev.shape[0]
    cell_x = (east - west) * m_lon / elev.shape[1]
    stride = max(1, round(GRID_M / ((cell_x + cell_y) / 2)))
    coarse = elev[::stride, ::stride]
    # Keep a source on the coarse cell that contains its fine cell.
    for source in sources:
        source["crow"] = min(source["row"] // stride, coarse.shape[0] - 1)
        source["ccol"] = min(source["col"] // stride, coarse.shape[1] - 1)
    c_lat, c_lon = _axes(bounds, coarse.shape)
    # Cell size of the coarse grid, from its own edges.
    cy = (north - south) * m_lat / coarse.shape[0]
    cx = (east - west) * m_lon / coarse.shape[1]
    print(
        f"audibility grid {coarse.shape[1]}x{coarse.shape[0]} "
        f"at {cx:.0f} x {cy:.0f} m (stride {stride})",
        flush=True,
    )
    return coarse, c_lat, c_lon, cx, cy


def _max_excess(elev, src_r, src_c, zs, dr, dc, steps, dist, zr, cell_x, cell_y):
    """Highest intervening terrain above the curved-earth chord, in meters."""
    limit = int(steps.max()) if steps.size else 0
    max_excess = np.full(dr.shape[0], -1.0e9, dtype=np.float64)
    two_r = 2.0 * EARTH_RADIUS_M
    zr_adj = zr - (dist * dist) / two_r
    cell = max(cell_x, cell_y)
    for step in range(1, limit):
        active = step < steps
        if not np.any(active):
            break
        frac = step / np.maximum(steps, 1)
        rr = np.rint(src_r + dr * frac).astype(np.int32)
        cc = np.rint(src_c + dc * frac).astype(np.int32)
        np.clip(rr, 0, elev.shape[0] - 1, out=rr)
        np.clip(cc, 0, elev.shape[1] - 1, out=cc)
        sample_d = np.hypot((rr - src_r) * cell_y, (cc - src_c) * cell_x)
        active &= (dist - sample_d) > cell
        active &= sample_d > cell
        z_adj = elev[rr, cc] - (sample_d * sample_d) / two_r
        line = zs + (zr_adj - zs) * (sample_d / np.maximum(dist, 1.0))
        excess = np.where(active, z_adj - line, -1.0e9)
        np.maximum(max_excess, excess, out=max_excess)
    return max_excess


def audibility_from(elev, src_r, src_c, zs, cell_x, cell_y) -> np.ndarray:
    """Relative reach from one gun position. 1 is beside the gun, 0 is out of range."""
    nrows, ncols = elev.shape
    rows, cols = np.indices((nrows, ncols))
    dr = (rows - src_r).astype(np.float64)
    dc = (cols - src_c).astype(np.float64)
    dist = np.hypot(dr * cell_y, dc * cell_x)
    open_m = OPEN_MILES * MILE_M
    aud = np.zeros((nrows, ncols), dtype=np.float32)
    aud[src_r, src_c] = 1.0
    keep = (dist > max(cell_x, cell_y)) & (dist <= open_m) & np.isfinite(elev)
    flat_r = rows[keep]
    flat_c = cols[keep]
    flat_dr = dr[keep]
    flat_dc = dc[keep]
    flat_dist = dist[keep]
    zr = elev[flat_r, flat_c].astype(np.float64) + EAR_H_M
    steps = np.maximum(np.abs(flat_dr), np.abs(flat_dc)).astype(np.int32)
    excess = np.empty(flat_r.shape[0], dtype=np.float64)
    batch = 6000
    print(f"  rays {flat_r.shape[0]}  max steps {int(steps.max())}", flush=True)
    for start in range(0, flat_r.shape[0], batch):
        stop = min(start + batch, flat_r.shape[0])
        excess[start:stop] = _max_excess(
            elev,
            src_r,
            src_c,
            zs,
            flat_dr[start:stop],
            flat_dc[start:stop],
            steps[start:stop],
            flat_dist[start:stop],
            zr[start:stop],
            cell_x,
            cell_y,
        )
    barrier = np.clip(excess, 0.0, None)
    term = distance_term(flat_dist) * np.exp(-barrier / BARRIER_SCALE_M)
    aud[flat_r, flat_c] = term.astype(np.float32)
    return aud


def compute_audibility(coarse, sources, cell_x, cell_y) -> dict[str, np.ndarray]:
    fields = {}
    for source in sources:
        print(f"audibility {source['id']}", flush=True)
        # Gun height uses the fine-grid crest, not the averaged coarse cell.
        zs = source["elev_m"] + SOURCE_H_M
        fields[source["id"]] = audibility_from(
            coarse, source["crow"], source["ccol"], zs, cell_x, cell_y
        )
    return fields


def sample_audibility(fields, lat, lon, point_lat, point_lon) -> dict[str, float]:
    r = int(np.clip(np.argmin(np.abs(lat - point_lat)), 0, lat.shape[0] - 1))
    c = int(np.clip(np.argmin(np.abs(lon - point_lon)), 0, lon.shape[0] - 1))
    return {key: float(grid[r, c]) for key, grid in fields.items()}


def hillshade(elev: np.ndarray, cell_x: float, cell_y: float) -> np.ndarray:
    """Horn hillshade, lit from the northwest. Row 0 is north."""
    padded = np.pad(elev, 1, mode="edge")
    dzdx = (
        padded[:-2, 2:]
        + 2 * padded[1:-1, 2:]
        + padded[2:, 2:]
        - (padded[:-2, :-2] + 2 * padded[1:-1, :-2] + padded[2:, :-2])
    ) / (8 * cell_x)
    dzdy = (
        padded[2:, :-2]
        + 2 * padded[2:, 1:-1]
        + padded[2:, 2:]
        - (padded[:-2, :-2] + 2 * padded[:-2, 1:-1] + padded[:-2, 2:])
    ) / (8 * cell_y)
    slope = np.arctan(np.hypot(dzdx, dzdy))
    aspect = np.arctan2(dzdy, -dzdx)
    zenith = np.deg2rad(48)
    azimuth = np.deg2rad(315)
    shaded = np.cos(zenith) * np.cos(slope) + np.sin(zenith) * np.sin(slope) * np.cos(
        azimuth - aspect
    )
    return np.clip(shaded, 0, 1).astype(np.float32)


def resize_bilinear(grid: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    """Resample a north-up grid onto the display raster."""
    if grid.shape == (out_h, out_w):
        return grid
    ys = np.linspace(0, grid.shape[0] - 1, out_h)
    xs = np.linspace(0, grid.shape[1] - 1, out_w)
    y0 = np.floor(ys).astype(np.int32)
    x0 = np.floor(xs).astype(np.int32)
    y1 = np.clip(y0 + 1, 0, grid.shape[0] - 1)
    x1 = np.clip(x0 + 1, 0, grid.shape[1] - 1)
    wy = (ys - y0)[:, None]
    wx = (xs - x0)[None, :]
    g00 = grid[y0][:, x0]
    g01 = grid[y0][:, x1]
    g10 = grid[y1][:, x0]
    g11 = grid[y1][:, x1]
    return (
        g00 * (1 - wy) * (1 - wx)
        + g01 * (1 - wy) * wx
        + g10 * wy * (1 - wx)
        + g11 * wy * wx
    )


def ground_color(
    elev: np.ndarray, shade: np.ndarray, basemap: np.ndarray | None
) -> np.ndarray:
    """Dark relief. A faint Esri canvas keeps the streets of the modern city."""
    span = max(float(np.nanmax(elev) - np.nanmin(elev)), 1.0)
    height = (elev - float(np.nanmin(elev))) / span
    low = np.array([0.07, 0.09, 0.07], dtype=np.float32)
    high = np.array([0.34, 0.31, 0.24], dtype=np.float32)
    tint = low + (high - low) * height[..., None]
    lit = (0.42 + 0.78 * shade)[..., None]
    relief = np.clip(tint * lit, 0, 1)
    if basemap is None:
        return relief
    return np.clip(
        relief * 0.78 + basemap * (0.28 + 0.45 * shade)[..., None] * 0.55, 0, 1
    )


def composite_reach(base: np.ndarray, fields: dict[str, np.ndarray]) -> np.ndarray:
    """Mix the three reaches by relative strength. Order does not pick the color."""
    order = ("chickamauga", "lookout", "missionary")
    weights = []
    for key in order:
        aud = np.clip(fields[key], 0, 1)
        weights.append(np.where(aud < 0.045, 0, aud) ** 0.82)
    stack = np.stack(weights)
    total = stack.sum(axis=0)
    mix = np.zeros(base.shape, dtype=np.float32)
    for key, weight in zip(order, stack, strict=True):
        rgb = np.array(
            [int(COLORS[key][i : i + 2], 16) for i in (1, 3, 5)], dtype=np.float32
        )
        mix += (rgb / 255.0) * weight[..., None]
    mix /= np.maximum(total, 1e-6)[..., None]
    alpha = np.clip(stack.max(axis=0) * 0.80, 0, 0.82)
    return np.clip(base * (1 - alpha[..., None]) + mix * alpha[..., None], 0, 1)


def fetch_basemap(bounds, shape) -> np.ndarray | None:
    west, south, east, north = bounds
    nrows, ncols = shape
    # Cap the export. The relief grid is resampled onto this image either way.
    width = min(ncols, 1600)
    height = min(nrows, 1600)
    query = (
        f"?bbox={west},{south},{east},{north}&bboxSR=4326&imageSR=4326"
        f"&size={width},{height}&format=png32&f=image"
    )
    try:
        payload = _get(ESRI_EXPORT + query, timeout=120)
    except OSError as exc:
        print(f"basemap skipped ({exc})", flush=True)
        return None
    if not payload.startswith(b"\x89PNG"):
        print("basemap skipped (not a PNG)", flush=True)
        return None
    image = Image.open(__import__("io").BytesIO(payload)).convert("RGB")
    image = image.resize((ncols, nrows), Image.Resampling.BILINEAR)
    print(f"basemap {width}x{height}", flush=True)
    return np.asarray(image).astype(np.float32) / 255.0


def ring(lat0: float, lon0: float, miles: float) -> tuple[np.ndarray, np.ndarray]:
    m_lat, m_lon = meters_per_degree(lat0)
    radius = miles * MILE_M
    theta = np.linspace(0, 2 * math.pi, 420)
    lat = lat0 + (radius * np.cos(theta)) / m_lat
    lon = lon0 + (radius * np.sin(theta)) / m_lon
    return lon, lat


def draw_polygon(ax, poly, **kwargs):
    geoms = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
    for geom in geoms:
        if geom.is_empty:
            continue
        ring_xy = np.asarray(geom.exterior.coords)
        ax.add_patch(MplPolygon(ring_xy, **kwargs))


def hex_rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))


def render_poster(
    elev, bounds, shade, fields_fine, parts, cemetery, city, sources, stats
):
    west, south, east, north = bounds
    m_lat, m_lon = meters_per_degree((south + north) / 2)
    width_m = (east - west) * m_lon
    height_m = (north - south) * m_lat
    map_w = 9.15
    map_h = map_w * height_m / width_m
    fig_h = map_h + 0.55
    fig_w = map_w + 4.15
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=150, facecolor=BG)
    ax = fig.add_axes([0.012, 0.045 / fig_h, map_w / fig_w, map_h / fig_h])
    ax.set_axis_off()
    base = ground_color(elev, shade, stats.get("basemap"))
    image = composite_reach(base, fields_fine)
    ax.imshow(
        image,
        extent=[west, east, south, north],
        origin="upper",
        interpolation="bilinear",
        zorder=1,
    )
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    ax.set_aspect(m_lat / m_lon)

    for poly in parts:
        draw_polygon(
            ax,
            poly,
            closed=True,
            fill=False,
            edgecolor="#E7E1D2",
            linewidth=0.45,
            alpha=0.55,
            zorder=3,
        )
    draw_polygon(
        ax,
        cemetery,
        closed=True,
        facecolor="#F4F1E6",
        edgecolor="#F4F1E6",
        linewidth=0.6,
        alpha=0.92,
        zorder=4,
    )

    chick = next(src for src in sources if src["id"] == "chickamauga")
    ring_lon, ring_lat = ring(chick["lat"], chick["lon"], HEARD_MILES)
    ax.plot(
        ring_lon,
        ring_lat,
        color=INK,
        linewidth=0.7,
        linestyle=(0, (1.2, 1.6)),
        alpha=0.55,
        zorder=3,
    )

    stroke = [withStroke(linewidth=2.4, foreground=BG)]
    offsets = {
        "chickamauga": (0.0, -0.012, "Chickamauga"),
        "lookout": (-0.03, 0.008, "Lookout Mountain"),
        "missionary": (0.028, 0.006, "Missionary Ridge"),
    }
    for source in sources:
        color = COLORS[source["id"]]
        ax.scatter(
            [source["lon"]],
            [source["lat"]],
            s=18,
            c=color,
            edgecolors=BG,
            linewidths=0.4,
            zorder=5,
        )
        dx, dy, name = offsets[source["id"]]
        ax.text(
            source["lon"] + dx,
            source["lat"] + dy,
            name,
            color=color,
            fontsize=8,
            fontweight="bold",
            ha="center",
            va="center",
            path_effects=stroke,
            zorder=6,
        )
    ax.text(
        city[1],
        city[0] + 0.012,
        "Chattanooga",
        color=INK,
        fontsize=8.5,
        fontweight="bold",
        ha="center",
        va="bottom",
        path_effects=stroke,
        zorder=6,
    )
    cem_c = cemetery.centroid
    ax.text(
        cem_c.x + 0.012,
        cem_c.y - 0.01,
        "National Cemetery",
        color=INK,
        fontsize=7,
        ha="left",
        va="top",
        path_effects=stroke,
        zorder=6,
    )
    # Keep the 10-mile label on the open eastern arc, clear of the city labels.
    label_lon, label_lat = ring(chick["lat"], chick["lon"], HEARD_MILES)
    eastern = int(np.argmax(label_lon))
    ax.text(
        label_lon[eastern],
        label_lat[eastern],
        "10 mi",
        color=INK,
        fontsize=7,
        ha="left",
        va="center",
        path_effects=stroke,
        zorder=6,
    )
    ax.text(
        west + 0.012,
        north - 0.012,
        "N",
        color=INK,
        fontsize=9,
        fontweight="bold",
        ha="left",
        va="top",
        path_effects=stroke,
        zorder=6,
    )

    rail_x = 0.745
    fig.text(
        rail_x,
        0.955,
        "WHERE THE GUNS",
        color=INK,
        fontsize=15,
        fontweight="bold",
        ha="left",
        va="top",
    )
    fig.text(
        rail_x,
        0.915,
        "WERE HEARD",
        color=INK,
        fontsize=15,
        fontweight="bold",
        ha="left",
        va="top",
    )
    fig.text(
        rail_x,
        0.868,
        "Day 11  ·  Senses: Sound\nVeterans Day  ·  November 11, 2026",
        color=MUTED,
        fontsize=8,
        ha="left",
        va="top",
        linespacing=1.35,
    )
    fig.text(
        rail_x,
        0.795,
        "Estimated audible reach of Civil War\n"
        "artillery over modern Chattanooga.\n"
        "A relative proxy, not a decibel model.",
        color=INK,
        fontsize=8,
        ha="left",
        va="top",
        linespacing=1.35,
    )

    swatch_y = 0.68
    entries = [
        ("chickamauga", "Chickamauga", "Sept 19–20, 1863"),
        ("lookout", "Lookout Mountain", "Nov 24, 1863"),
        ("missionary", "Missionary Ridge", "Nov 25, 1863"),
    ]
    for source_id, name, date in entries:
        fig.patches.append(
            FancyBboxPatch(
                (rail_x, swatch_y - 0.008),
                0.018,
                0.016,
                transform=fig.transFigure,
                facecolor=COLORS[source_id],
                edgecolor="none",
                boxstyle="square,pad=0",
                mutation_aspect=0.6,
            )
        )
        fig.text(
            rail_x + 0.028,
            swatch_y + 0.006,
            name,
            color=INK,
            fontsize=8.5,
            fontweight="bold",
            ha="left",
            va="center",
        )
        fig.text(
            rail_x + 0.028,
            swatch_y - 0.012,
            date,
            color=MUTED,
            fontsize=7.5,
            ha="left",
            va="center",
        )
        swatch_y -= 0.048

    city_mi = stats["chickamauga_to_city_mi"]
    cem_mi = stats["chickamauga_to_cemetery_mi"]
    fig.text(
        rail_x,
        0.50,
        "The dashed ring is 10 miles from\n"
        "the Chickamauga field, on open\n"
        f"ground. Downtown is {city_mi:.1f} miles\n"
        f"from that point; the cemetery is\n"
        f"{cem_mi:.1f}. The wash fades out at\n"
        "15 miles if no ridge intervenes.\n\n"
        "Lookout and Missionary Ridge\n"
        "cut the reach where they rise\n"
        "above the path. A ridge about\n"
        "90 m above the path leaves\n"
        "roughly a third of the proxy.\n\n"
        "The cemetery, opened December\n"
        "25, 1863, sits in the valley\n"
        "between the mountain and the ridge.",
        color=MUTED,
        fontsize=7.4,
        ha="left",
        va="top",
        linespacing=1.32,
    )
    fig.text(
        rail_x,
        0.055,
        "NPS park boundary  ·  USGS 3DEP\n"
        "OpenStreetMap cemetery and city\n"
        "Esri Dark Gray Canvas\n"
        "Representative points, not batteries.",
        color=MUTED,
        fontsize=6.6,
        ha="left",
        va="bottom",
        linespacing=1.3,
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=150, facecolor=BG)
    plt.close(fig)
    print(f"wrote {OUT_PNG.relative_to(ROOT)}", flush=True)


def write_overlays(fields, bounds):
    """Small transparent washes for the Leaflet page."""
    DAY.mkdir(parents=True, exist_ok=True)
    for key, grid in fields.items():
        height, width = grid.shape
        limit = 700
        scale = limit / max(height, width)
        if scale < 1:
            grid = resize_bilinear(grid, round(height * scale), round(width * scale))
        rgb = hex_rgb(COLORS[key])
        aud = np.clip(grid, 0, 1)
        alpha = np.where(aud < 0.045, 0, aud)
        alpha = (np.clip(alpha, 0, 1) ** 0.85 * 210).astype(np.uint8)
        image = np.zeros((*aud.shape, 4), dtype=np.uint8)
        image[..., 0] = rgb[0]
        image[..., 1] = rgb[1]
        image[..., 2] = rgb[2]
        image[..., 3] = alpha
        path = DAY / f"audibility-{key}.png"
        Image.fromarray(image, mode="RGBA").save(path, optimize=True)
        print(
            f"wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1e3:.0f} KB)",
            flush=True,
        )
    west, south, east, north = bounds
    return west, south, east, north


def write_web(bounds, parts, cemetery, city, sources, stats, park_feature):
    west, south, east, north = write_overlays(stats["coarse_fields"], bounds)
    payload = {
        "west": round(west, 5),
        "south": round(south, 5),
        "east": round(east, 5),
        "north": round(north, 5),
        "openMiles": OPEN_MILES,
        "heardMiles": HEARD_MILES,
        "heardLevel": HEARD_LEVEL,
        "barrierScaleM": BARRIER_SCALE_M,
        "chickamaugaToCityMiles": round(stats["chickamauga_to_city_mi"], 2),
        "chickamaugaToCemeteryMiles": round(stats["chickamauga_to_cemetery_mi"], 2),
        "sources": [
            {
                "id": src["id"],
                "name": src["name"],
                "date": src["date"],
                "lat": round(src["lat"], 5),
                "lon": round(src["lon"], 5),
                "elevM": round(src["elev_m"], 1),
                "note": src["note"],
            }
            for src in sources
        ],
    }
    (DAY / "bounds.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

    features = []
    for poly in parts:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "kind": "park",
                    "name": park_feature["properties"].get(
                        "UNIT_NAME",
                        "Chickamauga and Chattanooga National Military Park",
                    ),
                },
                "geometry": poly.__geo_interface__,
            }
        )
    features.append(
        {
            "type": "Feature",
            "properties": {"kind": "cemetery", "name": "Chattanooga National Cemetery"},
            "geometry": cemetery.__geo_interface__,
        }
    )
    features.append(
        {
            "type": "Feature",
            "properties": {"kind": "city", "name": "Chattanooga"},
            "geometry": Point(city[1], city[0]).__geo_interface__,
        }
    )
    for src in sources:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "kind": "source",
                    "id": src["id"],
                    "name": src["name"],
                    "date": src["date"],
                    "elevM": round(src["elev_m"], 1),
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(src["lon"], 5), round(src["lat"], 5)],
                },
            }
        )
    collection = {"type": "FeatureCollection", "features": features}
    (DAY / "places.geojson").write_text(json.dumps(collection) + "\n", encoding="utf-8")
    print(f"wrote {DAY.relative_to(ROOT)}/bounds.json and places.geojson", flush=True)


def check_story(sources, fields, lat, lon, city, cemetery) -> dict:
    by_id = {src["id"]: src for src in sources}
    chick = by_id["chickamauga"]
    look = by_id["lookout"]
    miss = by_id["missionary"]
    city_lat, city_lon = city
    cem = cemetery.centroid
    to_city = miles_between(chick["lat"], chick["lon"], city_lat, city_lon)
    to_cem = miles_between(chick["lat"], chick["lon"], cem.y, cem.x)
    print(
        f"Chickamauga to downtown {to_city:.2f} mi; to cemetery {to_cem:.2f} mi",
        flush=True,
    )
    if not 7.0 <= to_city <= 14.0:
        raise RuntimeError(
            f"Chickamauga-to-city distance {to_city:.1f} mi is outside 7–14."
        )
    if look["elev_m"] < chick["elev_m"] + 120:
        raise RuntimeError(
            "Lookout source is not on the mountain relative to Chickamauga."
        )
    if miss["elev_m"] < chick["elev_m"] + 25:
        raise RuntimeError(
            "Missionary Ridge source is not above the Chickamauga field."
        )

    at_city = sample_audibility(fields, lat, lon, city_lat, city_lon)
    at_cem = sample_audibility(fields, lat, lon, cem.y, cem.x)
    print(
        f"proxy at downtown { {k: round(v, 2) for k, v in at_city.items()} }",
        flush=True,
    )
    print(
        f"proxy at cemetery { {k: round(v, 2) for k, v in at_cem.items()} }", flush=True
    )
    if at_city["chickamauga"] < 0.2:
        raise RuntimeError(
            "Chickamauga reach at downtown is below 0.2; the valley path should stay open."
        )

    # West of Lookout versus toward the city, at the same distance from the point.
    m_lat, m_lon = meters_per_degree(look["lat"])
    step = 7000.0
    east = sample_audibility(
        fields,
        lat,
        lon,
        look["lat"] + step / m_lat * 0.45,
        look["lon"] + step / m_lon * 0.9,
    )
    west = sample_audibility(
        fields,
        lat,
        lon,
        look["lat"] - step / m_lat * 0.2,
        look["lon"] - step / m_lon,
    )
    print(
        f"Lookout proxy 7 km toward the city {east['lookout']:.2f}; west {west['lookout']:.2f}",
        flush=True,
    )
    return {
        "chickamauga_to_city_mi": to_city,
        "chickamauga_to_cemetery_mi": to_cem,
        "at_city": at_city,
        "at_cemetery": at_cem,
        "lookout_toward_city": east["lookout"],
        "lookout_west": west["lookout"],
    }


def self_check_decay() -> None:
    heard = HEARD_MILES * MILE_M
    outer = OPEN_MILES * MILE_M
    samples = distance_term(np.array([0.0, heard, outer, outer + 1000]))
    if abs(samples[0] - 1) > 1e-9 or abs(samples[1] - HEARD_LEVEL) > 1e-9:
        raise RuntimeError("Distance fade does not hit the stated anchors.")
    if samples[2] > 1e-9 or samples[3] != 0:
        raise RuntimeError("Distance fade does not reach zero at 15 miles.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh", action="store_true", help="Redownload cached sources"
    )
    args = parser.parse_args()
    self_check_decay()
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    park_feature, parts = load_boundary(args.refresh)
    cemetery = load_cemetery(args.refresh)
    city = load_city(args.refresh)
    chick, look_mass, missionary = choose_parts(parts)
    # 16 miles of pad so a point inside each unit still has a full 15-mile reach.
    bounds = expand_bounds([chick, look_mass, missionary], (OPEN_MILES + 1) * MILE_M)
    elev, dem_bounds = load_dem(bounds, args.refresh)
    # Use the raster edges, which may differ by a fraction of a pixel.
    bounds = dem_bounds
    sources = locate_sources(chick, look_mass, missionary, parts, elev, bounds)
    coarse, c_lat, c_lon, cell_x, cell_y = stride_grid(elev, bounds, sources)

    if GRID_PATH.exists() and not args.refresh:
        stored = np.load(GRID_PATH)
        fields = {key: stored[key] for key in ("chickamauga", "lookout", "missionary")}
        print(f"using cached {GRID_PATH.name}", flush=True)
    else:
        fields = compute_audibility(coarse, sources, cell_x, cell_y)
        np.savez_compressed(GRID_PATH, **fields)
        print(f"wrote {GRID_PATH.name}", flush=True)

    stats = check_story(sources, fields, c_lat, c_lon, city, cemetery)
    m_lat, m_lon = meters_per_degree((bounds[1] + bounds[3]) / 2)
    fine_x = (bounds[2] - bounds[0]) * m_lon / elev.shape[1]
    fine_y = (bounds[3] - bounds[1]) * m_lat / elev.shape[0]
    shade = hillshade(elev, fine_x, fine_y)
    fields_fine = {
        key: resize_bilinear(grid, elev.shape[0], elev.shape[1]).astype(np.float32)
        for key, grid in fields.items()
    }
    stats["basemap"] = fetch_basemap(bounds, elev.shape)
    stats["coarse_fields"] = fields
    render_poster(
        elev, bounds, shade, fields_fine, parts, cemetery, city, sources, stats
    )
    write_web(bounds, parts, cemetery, city, sources, stats, park_feature)


if __name__ == "__main__":
    main()
