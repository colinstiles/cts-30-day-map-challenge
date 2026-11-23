"""Flow map of Tennessee distilled-spirits exports.

Fiscal year 2025 is the latest complete year in the USDA ERS State
Trade by Country of Origin and Destination file. The sheet keeps only
distilled spirits. ERS names each commodity's five largest foreign
buyers. Smaller buyers are not in the table.

The lines start in Tennessee. Their width is the state's export value
to that country. The Census table does not split those dollars by
distillery, so the lines are not brand shares. Jack Daniel's and
George Dickel are marked because they are the two largest Tennessee
whiskey producers. Their coordinates are OpenStreetMap.

Two orthographic globes replace the azimuthal equidistant disk.
Australia sat on the rim of that disk and was stretched. The Atlantic
globe carries the European buyers. The second globe is centered on
Australia so the continent keeps its shape. Line width is stretched
across these five buyers, and each buyer has its own color, because
the dollar amounts are close and a single shared stroke could not be
traced. The strokes run onto each country and stay translucent, and
the borders are drawn over them.

Type is Playfair Display. Jack Daniel's marketing headlines use JD
Serif Bold, a proprietary brand face, so the sheet uses this open
serif in its place. The files are scripts/2026/fonts/.

Downloads are cached under data/2026/raw/, which is gitignored. The
buyer table is 2026/day-23/destinations.csv. The gallery sheet is
2026/day-23/day-23.png.

A corporate proxy may need the local Zscaler CA on SSL_CERT_FILE. Do
not disable TLS verification. ers.usda.gov may fail on the corporate
DNS; the cached CSV is then required.

Run from the repository root:

    python scripts/2026/build_day23_taste.py
    python scripts/2026/build_day23_taste.py --refresh
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib import font_manager
from matplotlib.patches import Circle, FancyBboxPatch
from shapely.geometry import Point
import _env  # noqa: F401  (loads .env for SSL_CERT_FILE / REQUESTS_CA_BUNDLE)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "2026" / "raw"
DAY = ROOT / "2026" / "day-23"
OUT_PNG = DAY / "day-23.png"
TABLE_PATH = DAY / "destinations.csv"
MAKERS_PATH = DAY / "makers.csv"
COUNTRIES_PATH = RAW / "ne_50m_admin_0_countries.geojson"
STATES_PATH = RAW / "ne_50m_admin_1_states_provinces.geojson"
TRADE_PATH = RAW / "day23_ers_exports_by_country.csv"
FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT_REGULAR = FONT_DIR / "PlayfairDisplay-Regular.ttf"
FONT_BOLD = FONT_DIR / "PlayfairDisplay-Bold.ttf"

COUNTRIES_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "v5.1.2/geojson/ne_50m_admin_0_countries.geojson"
)
STATES_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "v5.1.2/geojson/ne_50m_admin_1_states_provinces.geojson"
)
TRADE_URL = (
    "https://www.ers.usda.gov/media/5422/"
    "top-5-us-agricultural-export-commodities-by-state-fiscal-year.csv?v=75483"
)

# OpenStreetMap via Nominatim, 2026-11-23. Jack Daniel's is the visitor
# grounds on Lynchburg Highway. George Dickel is the works at Cascade Hollow.
MAKERS = (
    {
        "name": "Jack Daniel's",
        "place": "Lynchburg",
        "latitude": 35.2836001,
        "longitude": -86.3699474,
    },
    {
        "name": "George Dickel",
        "place": "Cascade Hollow",
        "latitude": 35.4382475,
        "longitude": -86.2446291,
    },
)
# Degrees left of the great circle, peaking halfway along the route.
# The Netherlands arc stays north of Britain. Poland stays south of Norway.
BOW_DEG = {
    "Poland": 14.0,
    "Netherlands": 8.0,
    "United Kingdom": 0.0,
    "France": -10.0,
    "Australia": 2.0,
}
# Orthographic centers. The Atlantic view holds Tennessee and Europe.
# Australia has its own globe so the continent is not pushed to a rim.
ATLANTIC = (46.0, -32.0)
AUSTRALIA_CENTER = (-25.5, 134.0)
# City centers, for the Tennessee locator.
CITIES = (
    ("Memphis", 35.1495, -90.0490),
    ("Nashville", 36.1627, -86.7816),
    ("Chattanooga", 35.0456, -85.3097),
    ("Knoxville", 35.9606, -83.9207),
)

CENTER_LAT = sum(maker["latitude"] for maker in MAKERS) / len(MAKERS)
CENTER_LON = sum(maker["longitude"] for maker in MAKERS) / len(MAKERS)
EARTH_RADIUS_M = 6_378_137.0
TN_CRS = "+proj=aea +lat_1=35.2 +lat_2=36.4 +lat_0=35.8 +lon_0=-86 +datum=WGS84 +units=m +no_defs"

FIG_W, FIG_H = 18.0, 11.0
DPI = 150

PAPER = "#141210"
INK = "#F6F1E4"
MUTED = "#C4B8A4"
OCEAN = "#1A242C"
LAND = "#3A3834"
EDGE = "#141210"
PANEL = "#221C16"
GOLD = "#E8C27A"
TN_FILL = "#6A4E32"
# One color per buyer so a line can be followed to its country.
FLOW_COLOR = {
    "Netherlands": "#F6E7C1",
    "Poland": "#E7A23A",
    "United Kingdom": "#E36A3A",
    "France": "#D7B56A",
    "Australia": "#6EB8B2",
}

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "cts-30-day-map-challenge day-23 educational map"


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = SESSION.get(url, timeout=(30, 180))
    response.raise_for_status()
    dest.write_bytes(response.content)


def load_countries() -> gpd.GeoDataFrame:
    if not COUNTRIES_PATH.is_file():
        download(COUNTRIES_URL, COUNTRIES_PATH)
    frame = gpd.read_file(COUNTRIES_PATH)
    frame = frame[frame["ADM0_A3"] != "ATA"].copy()
    frame["name"] = frame["NAME"]
    return frame[["name", "geometry"]].reset_index(drop=True)


def load_states() -> gpd.GeoDataFrame:
    if not STATES_PATH.is_file():
        download(STATES_URL, STATES_PATH)
    states = gpd.read_file(STATES_PATH)
    name_col = "name" if "name" in states.columns else "NAME"
    iso_col = "iso_a2" if "iso_a2" in states.columns else "ISO_A2"
    states = states[states[iso_col].eq("US")].copy()
    states["name"] = states[name_col]
    states = states[~states["name"].isin(["Alaska", "Hawaii"])]
    if not states["name"].eq("Tennessee").any():
        raise RuntimeError("Natural Earth has no Tennessee polygon")
    return states[["name", "geometry"]].reset_index(drop=True)


def load_spirits(refresh: bool) -> tuple[pd.DataFrame, float, int]:
    if refresh or not TRADE_PATH.is_file():
        download(TRADE_URL, TRADE_PATH)
    trade = pd.read_csv(TRADE_PATH)
    spirits = trade[
        trade["State"].eq("TN")
        & trade["Trade type"].eq("Exports")
        & trade["Commodity name"].eq("Distilled spirits")
    ].copy()
    year = _complete_year(spirits)
    annual = spirits[spirits["Fiscal year"].eq(year) & spirits["Fiscal quarter"].eq(0)]
    world = float(annual.loc[annual["Country"].eq("World"), "Dollar value"].iloc[0])
    buyers = annual[~annual["Country"].eq("World")][["Country", "Dollar value"]].copy()
    buyers = buyers.rename(columns={"Country": "country", "Dollar value": "dollars"})
    buyers = buyers.sort_values("dollars", ascending=False)
    return buyers, world, year


def _complete_year(spirits: pd.DataFrame) -> int:
    complete = []
    for year, sub in spirits.groupby("Fiscal year"):
        quarters = set(sub["Fiscal quarter"].astype(int))
        if {1, 2, 3, 4}.issubset(quarters):
            complete.append(int(year))
    if not complete:
        raise RuntimeError("ERS file has no complete Tennessee spirits year")
    return max(complete)


def main_land(countries: gpd.GeoDataFrame, names: set[str]) -> gpd.GeoDataFrame:
    """Largest polygon of each destination, so overseas pieces stay plain."""
    chosen = countries[countries["name"].isin(names)].copy()
    missing = names - set(chosen["name"])
    if missing:
        raise RuntimeError(f"Natural Earth has no match for {sorted(missing)}")
    parts = chosen.explode(index_parts=False).reset_index(drop=True)
    parts = parts[~parts.geometry.is_empty & parts.geometry.notna()].copy()
    parts["area"] = parts.to_crs("EPSG:6933").geometry.area
    keep = parts.groupby("name")["area"].idxmax()
    return parts.loc[keep, ["name", "geometry"]].reset_index(drop=True)


def _use_playfair() -> None:
    """Register Playfair Display before any text is drawn."""
    for path in (FONT_REGULAR, FONT_BOLD):
        if not path.is_file():
            raise RuntimeError(f"Missing typeface file {path}")
        font_manager.fontManager.addfont(str(path))
    plt.rcParams["font.family"] = "Playfair Display"


def _width(dollars: float, buyers: pd.DataFrame) -> float:
    """Stretch width across the five buyers. Their dollar amounts are close."""
    lo = float(buyers["dollars"].min())
    hi = float(buyers["dollars"].max())
    span = hi - lo
    t = 0.0 if span == 0 else (dollars - lo) / span
    return 1.3 + 5.2 * t


def _ortho(lat: float, lon: float) -> str:
    return f"+proj=ortho +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs"


def _vec(lat: float, lon: float) -> tuple[float, float, float]:
    phi, lam = math.radians(lat), math.radians(lon)
    return (math.cos(phi) * math.cos(lam), math.cos(phi) * math.sin(lam), math.sin(phi))


def _latlon(x: float, y: float, z: float) -> tuple[float, float]:
    lat = math.degrees(math.asin(max(-1.0, min(1.0, z))))
    lon = math.degrees(math.atan2(y, x))
    return lat, lon


def _norm(v: tuple[float, float, float]) -> tuple[float, float, float]:
    mag = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / mag for c in v)


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _route(lat1: float, lon1: float, lat2: float, lon2: float, bow_deg: float) -> list[tuple[float, float]]:
    """Great circle from (lat1, lon1) to (lat2, lon2), bowed left by bow_deg."""
    start, end = _vec(lat1, lon1), _vec(lat2, lon2)
    normal = _norm(_cross(start, end))
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(start, end, strict=True))))
    omega = math.acos(dot)
    points = []
    steps = 80
    for step in range(steps + 1):
        t = step / steps
        if omega < 1e-8:
            vector = start
        else:
            scale = math.sin(omega)
            vector = tuple(
                (math.sin((1 - t) * omega) * a + math.sin(t * omega) * b) / scale
                for a, b in zip(start, end, strict=True)
            )
        amp = math.sin(math.pi * t) * math.radians(bow_deg)
        bowed = tuple(
            math.cos(amp) * a + math.sin(amp) * b for a, b in zip(vector, normal, strict=True)
        )
        points.append(_latlon(*_norm(bowed)))
    return points


def _angular_degrees(lat: pd.Series, lon: pd.Series, lat0: float, lon0: float) -> pd.Series:
    lat0_r = math.radians(lat0)
    lon0_r = math.radians(lon0)
    lat_r = lat.map(math.radians)
    lon_r = lon.map(math.radians)
    cosine = (
        math.sin(lat0_r) * lat_r.map(math.sin)
        + math.cos(lat0_r) * lat_r.map(math.cos) * (lon_r - lon0_r).map(math.cos)
    ).clip(-1, 1)
    return cosine.map(math.acos).map(math.degrees)


def _visible_land(frame: gpd.GeoDataFrame, lat0: float, lon0: float, crs: str) -> gpd.GeoDataFrame:
    """Keep pieces well inside the limb, then project. Orthographic breaks past it."""
    parts = frame.explode(index_parts=False).reset_index(drop=True)
    parts = parts[~parts.geometry.is_empty & parts.geometry.notna()].copy()
    point = parts.geometry.representative_point()
    degrees = _angular_degrees(point.y, point.x, lat0, lon0)
    kept = parts.loc[degrees < 78].copy()
    kept["geometry"] = kept.geometry.make_valid()
    projected = kept.to_crs(crs)
    disk = Point(0, 0).buffer(EARTH_RADIUS_M * 0.995)
    pieces = []
    for geom in projected.geometry:
        try:
            piece = geom.intersection(disk)
        except Exception:
            continue
        if not piece.is_empty:
            pieces.append(piece)
    if not pieces:
        return gpd.GeoDataFrame(geometry=[], crs=crs)
    return gpd.GeoDataFrame(geometry=pieces, crs=crs)


def _project_route(lat1: float, lon1: float, lat2: float, lon2: float, bow: float, crs: str) -> list[tuple[float, float]]:
    route = _route(lat1, lon1, lat2, lon2, bow)
    series = gpd.GeoSeries([Point(lon, lat) for lat, lon in route], crs="EPSG:4326").to_crs(crs)
    limit = EARTH_RADIUS_M * 0.97
    return [
        (float(x), float(y))
        for x, y in zip(series.x, series.y, strict=True)
        if math.hypot(float(x), float(y)) < limit
    ]


def _draw_globe(
    ax,
    countries: gpd.GeoDataFrame,
    targets: gpd.GeoDataFrame,
    buyers: pd.DataFrame,
    center: tuple[float, float],
    countries_on_globe: set[str],
    label_origin: bool,
) -> None:
    lat0, lon0 = center
    crs = _ortho(lat0, lon0)
    land = _visible_land(countries, lat0, lon0, crs)
    chosen = buyers[buyers["country"].isin(countries_on_globe)]
    highlights = targets[targets["name"].isin(countries_on_globe)].merge(
        chosen, left_on="name", right_on="country"
    )
    ax.set_facecolor(PAPER)
    ax.add_patch(
        Circle((0, 0), EARTH_RADIUS_M, facecolor=OCEAN, edgecolor="#2C3840", linewidth=1.1, zorder=0)
    )
    if not land.empty:
        land.plot(ax=ax, color=LAND, edgecolor=EDGE, linewidth=0.28, zorder=1)
    painted_by_country = {}
    for country, geom in zip(highlights["name"], highlights.geometry, strict=True):
        painted = _visible_land(
            gpd.GeoDataFrame({"name": [country]}, geometry=[geom], crs="EPSG:4326"),
            lat0,
            lon0,
            crs,
        )
        if painted.empty:
            continue
        painted_by_country[country] = painted
        painted.plot(
            ax=ax,
            color=FLOW_COLOR[country],
            edgecolor="none",
            linewidth=0,
            zorder=2,
            alpha=0.36,
        )
    ordered = chosen.sort_values("dollars", ascending=False)
    indexed = targets.set_index("name")
    for country, dollars in ordered.itertuples(index=False):
        end = indexed.loc[country].geometry.representative_point()
        points = _project_route(
            CENTER_LAT,
            CENTER_LON,
            float(end.y),
            float(end.x),
            BOW_DEG[country],
            crs,
        )
        if len(points) < 2:
            continue
        xs, ys = zip(*points, strict=True)
        width = _width(float(dollars), buyers)
        # A wide translucent stroke keeps the width, and a narrow solid
        # core stays visible after the line crosses onto the country.
        ax.plot(
            xs,
            ys,
            color=FLOW_COLOR[country],
            lw=width,
            alpha=0.38,
            solid_capstyle="round",
            solid_joinstyle="round",
            zorder=3,
        )
        ax.plot(
            xs,
            ys,
            color=FLOW_COLOR[country],
            lw=max(0.9, width * 0.38),
            alpha=1.0,
            solid_capstyle="round",
            solid_joinstyle="round",
            zorder=4,
        )
    # Borders go on last, in a lighter ink, so a stroke cannot hide a coast.
    if not land.empty:
        land.boundary.plot(ax=ax, color="#B7A99A", linewidth=0.45, zorder=5)
    if label_origin:
        origin = gpd.GeoSeries([Point(CENTER_LON, CENTER_LAT)], crs="EPSG:4326").to_crs(crs)
        ox, oy = float(origin.x.iloc[0]), float(origin.y.iloc[0])
        ax.scatter([ox], [oy], s=42, color=GOLD, zorder=6, linewidths=0)
        ax.annotate(
            "Tennessee",
            (ox, oy),
            xytext=(0, -11),
            textcoords="offset points",
            color=INK,
            fontsize=9,
            ha="center",
            va="top",
            zorder=7,
        )
    limit = EARTH_RADIUS_M * 1.06
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_aspect("equal")
    ax.set_axis_off()


def _draw_inset(fig, states: gpd.GeoDataFrame) -> None:
    """Tennessee and its neighbors, with the two distilleries and the large cities."""
    inset = fig.add_axes((0.545, 0.305, 0.43, 0.25))
    inset.set_facecolor(OCEAN)
    projected = states.to_crs(TN_CRS)
    tennessee = projected[projected["name"].eq("Tennessee")]
    neighbors = projected[~projected["name"].eq("Tennessee")]
    neighbors.plot(ax=inset, color="#4E4A44", edgecolor="#6A6560", linewidth=0.5, zorder=1)
    tennessee.plot(ax=inset, color=TN_FILL, edgecolor=GOLD, linewidth=1.05, zorder=2)

    cities = gpd.GeoSeries(
        [Point(lon, lat) for _name, lat, lon in CITIES], crs="EPSG:4326"
    ).to_crs(TN_CRS)
    inset.scatter(cities.x, cities.y, s=10, color=MUTED, zorder=3, linewidths=0)
    city_offset = {
        "Memphis": (5, 0),
        "Nashville": (0, 7),
        "Chattanooga": (0, -8),
        "Knoxville": (0, 7),
    }
    city_ha = {"Memphis": "left", "Nashville": "center", "Chattanooga": "center", "Knoxville": "center"}
    for (name, _lat, _lon), point in zip(CITIES, cities, strict=True):
        dx, dy = city_offset[name]
        inset.annotate(
            name,
            (point.x, point.y),
            xytext=(dx, dy),
            textcoords="offset points",
            color=MUTED,
            fontsize=7,
            ha=city_ha[name],
            va="center",
            zorder=4,
        )

    makers = gpd.GeoSeries(
        [Point(maker["longitude"], maker["latitude"]) for maker in MAKERS], crs="EPSG:4326"
    ).to_crs(TN_CRS)
    inset.scatter(makers.x, makers.y, s=36, color=GOLD, zorder=5, linewidths=0)
    # The stills are about 30 km apart, so the names sit on opposite sides.
    maker_offset = {"Jack Daniel's": (-6, -7), "George Dickel": (7, 8)}
    maker_align = {"Jack Daniel's": ("right", "top"), "George Dickel": ("left", "bottom")}
    for maker, point in zip(MAKERS, makers, strict=True):
        ha, va = maker_align[maker["name"]]
        inset.annotate(
            maker["name"],
            (point.x, point.y),
            xytext=maker_offset[maker["name"]],
            textcoords="offset points",
            color=INK,
            fontsize=7.5,
            ha=ha,
            va=va,
            zorder=6,
        )

    bounds = tennessee.total_bounds
    pad_x = (bounds[2] - bounds[0]) * 0.05
    pad_y = (bounds[3] - bounds[1]) * 0.14
    inset.set_xlim(bounds[0] - pad_x, bounds[2] + pad_x)
    inset.set_ylim(bounds[1] - pad_y, bounds[3] + pad_y)
    inset.set_axis_off()
    inset.set_aspect("equal")


def _text_width_in(text: str, size: float, weight: str) -> float:
    """Width of a Playfair string in inches."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath

    prop = FontProperties(family="Playfair Display", size=size, weight=weight)
    return TextPath((0, 0), text, prop=prop).get_extents().width / 72


def _draw_panel(fig, buyers: pd.DataFrame, named: float, world: float, year: int) -> None:
    """Buyer key, sized to its text and set in the lower right."""
    title = f"Buyers, fiscal year {year}"
    share = named / world if world else 0
    footer = (
        f"Top 5 buyers are {named / 1e6:.0f} million out of a total of "
        f"{world / 1e6:.0f} million, {share:.0%}."
    )
    rows = []
    for country, dollars in buyers.itertuples(index=False):
        millions = float(dollars) / 1_000_000
        amount = f"${millions:.0f}M" if millions >= 100 else f"${millions:.1f}M"
        rows.append((country, float(dollars), amount))

    pad_x = 0.16
    pad_top = 0.10
    pad_bottom = 0.10
    title_size = 11
    row_size = 9
    footer_size = 10
    title_block = 0.20
    title_buffer = 0.28
    row_pitch = 0.22
    footer_gap = 0.12
    footer_block = 0.16
    swatch = 0.48
    col_gap = 0.14

    title_w = _text_width_in(title, title_size, "bold")
    footer_w = _text_width_in(footer, footer_size, "regular")
    country_w = max(_text_width_in(country, row_size, "regular") for country, _dollars, _amount in rows)
    amount_w = max(_text_width_in(amount, row_size, "regular") for _country, _dollars, amount in rows)
    rows_w = swatch + col_gap + country_w + col_gap + amount_w
    box_w = max(title_w, footer_w, rows_w) + 2 * pad_x
    box_h = (
        pad_top
        + title_block
        + title_buffer
        + row_pitch * (len(rows) - 1)
        + footer_gap
        + footer_block
        + pad_bottom
    )

    right_margin = 0.22
    bottom_margin = 0.16
    panel = fig.add_axes(
        (
            1 - (right_margin + box_w) / FIG_W,
            bottom_margin / FIG_H,
            box_w / FIG_W,
            box_h / FIG_H,
        )
    )
    panel.set_xlim(0, box_w)
    panel.set_ylim(0, box_h)
    panel.set_axis_off()
    panel.add_patch(
        FancyBboxPatch(
            (0.0, 0.0),
            1.0,
            1.0,
            boxstyle="round,pad=0.008,rounding_size=0.03",
            facecolor=PANEL,
            edgecolor="none",
            transform=panel.transAxes,
            clip_on=False,
        )
    )
    y = box_h - pad_top
    panel.text(pad_x, y, title, fontsize=title_size, color=INK, fontweight="bold", va="top")
    y -= title_block + title_buffer
    for country, dollars, amount in rows:
        width = _width(dollars, buyers)
        panel.plot(
            [pad_x, pad_x + swatch],
            [y, y],
            color=FLOW_COLOR[country],
            lw=width,
            solid_capstyle="round",
        )
        panel.text(pad_x + swatch + col_gap, y, country, fontsize=row_size, color=INK, va="center")
        panel.text(box_w - pad_x, y, amount, fontsize=row_size, color=MUTED, ha="right", va="center")
        y -= row_pitch
    panel.text(pad_x, pad_bottom, footer, fontsize=footer_size, color=MUTED, va="bottom")


def render(
    countries: gpd.GeoDataFrame,
    states: gpd.GeoDataFrame,
    buyers: pd.DataFrame,
    world: float,
    year: int,
) -> None:
    _use_playfair()
    targets = main_land(countries, set(buyers["country"]))
    named = float(buyers["dollars"].sum())
    europe = {"Netherlands", "Poland", "United Kingdom", "France"}

    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI, facecolor=PAPER)
    # Both globes are square in inches so the orthographic disk stays a circle.
    # The Atlantic globe sits below the title. Australia's globe is centered
    # on the continent.
    atlantic = fig.add_axes((0.025, 0.04, 8.6 / FIG_W, 8.6 / FIG_H))
    australia = fig.add_axes((0.655, 0.58, 3.6 / FIG_W, 3.6 / FIG_H))
    _draw_globe(atlantic, countries, targets, buyers, ATLANTIC, europe, label_origin=True)
    _draw_globe(australia, countries, targets, buyers, AUSTRALIA_CENTER, {"Australia"}, label_origin=False)
    _draw_inset(fig, states)
    _draw_panel(fig, buyers, named, world, year)

    fig.text(
        0.028,
        0.955,
        "Taste of Tennessee",
        fontsize=30,
        color=INK,
        fontweight="bold",
        ha="left",
        va="center",
    )
    fig.text(
        0.028,
        0.908,
        "Exports of distilled spirits from Tennessee",
        fontsize=14,
        color=MUTED,
        ha="left",
        va="center",
    )
    # Inset axes are (0.545, 0.305, 0.43, 0.25). Center the caption on that box.
    fig.text(
        0.545 + 0.43 / 2,
        0.278,
        "Jack Daniel's, Lynchburg  ·  George Dickel, Cascade Hollow",
        fontsize=10,
        color=INK,
        ha="center",
        va="bottom",
    )
    fig.text(
        0.015,
        0.018,
        "Sources: USDA ERS, Census origin of movement, Natural Earth; OpenStreetMap. "
        "Created by Colin T. Stiles.",
        fontsize=8,
        color=MUTED,
        ha="left",
        va="bottom",
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    print(f"wrote {OUT_PNG.relative_to(ROOT)}", flush=True)


def write_tables(buyers: pd.DataFrame) -> None:
    DAY.mkdir(parents=True, exist_ok=True)
    buyers.to_csv(TABLE_PATH, index=False)
    pd.DataFrame(MAKERS).to_csv(MAKERS_PATH, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Ignore the cached ERS export file.")
    args = parser.parse_args()
    buyers, world, year = load_spirits(args.refresh)
    write_tables(buyers)
    countries = load_countries()
    states = load_states()
    print(
        f"fiscal year {year} buyers {len(buyers)} "
        f"named {buyers['dollars'].sum() / 1e6:.0f} million "
        f"of {world / 1e6:.0f} million",
        flush=True,
    )
    render(countries, states, buyers, world, year)


if __name__ == "__main__":
    main()
