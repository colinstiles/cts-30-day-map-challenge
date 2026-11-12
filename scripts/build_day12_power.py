#!/usr/bin/env python3
"""Day 12 — Power. Year 5 of the full-scale war: the claim and the hold.

Downloads stay in data/raw and data/processed. The sheet and the simplified
time-map file are the pieces that get committed.

Assessed control is the DeepStateMap occupied-area polygon, clipped to the
geoBoundaries Ukraine outline. Areas are measured on a Ukraine Albers
equal-area projection (parallels 46N and 52N, origin 48N, 32E, WGS84).

Behind Zscaler, point SSL_CERT_FILE at the corporate certificate. Leave TLS
verification on.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import geopandas as gpd
import matplotlib.pyplot as plt
import shapely
from matplotlib import font_manager
from matplotlib.patches import Rectangle
from shapely.geometry import box, mapping, shape

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "day12"
PROCESSED = ROOT / "data" / "processed" / "day12"
DAY = ROOT / "2026" / "12_power"
OUT_PNG = ROOT / "2026" / "images" / "day-12.png"
OUT_FRAMES = DAY / "frames.json"
GIS = DAY / "gis"
GPKG = GIS / "year5-power.gpkg"
GEOLIBRE = DAY / "year5-the-claim-and-the-hold.geolibre.json"
AREA_NOTE = (
    "km2 values were measured on Ukraine Albers (parallels 46N and 52N, "
    "origin 48N 32E, WGS84). This file is EPSG:4326. "
    "held_end_pct divides by the geoBoundaries polygon, which includes sea "
    "for Crimea and Sevastopol."
)

USER_AGENT = "cts-30-day-map-challenge day12"
YEAR5_START = date(2026, 2, 24)
GB_API = "https://www.geoboundaries.org/api/current/gbOpen/UKR/{level}/"
NE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_50m_admin_0_countries.geojson"
)
# The mirror names files deepstatemap_data_YYYYMMDD.geojson, with no hyphens.
SNAPSHOT_URL = (
    "https://raw.githubusercontent.com/cyterat/deepstate-map-data/"
    "main/data/deepstatemap_data_{stamp}.geojson"
)

# Equal-area for Ukraine. State it on the sheet and in the build log.
ALBERS = (
    "+proj=aea +lat_1=46 +lat_2=52 +lat_0=48 +lon_0=32 "
    "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
)
WORK_TOLERANCE_M = 100.0
SHEET_W_IN = 11.0
SHEET_H_IN = 17.0
SHEET_DPI = 150

PAPER = "#F3F0EA"
INK = "#241F1A"
MUTED = "#5C564E"
WATER = "#D5DDE0"
NEIGHBOR = "#E6E0D6"
UKRAINE_FILL = "#E4DDD2"
CLAIM = "#C6A15A"
HELD = "#9A8F82"
GAIN = "#A15C38"
RETAKEN = "#3E6B58"

# shapeName / ISO text only has to contain one of these tokens.
CLAIM_KEYS = (
    ("Sevastopol", ("sevastopol",)),
    ("Kherson", ("kherson",)),
    ("Zaporizhzhia", ("zaporiz",)),
    ("Donetsk", ("donetsk",)),
    ("Luhansk", ("luhansk", "luhans")),
    ("Crimea", ("crimea", "krym")),
)
REQUIRED_CLAIMS = ("Kherson", "Zaporizhzhia", "Donetsk", "Luhansk", "Crimea")
CLAIM_ORDER = ("Kherson", "Zaporizhzhia", "Donetsk", "Luhansk", "Crimea", "Sevastopol")

# Ordinary city centers, so the oblasts can be read. label=True on the national sheet.
CITIES = (
    ("Kyiv", 50.4501, 30.5234, True),
    ("Kharkiv", 49.9935, 36.2304, True),
    ("Sumy", 50.9077, 34.7981, False),
    ("Dnipro", 48.4647, 35.0462, True),
    ("Zaporizhzhia", 47.8388, 35.1396, False),
    ("Donetsk", 48.0159, 37.8028, True),
    ("Luhansk", 48.5740, 39.3078, False),
    ("Mariupol", 47.0971, 37.5434, False),
    ("Kherson", 46.6354, 32.6169, True),
    ("Simferopol", 44.9521, 34.1024, True),
    ("Sevastopol", 44.6166, 33.5254, False),
    ("Odesa", 46.4825, 30.7233, True),
    ("Kupiansk", 49.7064, 37.6165, False),
    ("Kramatorsk", 48.7233, 37.5564, False),
    ("Pokrovsk", 48.2820, 37.1758, False),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Redownload cached files.")
    parser.add_argument("--opening-m", type=float, default=150.0)
    parser.add_argument("--min-km2", type=float, default=0.5)
    parser.add_argument("--end", default="2026-11-12", help="Last day to request, YYYY-MM-DD.")
    parser.add_argument(
        "--gis-only",
        action="store_true",
        help="Write the GIS package and GeoLibre project, and skip the draft sheet.",
    )
    return parser.parse_args()


def http_get(url: str, timeout: int = 180) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise FileNotFoundError(url) from exc
        raise SystemExit(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not reach {url}\n{exc}\n"
            "Behind Zscaler, set SSL_CERT_FILE to the local corporate certificate. "
            "Leave TLS verification on."
        ) from exc


def download(url: str, dest: Path, refresh: bool) -> None:
    if dest.exists() and dest.stat().st_size > 0 and not refresh:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"GET {url}")
    dest.write_bytes(http_get(url))


def font_family() -> str:
    available = {found.name for found in font_manager.fontManager.ttflist}
    for name in ("Georgia", "Palatino Linotype", "Times New Roman", "DejaVu Serif"):
        if name in available:
            return name
    return "DejaVu Serif"


def iter_polygons(geom):
    if geom is None or geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        yield geom
    elif geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        for part in geom.geoms:
            yield from iter_polygons(part)


def as_multi(parts: list):
    kept = [part for part in parts if part is not None and not part.is_empty and part.area > 0]
    if not kept:
        return shapely.MultiPolygon([])
    if len(kept) == 1:
        return kept[0]
    return shapely.MultiPolygon(kept)


def polygons_only(geom):
    return as_multi(list(iter_polygons(geom)))


def km2(geom) -> float:
    if geom is None or geom.is_empty:
        return 0.0
    return float(geom.area) / 1_000_000.0


def open_geom(geom, meters: float):
    if geom is None or geom.is_empty or meters <= 0:
        return polygons_only(geom)
    opened = geom.buffer(-meters).buffer(meters).buffer(0)
    return polygons_only(opened)


def drop_small(geom, min_m2: float):
    return as_multi([part for part in iter_polygons(geom) if part.area >= min_m2])


def load_polygons(path: Path) -> gpd.GeoDataFrame:
    try:
        frame = gpd.read_file(path)
    except Exception:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("type") == "FeatureCollection":
            geoms = [shape(feature["geometry"]) for feature in payload["features"] if feature.get("geometry")]
        else:
            geoms = [shape(payload)]
        frame = gpd.GeoDataFrame(geometry=geoms, crs="EPSG:4326")
    if frame.crs is None:
        frame = frame.set_crs(4326)
    else:
        frame = frame.to_crs(4326)
    return frame


def occupied_geometry(path: Path):
    frame = load_polygons(path)
    parts = []
    for geom in frame.geometry:
        if geom is None or geom.is_empty:
            continue
        if not geom.is_valid:
            geom = geom.buffer(0)
        parts.extend(iter_polygons(geom))
    if not parts:
        raise SystemExit(f"No polygons in {path}")
    return shapely.union_all(parts)


def project_working(geom, ukraine):
    projected = gpd.GeoSeries([geom], crs=4326).to_crs(ALBERS).iloc[0]
    projected = polygons_only(projected.buffer(0).intersection(ukraine))
    return polygons_only(projected.simplify(WORK_TOLERANCE_M, preserve_topology=True))


def working_occupied(path: Path, ukraine, refresh: bool):
    cache = PROCESSED / f"{path.stem}.wkb"
    if cache.exists() and cache.stat().st_size > 0 and not refresh:
        return shapely.from_wkb(cache.read_bytes())
    PROCESSED.mkdir(parents=True, exist_ok=True)
    geom = project_working(occupied_geometry(path), ukraine)
    cache.write_bytes(geom.wkb)
    return geom


def fetch_geoboundaries(level: str, dest: Path, refresh: bool) -> gpd.GeoDataFrame:
    if not (dest.exists() and dest.stat().st_size > 0 and not refresh):
        meta = json.loads(http_get(GB_API.format(level=level)))
        url = meta.get("gjDownloadURL") or meta.get("simplifiedGeometryGeoJSON")
        if not url:
            raise SystemExit(f"geoBoundaries {level} response had no download URL.")
        download(url, dest, refresh=True)
    return load_polygons(dest)


def claim_label(text: str) -> str | None:
    folded = text.casefold().replace("'", "").replace("’", "").replace("`", "")
    for label, tokens in CLAIM_KEYS:
        if any(token in folded for token in tokens):
            return label
    return None


def row_blob(row) -> str:
    preferred = []
    index = getattr(row, "index", None)
    if index is not None:
        for key in ("shapeName", "shapeISO", "NAME", "name", "ADM1_EN"):
            if key in index and isinstance(row[key], str):
                preferred.append(row[key])
    if preferred:
        return " ".join(preferred)
    parts = []
    for value in row:
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts)


def extract_claims(oblasts: gpd.GeoDataFrame, ukraine):
    grouped: dict[str, list] = {}
    for _, row in oblasts.iterrows():
        label = claim_label(row_blob(row))
        if label is None or row.geometry is None:
            continue
        projected = gpd.GeoSeries([row.geometry], crs=4326).to_crs(ALBERS).iloc[0]
        grouped.setdefault(label, []).append(polygons_only(projected.buffer(0).intersection(ukraine)))
    found = {}
    for label, parts in grouped.items():
        found[label] = polygons_only(shapely.union_all(parts))
    missing = [label for label in REQUIRED_CLAIMS if label not in found]
    if missing:
        names = sorted({str(value) for value in oblasts.to_numpy().ravel() if isinstance(value, str)})
        raise SystemExit(
            "Could not match claimed regions: "
            + ", ".join(missing)
            + "\nOblast text in the file:\n"
            + "\n".join(names)
        )
    return found


def snapshot_stamp(day: date) -> str:
    return day.strftime("%Y%m%d")


def resolve_snapshot(day: date, refresh: bool, back: int = 6) -> tuple[date, Path]:
    for offset in range(back + 1):
        candidate = day - timedelta(days=offset)
        stamp = snapshot_stamp(candidate)
        dest = RAW / f"deepstatemap_data_{stamp}.geojson"
        if dest.exists() and dest.stat().st_size > 0 and not refresh:
            return candidate, dest
        url = SNAPSHOT_URL.format(stamp=stamp)
        try:
            payload = http_get(url)
        except FileNotFoundError:
            print(f"No snapshot for {candidate.isoformat()}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
        print(f"Saved {dest.name} ({len(payload) / 1e6:.1f} MB)")
        return candidate, dest
    raise SystemExit(f"No DeepStateMap snapshot within {back} days of {day.isoformat()}.")


def weekly_dates(start: date, end: date) -> list[date]:
    days = []
    cursor = start
    while cursor < end:
        days.append(cursor)
        cursor += timedelta(days=7)
    days.append(end)
    return days


def round_coords(node, digits: int = 4):
    if isinstance(node, (list, tuple)):
        if node and isinstance(node[0], (int, float)) and not isinstance(node[0], bool):
            return [round(float(value), digits) for value in node]
        return [round_coords(item, digits) for item in node]
    return node


def web_geom(geom, tolerance_m: float):
    if geom is None or geom.is_empty:
        return None
    simplified = polygons_only(geom.simplify(tolerance_m, preserve_topology=True))
    if simplified.is_empty:
        return None
    exported = gpd.GeoSeries([simplified], crs=ALBERS).to_crs(4326).iloc[0]
    return round_coords(mapping(exported))


def safe_diff(source, other):
    return polygons_only(polygons_only(source).difference(polygons_only(other)))


def build_frames(dates, geoms, opening_m: float, min_km2: float):
    baseline = geoms[0]
    min_m2 = min_km2 * 1_000_000.0
    frames = []
    for day, geom in zip(dates, geoms):
        gained_raw = safe_diff(geom, baseline)
        retaken_raw = safe_diff(baseline, geom)
        gained = drop_small(open_geom(gained_raw, opening_m), min_m2)
        retaken = drop_small(open_geom(retaken_raw, opening_m), min_m2)
        frames.append(
            {
                "date": day.isoformat(),
                "held_km2": round(km2(geom), 1),
                "gained_raw_km2": round(km2(gained_raw), 1),
                "retaken_raw_km2": round(km2(retaken_raw), 1),
                "gained_km2": round(km2(gained), 1),
                "retaken_km2": round(km2(retaken), 1),
                "gained_geom": gained,
                "retaken_geom": retaken,
            }
        )
        print(
            f"{day.isoformat()}  held {km2(geom):,.0f} km²  "
            f"drawn +{km2(gained):,.0f} / −{km2(retaken):,.0f}  "
            f"unfiltered +{km2(gained_raw):,.0f} / −{km2(retaken_raw):,.0f}"
        )
    return frames


def oblast_rows(claims: dict, held) -> list[dict]:
    rows = []
    for name in CLAIM_ORDER:
        geom = claims.get(name)
        if geom is None or geom.is_empty:
            continue
        area = km2(geom)
        held_area = km2(polygons_only(geom.intersection(held)))
        rows.append(
            {
                "name": name,
                "area_km2": round(area, 1),
                "held_km2": round(held_area, 1),
                "held_pct": round(100.0 * held_area / area, 1) if area else 0.0,
            }
        )
    return rows


def write_frames(payload_frames, claims, held, ukraine, rows, meta: dict) -> None:
    claim_features = []
    for name in CLAIM_ORDER:
        geom = claims.get(name)
        if geom is None:
            continue
        claim_features.append({"name": name, "geometry": web_geom(geom, 1000)})
    body = {
        **meta,
        "ukraine": web_geom(ukraine, 2000),
        "claim": claim_features,
        "held": web_geom(held, 800),
        "oblasts": rows,
        "cities": [
            {"name": name, "lat": lat, "lon": lon, "label": label}
            for name, lat, lon, label in CITIES
        ],
        "frames": [
            {
                "date": frame["date"],
                "held_km2": frame["held_km2"],
                "gained_km2": frame["gained_km2"],
                "retaken_km2": frame["retaken_km2"],
                "gained": web_geom(frame["gained_geom"], 400),
                "retaken": web_geom(frame["retaken_geom"], 400),
            }
            for frame in payload_frames
        ],
    }
    OUT_FRAMES.parent.mkdir(parents=True, exist_ok=True)
    OUT_FRAMES.write_text(json.dumps(body, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT_FRAMES.relative_to(ROOT)} ({OUT_FRAMES.stat().st_size / 1e6:.2f} MB)")


def add_geom(ax, geom, **style) -> None:
    if geom is None or geom.is_empty:
        return
    gpd.GeoSeries([geom], crs=ALBERS).plot(ax=ax, **style)


def draw_cities(ax, cities: gpd.GeoDataFrame, limits, family: str, size: float) -> None:
    minx, miny, maxx, maxy = limits
    dx = maxx - minx
    dy = maxy - miny
    for _, city in cities.iterrows():
        x, y = city.geometry.x, city.geometry.y
        if not (minx <= x <= maxx and miny <= y <= maxy):
            continue
        ax.plot(x, y, marker="o", markersize=2.2, color=INK, zorder=8)
        if city["label"]:
            ax.text(
                x + 0.012 * dx,
                y + 0.012 * dy,
                city["name"],
                fontsize=size,
                color=INK,
                fontfamily=family,
                zorder=9,
            )


def scale_bar(ax, family: str, length_m: float = 100_000) -> None:
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x = x0 + 0.06 * (x1 - x0)
    y = y0 + 0.05 * (y1 - y0)
    ax.plot([x, x + length_m], [y, y], color=INK, lw=1.1, solid_capstyle="butt", zorder=8)
    ax.text(x, y + 0.012 * (y1 - y0), "0", fontsize=7, color=INK, fontfamily=family, ha="center")
    ax.text(
        x + length_m,
        y + 0.012 * (y1 - y0),
        "100 km",
        fontsize=7,
        color=INK,
        fontfamily=family,
        ha="center",
    )


def north_arrow(ax, family: str) -> None:
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x = x0 + 0.08 * (x1 - x0)
    y = y1 - 0.08 * (y1 - y0)
    length = 0.04 * (y1 - y0)
    ax.annotate(
        "N",
        xy=(x, y),
        xytext=(x, y - length),
        ha="center",
        va="top",
        fontsize=8,
        color=INK,
        fontfamily=family,
        arrowprops={"arrowstyle": "-|>", "color": INK, "lw": 0.7},
        zorder=8,
    )


def render_sheet(ukraine, neighbors, claims, held_start, held_end, frames, rows, opening_m: float, family: str) -> None:
    baseline = frames[0]
    latest = frames[-1]
    claim = polygons_only(shapely.union_all(list(claims.values())))
    gained = frames[-1]["gained_geom"]
    retaken = frames[-1]["retaken_geom"]
    unheld = safe_diff(claim, held_end)

    fig = plt.figure(figsize=(SHEET_W_IN, SHEET_H_IN), dpi=SHEET_DPI, facecolor=PAPER)
    ax = fig.add_axes([0.04, 0.31, 0.92, 0.52])
    ax.set_facecolor(WATER)

    minx, miny, maxx, maxy = ukraine.bounds
    dx = maxx - minx
    dy = maxy - miny
    limits = (minx - 0.08 * dx, miny - 0.06 * dy, maxx + 0.06 * dx, maxy + 0.08 * dy)
    envelope = box(*limits)
    if neighbors is not None and not neighbors.empty:
        clipped = gpd.clip(neighbors.to_crs(ALBERS), envelope)
        clipped.plot(ax=ax, facecolor=NEIGHBOR, edgecolor="#C9C2B6", linewidth=0.2, zorder=1)

    add_geom(ax, ukraine, facecolor=UKRAINE_FILL, edgecolor=INK, linewidth=0.7, zorder=2)
    add_geom(ax, claim, facecolor=CLAIM, edgecolor=INK, linewidth=0.45, zorder=3)
    add_geom(ax, held_start, facecolor=HELD, edgecolor="none", linewidth=0, zorder=4)
    add_geom(ax, retaken, facecolor=RETAKEN, edgecolor=INK, linewidth=0.15, zorder=5)
    add_geom(ax, gained, facecolor=GAIN, edgecolor=INK, linewidth=0.15, zorder=6)
    add_geom(ax, ukraine, facecolor="none", edgecolor=INK, linewidth=0.8, zorder=7)

    ax.set_xlim(limits[0], limits[2])
    ax.set_ylim(limits[1], limits[3])
    ax.set_aspect("equal")
    ax.axis("off")

    cities = gpd.GeoDataFrame(
        {
            "name": [item[0] for item in CITIES],
            "label": [item[3] for item in CITIES],
        },
        geometry=gpd.points_from_xy(
            [item[2] for item in CITIES],
            [item[1] for item in CITIES],
        ),
        crs=4326,
    ).to_crs(ALBERS)
    draw_cities(ax, cities, limits, family, 7)
    scale_bar(ax, family)
    north_arrow(ax, family)

    inset_source = polygons_only(shapely.union_all([unheld, gained, retaken]))
    if not inset_source.is_empty:
        ix0, iy0, ix1, iy1 = inset_source.bounds
        pad_x = max((ix1 - ix0) * 0.18, 80_000)
        pad_y = max((iy1 - iy0) * 0.18, 80_000)
        inset_limits = (ix0 - pad_x, iy0 - pad_y, ix1 + pad_x, iy1 + pad_y)
        ax_in = fig.add_axes([0.055, 0.325, 0.36, 0.20])
        ax_in.set_facecolor(WATER)
        inset_box = box(*inset_limits)
        if neighbors is not None and not neighbors.empty:
            gpd.clip(neighbors.to_crs(ALBERS), inset_box).plot(
                ax=ax_in, facecolor=NEIGHBOR, edgecolor="none", zorder=1
            )
        add_geom(ax_in, ukraine, facecolor=UKRAINE_FILL, edgecolor=INK, linewidth=0.4, zorder=2)
        add_geom(ax_in, claim, facecolor=CLAIM, edgecolor=INK, linewidth=0.4, zorder=3)
        add_geom(ax_in, held_start, facecolor=HELD, edgecolor="none", zorder=4)
        add_geom(ax_in, retaken, facecolor=RETAKEN, edgecolor="none", zorder=5)
        add_geom(ax_in, gained, facecolor=GAIN, edgecolor="none", zorder=6)
        ax_in.set_xlim(inset_limits[0], inset_limits[2])
        ax_in.set_ylim(inset_limits[1], inset_limits[3])
        ax_in.set_aspect("equal")
        ax_in.axis("off")
        for spine in ax_in.spines.values():
            spine.set_visible(True)
            spine.set_color(INK)
            spine.set_linewidth(0.6)
        ax_in.set_title("Where the claim exceeds the hold", fontsize=8, color=INK, fontfamily=family, loc="left")
        inset_cities = cities.copy()
        inset_cities["label"] = True
        draw_cities(ax_in, inset_cities, inset_limits, family, 6)

    fig.text(0.06, 0.955, "Day 12  ·  Power", fontsize=11, color=MUTED, fontfamily=family)
    fig.text(0.06, 0.925, "The claim and the hold", fontsize=22, color=INK, fontfamily=family)
    fig.text(
        0.06,
        0.902,
        f"Year 5 of the full-scale war,  {baseline['date']}  to  {latest['date']}",
        fontsize=10,
        color=INK,
        fontfamily=family,
    )
    net = latest["gained_km2"] - latest["retaken_km2"]
    fig.text(
        0.06,
        0.878,
        (
            f"Occupied inside Ukraine:  {baseline['held_km2']:,.0f} km² on {baseline['date']}"
            f"    {latest['held_km2']:,.0f} km² on {latest['date']}"
            f"    drawn net {net:+,.0f} km²"
        ),
        fontsize=9,
        color=INK,
        fontfamily=family,
    )

    swatches = [
        (CLAIM, "Claimed, still not held"),
        (HELD, "Held on the first day of Year 5"),
        (GAIN, "Passed to Russian control"),
        (RETAKEN, "Passed back to Ukrainian control"),
    ]
    swatch_spots = [(0.06, 0.278), (0.52, 0.278), (0.06, 0.258), (0.52, 0.258)]
    for (color, label), (swatch_x, swatch_y) in zip(swatches, swatch_spots):
        fig.patches.append(
            Rectangle(
                (swatch_x, swatch_y),
                0.016,
                0.011,
                transform=fig.transFigure,
                facecolor=color,
                edgecolor=INK,
                linewidth=0.4,
                clip_on=False,
            )
        )
        fig.text(
            swatch_x + 0.02,
            swatch_y,
            label,
            fontsize=8,
            color=INK,
            fontfamily=family,
            va="bottom",
        )

    share_lines = ["Share of each claim assessed as occupied on " + latest["date"]]
    for row in rows:
        share_lines.append(f"{row['name']:<16}{row['held_pct']:5.1f}%")
    fig.text(0.06, 0.242, "\n".join(share_lines), fontsize=9, color=INK, fontfamily=family, va="top")

    month_last = {}
    for frame in frames:
        month_last[frame["date"][:7]] = frame
    labels = []
    values = []
    for key in sorted(month_last):
        frame = month_last[key]
        labels.append(datetime.strptime(key, "%Y-%m").strftime("%b"))
        values.append(frame["gained_km2"] - frame["retaken_km2"])
    ax_bar = fig.add_axes([0.50, 0.055, 0.44, 0.17])
    ax_bar.set_facecolor(PAPER)
    colors = [GAIN if value >= 0 else RETAKEN for value in values]
    ax_bar.bar(labels, values, color=colors, width=0.72, zorder=2)
    ax_bar.axhline(0, color=INK, linewidth=0.6, zorder=3)
    ax_bar.set_title("Cumulative drawn net, km² since the first day", fontsize=8, color=INK, fontfamily=family, loc="left")
    ax_bar.tick_params(labelsize=8, colors=INK, length=0)
    for spine in ax_bar.spines.values():
        spine.set_visible(False)
    ax_bar.spines["bottom"].set_color(INK)
    ax_bar.spines["bottom"].set_visible(True)

    raw_gain = latest["gained_raw_km2"]
    raw_loss = latest["retaken_raw_km2"]
    fig.text(
        0.06,
        0.028,
        (
            f"Drawn change drops pieces thinner than {opening_m:.0f} m. "
            f"Unfiltered difference +{raw_gain:,.0f} / −{raw_loss:,.0f} km². "
            "Assessed control © DeepStateMap.live. Outlines: geoBoundaries (CC BY 4.0). "
            "Neighbors: Natural Earth. An assessment, not a survey and not an official boundary.\n"
            "https://deepstatemap.live/          https://challenge.colinstiles.com/2026/day-12.html"
        ),
        fontsize=7.5,
        color=MUTED,
        fontfamily=family,
        va="bottom",
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=SHEET_DPI, facecolor=PAPER)
    plt.close(fig)
    print(f"Wrote {OUT_PNG.relative_to(ROOT)}")


def to_wgs(geom):
    if geom is None or geom.is_empty:
        return None
    exported = gpd.GeoSeries([polygons_only(geom)], crs=ALBERS).to_crs(4326).iloc[0]
    if exported.is_empty:
        return None
    return exported


def save_layer(name: str, frame: gpd.GeoDataFrame) -> Path:
    kept = frame[frame.geometry.notnull() & ~frame.geometry.is_empty].copy()
    if kept.empty:
        raise SystemExit(f"Layer {name} has no geometry.")
    kept = kept.reset_index(drop=True)
    geojson_path = GIS / f"{name}.geojson"
    kept.to_file(geojson_path, driver="GeoJSON")
    kwargs = {"layer": name, "driver": "GPKG"}
    if GPKG.exists():
        kwargs["mode"] = "a"
    kept.to_file(GPKG, **kwargs)
    print(f"Wrote {geojson_path.relative_to(ROOT)} ({geojson_path.stat().st_size / 1e6:.2f} MB)")
    return geojson_path


def claim_iso(oblasts: gpd.GeoDataFrame) -> dict[str, str]:
    found = {}
    if "shapeISO" not in oblasts.columns:
        return found
    for _, row in oblasts.iterrows():
        label = claim_label(row_blob(row))
        if label and isinstance(row["shapeISO"], str):
            found[label] = row["shapeISO"]
    return found


def epoch_ms(day: date) -> int:
    moment = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    return int(moment.timestamp() * 1000)


def read_geojson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def geolibre_layer(layer_id: str, name: str, path: Path, fill: str, opacity: float, time: bool) -> dict:
    layer = {
        "id": layer_id,
        "name": name,
        "type": "geojson",
        "visible": True,
        "opacity": 1,
        "style": {
            "fillColor": fill,
            "strokeColor": INK,
            "strokeWidth": 0.8,
            "fillOpacity": opacity,
        },
        "metadata": {},
        "source": {"type": "geojson"},
        "sourcePath": str(path.resolve()),
        "geojson": read_geojson(path),
    }
    if time:
        layer["metadata"]["timeBinding"] = {
            "property": "assess_date",
            "valueKind": "isoDate",
            "min": None,
            "max": None,
            "granularity": "day",
            "window": {"unit": "day", "before": 6, "after": 1},
        }
    return layer


def write_geolibre(layers: list[dict], dates: list[date]) -> None:
    start = epoch_ms(dates[0])
    end = epoch_ms(dates[-1])
    for layer in layers:
        binding = layer["metadata"].get("timeBinding")
        if binding:
            binding["min"] = start
            binding["max"] = end
    project = {
        "version": "0.2.0",
        "name": "Year 5: the claim and the hold",
        "mapView": {"center": [34.8, 48.0], "zoom": 5.4, "bearing": 0, "pitch": 0},
        "basemapStyleUrl": "https://tiles.openfreemap.org/styles/liberty",
        "basemapVisible": True,
        "basemapOpacity": 1,
        "layers": layers,
        "metadata": {
            "summary": (
                "Weekly assessed occupation, 24 February 2026 through the latest snapshot. "
                "The time slider uses a six-day lookback so each weekly polygon stays up "
                "until the next one. Areas were measured on Ukraine Albers."
            ),
            "source": "https://deepstatemap.live/",
        },
    }
    GEOLIBRE.write_text(json.dumps(project), encoding="utf-8")
    print(f"Wrote {GEOLIBRE.relative_to(ROOT)} ({GEOLIBRE.stat().st_size / 1e6:.2f} MB)")


def export_gis(ukraine, neighbors, claims, oblasts, dates, geoms, frames, rows) -> None:
    """EPSG:4326 layers for ArcGIS Pro and GeoLibre. Areas stay in the attribute table."""
    GIS.mkdir(parents=True, exist_ok=True)
    if GPKG.exists():
        GPKG.unlink()

    ukraine_wgs = to_wgs(ukraine)
    save_layer(
        "ukraine",
        gpd.GeoDataFrame(
            [{"name": "Ukraine", "area_km2": round(km2(ukraine), 1)}],
            geometry=[ukraine_wgs],
            crs=4326,
        ),
    )

    minx, miny, maxx, maxy = ukraine_wgs.bounds
    envelope = box(minx - 2.5, miny - 2.5, maxx + 2.5, maxy + 2.5)
    nearby = gpd.clip(neighbors, envelope)
    name_col = "ADMIN" if "ADMIN" in nearby.columns else "NAME"
    if not nearby.empty:
        save_layer(
            "neighbors",
            gpd.GeoDataFrame(
                {"name": nearby[name_col].astype(str).tolist()},
                geometry=list(nearby.geometry),
                crs=4326,
            ),
        )

    iso = claim_iso(oblasts)
    start_share = {row["name"]: row for row in oblast_rows(claims, geoms[0])}
    end_share = {row["name"]: row for row in rows}
    claim_records = []
    claim_geoms = []
    for name in CLAIM_ORDER:
        geom = claims.get(name)
        if geom is None:
            continue
        end = end_share[name]
        start = start_share[name]
        claim_records.append(
            {
                "name": name,
                "shape_iso": iso.get(name, ""),
                "area_km2": end["area_km2"],
                "held_start_km2": start["held_km2"],
                "held_end_km2": end["held_km2"],
                "held_start_pct": start["held_pct"],
                "held_end_pct": end["held_pct"],
                "area_note": AREA_NOTE,
            }
        )
        claim_geoms.append(to_wgs(geom))
    save_layer("claims", gpd.GeoDataFrame(claim_records, geometry=claim_geoms, crs=4326))

    occupied_records = []
    occupied_geoms = []
    for day, geom, frame in zip(dates, geoms, frames):
        occupied_records.append(
            {
                "assess_date": day.isoformat(),
                "held_km2": frame["held_km2"],
                "gained_km2": frame["gained_km2"],
                "retaken_km2": frame["retaken_km2"],
            }
        )
        occupied_geoms.append(to_wgs(geom))
    save_layer(
        "occupied",
        gpd.GeoDataFrame(occupied_records, geometry=occupied_geoms, crs=4326),
    )

    change_records = []
    change_geoms = []
    for frame in frames:
        for status, key in (("gained", "gained_geom"), ("retaken", "retaken_geom")):
            geom = to_wgs(frame[key])
            if geom is None:
                continue
            change_records.append(
                {
                    "assess_date": frame["date"],
                    "status": status,
                    "area_km2": frame["gained_km2"] if status == "gained" else frame["retaken_km2"],
                    "baseline": dates[0].isoformat(),
                }
            )
            change_geoms.append(geom)
    change_path = save_layer(
        "change",
        gpd.GeoDataFrame(change_records, geometry=change_geoms, crs=4326),
    )

    cities = gpd.GeoDataFrame(
        {
            "name": [item[0] for item in CITIES],
            "label": [item[3] for item in CITIES],
        },
        geometry=gpd.points_from_xy(
            [item[2] for item in CITIES],
            [item[1] for item in CITIES],
        ),
        crs=4326,
    )
    cities_path = save_layer("cities", cities)
    print(f"Wrote {GPKG.relative_to(ROOT)} ({GPKG.stat().st_size / 1e6:.2f} MB)")

    change_fc = read_geojson(change_path)
    gained_features = [feature for feature in change_fc["features"] if feature["properties"]["status"] == "gained"]
    retaken_features = [feature for feature in change_fc["features"] if feature["properties"]["status"] == "retaken"]
    gained_path = GIS / "gained.geojson"
    retaken_path = GIS / "retaken.geojson"
    gained_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": gained_features}),
        encoding="utf-8",
    )
    retaken_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": retaken_features}),
        encoding="utf-8",
    )

    layers = []
    if (GIS / "neighbors.geojson").exists():
        layers.append(geolibre_layer("neighbors", "Neighbors", GIS / "neighbors.geojson", "#E6E0D6", 1, False))
    layers.extend(
        [
            geolibre_layer("ukraine", "Ukraine", GIS / "ukraine.geojson", "#E4DDD2", 1, False),
            geolibre_layer("claims", "Claimed regions", GIS / "claims.geojson", CLAIM, 0.55, False),
            geolibre_layer("occupied", "Assessed occupation", GIS / "occupied.geojson", HELD, 0.85, True),
            geolibre_layer("retaken", "Passed back", retaken_path, RETAKEN, 0.95, True),
            geolibre_layer("gained", "Passed to Russian control", gained_path, GAIN, 0.95, True),
            geolibre_layer("cities", "Cities", cities_path, PAPER, 1, False),
        ]
    )
    write_geolibre(layers, dates)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    end = datetime.strptime(args.end, "%Y-%m-%d").date()
    if end < YEAR5_START:
        raise SystemExit("--end is before 24 February 2026.")

    RAW.mkdir(parents=True, exist_ok=True)
    ukraine_frame = fetch_geoboundaries("ADM0", RAW / "ukr-adm0.geojson", args.refresh)
    oblasts = fetch_geoboundaries("ADM1", RAW / "ukr-adm1.geojson", args.refresh)
    download(NE_URL, RAW / "ne_50m_admin_0_countries.geojson", args.refresh)
    neighbors = load_polygons(RAW / "ne_50m_admin_0_countries.geojson")
    name_col = "ADMIN" if "ADMIN" in neighbors.columns else "NAME"
    neighbors = neighbors[neighbors[name_col] != "Ukraine"]

    ukraine = gpd.GeoSeries(list(ukraine_frame.geometry), crs=4326).to_crs(ALBERS)
    ukraine_geom = polygons_only(shapely.union_all(list(ukraine.geometry)).buffer(0))

    claims = extract_claims(oblasts, ukraine_geom)
    print("Claimed regions: " + ", ".join(name for name in CLAIM_ORDER if name in claims))

    requested = weekly_dates(YEAR5_START, end)
    resolved: list[tuple[date, Path]] = []
    seen = set()
    for day in requested:
        actual, path = resolve_snapshot(day, args.refresh)
        if actual in seen:
            continue
        seen.add(actual)
        resolved.append((actual, path))
        if actual != day:
            print(f"Requested {day.isoformat()}, using {actual.isoformat()}")

    dates = [item[0] for item in resolved]
    geoms = []
    for actual, path in resolved:
        print(f"Preparing {actual.isoformat()}")
        geoms.append(working_occupied(path, ukraine_geom, args.refresh))

    frames = build_frames(dates, geoms, args.opening_m, args.min_km2)
    rows = oblast_rows(claims, geoms[-1])
    for row in rows:
        print(f"{row['name']}: {row['held_pct']:.1f}% of {row['area_km2']:,.0f} km²")

    meta = {
        "title": "The claim and the hold",
        "baseline": dates[0].isoformat(),
        "end": dates[-1].isoformat(),
        "opening_m": args.opening_m,
        "min_part_km2": args.min_km2,
        "work_tolerance_m": WORK_TOLERANCE_M,
        "projection": "Ukraine Albers, lat_1=46, lat_2=52, lat_0=48, lon_0=32, WGS84",
        "source": "DeepStateMap.live occupied-area assessments",
        "source_url": "https://deepstatemap.live/",
        "boundaries": "geoBoundaries UKR ADM0 and ADM1, CC BY 4.0",
    }
    write_frames(frames, claims, geoms[0], ukraine_geom, rows, meta)
    export_gis(ukraine_geom, neighbors, claims, oblasts, dates, geoms, frames, rows)
    if args.gis_only:
        return
    family = font_family()
    print(f"Sheet typeface: {family}")
    render_sheet(
        ukraine_geom,
        neighbors,
        claims,
        geoms[0],
        geoms[-1],
        frames,
        rows,
        args.opening_m,
        family,
    )


if __name__ == "__main__":
    main()
