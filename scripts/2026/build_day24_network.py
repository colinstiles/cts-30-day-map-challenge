"""Network of the largest published crypto corridors.

BIS Working Paper 1265 prints the five largest directional country
pairs for Bitcoin, Ether, USDC, and Tether from Q3 2023 through Q2
2024 (Table 1), and the five largest sending countries in each asset
(Table 2). The bilateral matrix is not public. The sheet draws those
twenty corridors and nothing else.

Line width is billion dollars. A circle's area is the sum of the
corridors drawn leaving that country, not the country's full
cross-border total. Türkiye, Russia, Vietnam, and Korea send much
more than the thickest single link shows. Germany is on the sheet
because of one Bitcoin corridor and is not a top-five sender.

Dots are drawing points on each country so the links stay readable.
They are not cities and not exchange domiciles. The paper assigns
exchange-to-exchange flows to countries by app usage (Bitcoin, Iknaio
and Sensor Tower) or by web traffic (Ether, USDC, and Tether,
Chainalysis).

The base map is Natural Earth 1:50m, cached under data/2026/raw/,
which is gitignored. The transcribed tables are
2026/day-24/corridors.csv and 2026/day-24/senders.csv. The gallery
sheet is 2026/day-24/day-24.png. The interactive page reads a
simplified Natural Earth 1:110m outline at 2026/day-24/world.geojson.

A corporate proxy may need the local Zscaler CA on SSL_CERT_FILE. Do
not disable TLS verification.

Run from the repository root:

    python scripts/2026/build_day24_network.py
    python scripts/2026/build_day24_network.py --refresh
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib import patheffects
from matplotlib.patches import Circle, FancyBboxPatch, Polygon
from shapely.geometry import Point
import _env  # noqa: F401  (loads .env for SSL_CERT_FILE / REQUESTS_CA_BUNDLE)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "2026" / "raw"
DAY = ROOT / "2026" / "day-24"
OUT_PNG = DAY / "day-24.png"
CORRIDORS_PATH = DAY / "corridors.csv"
SENDERS_PATH = DAY / "senders.csv"
WORLD_PATH = DAY / "world.geojson"
COUNTRIES_PATH = RAW / "ne_50m_admin_0_countries.geojson"
COUNTRIES_110 = RAW / "ne_110m_admin_0_countries.geojson"
COUNTRIES_110_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "v5.1.2/geojson/ne_110m_admin_0_countries.geojson"
)
COUNTRIES_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "v5.1.2/geojson/ne_50m_admin_0_countries.geojson"
)

# Table 1, Q3 2023–Q2 2024. Flows are US$ billions. Shares are the
# paper's published percent of that asset's cross-border total.
# (origin iso2, dest iso2, origin, dest, asset, billion, share)
CORRIDORS = (
    ("GB", "US", "United Kingdom", "United States", "BTC", 9.89, 1.7),
    ("US", "GB", "United States", "United Kingdom", "BTC", 9.28, 1.6),
    ("CA", "US", "Canada", "United States", "BTC", 4.94, 0.8),
    ("DE", "US", "Germany", "United States", "BTC", 4.89, 0.8),
    ("US", "CA", "United States", "Canada", "BTC", 4.87, 0.8),
    ("US", "GB", "United States", "United Kingdom", "ETH", 2.23, 1.0),
    ("GB", "US", "United Kingdom", "United States", "ETH", 2.09, 0.9),
    ("US", "ID", "United States", "Indonesia", "ETH", 1.30, 0.6),
    ("US", "TR", "United States", "Türkiye", "ETH", 1.27, 0.6),
    ("RU", "US", "Russia", "United States", "ETH", 1.26, 0.6),
    ("US", "GB", "United States", "United Kingdom", "USDC", 6.33, 1.9),
    ("GB", "US", "United Kingdom", "United States", "USDC", 6.23, 1.8),
    ("IN", "US", "India", "United States", "USDC", 4.21, 1.2),
    ("US", "IN", "United States", "India", "USDC", 4.18, 1.2),
    ("ID", "US", "Indonesia", "United States", "USDC", 3.85, 1.1),
    ("US", "TR", "United States", "Türkiye", "USDT", 5.89, 0.5),
    ("US", "RU", "United States", "Russia", "USDT", 5.47, 0.5),
    ("TR", "US", "Türkiye", "United States", "USDT", 5.24, 0.5),
    ("RU", "US", "Russia", "United States", "USDT", 5.00, 0.4),
    ("GB", "US", "United Kingdom", "United States", "USDT", 4.79, 0.4),
)
# Table 1 row "All".
TOTALS = {"BTC": 592.99, "ETH": 225.54, "USDC": 338.14, "USDT": 1158.56}
# Table 3, top-5 concentration, 2023–24, percent of all flows.
TOP5_SHARE = {"BTC": 5.7, "ETH": 3.6, "USDC": 7.3, "USDT": 2.3}
# Table 2, flows sent, US$ billions and percent. Ordered as printed.
SENDERS = (
    ("US", "United States", "BTC", 102.3, 17.3),
    ("GB", "United Kingdom", "BTC", 29.6, 5.0),
    ("RU", "Russia", "BTC", 23.1, 3.9),
    ("TR", "Türkiye", "BTC", 21.3, 3.6),
    ("KR", "Korea", "BTC", 19.2, 3.2),
    ("US", "United States", "ETH", 30.4, 13.5),
    ("GB", "United Kingdom", "ETH", 10.8, 4.8),
    ("TR", "Türkiye", "ETH", 9.9, 4.4),
    ("RU", "Russia", "ETH", 9.7, 4.3),
    ("ID", "Indonesia", "ETH", 8.1, 3.6),
    ("US", "United States", "USDC", 82.3, 24.3),
    ("GB", "United Kingdom", "USDC", 18.5, 5.5),
    ("IN", "India", "USDC", 13.2, 3.9),
    ("ID", "Indonesia", "USDC", 11.8, 3.5),
    ("CA", "Canada", "USDC", 9.9, 2.9),
    ("US", "United States", "USDT", 98.1, 8.5),
    ("TR", "Türkiye", "USDT", 67.9, 5.9),
    ("RU", "Russia", "USDT", 66.1, 5.7),
    ("VN", "Vietnam", "USDT", 44.1, 3.8),
    ("GB", "United Kingdom", "USDT", 42.9, 3.7),
)

# Drawing points, not cities. The United Kingdom sits in northern
# Scotland and Germany in Bavaria so the two circles do not overlap.
# Western Indonesia keeps that node off New Guinea. European Russia
# keeps that node with the other Eurasian hubs.
ANCHORS = {
    "US": (-97.5, 38.5),
    "CA": (-100.0, 54.0),
    "GB": (-4.5, 57.6),
    "DE": (11.5, 48.6),
    "TR": (35.0, 39.0),
    "RU": (38.0, 56.5),
    "IN": (78.8, 22.8),
    "ID": (112.0, -2.2),
}
# Signed bend as a fraction of the chord. Positive is north of an
# eastbound route. Chosen so a corridor misses every other circle.
PAIR_BOW = {
    frozenset({"US", "CA"}): 0.40,
    frozenset({"US", "RU"}): 0.14,
    frozenset({"US", "GB"}): 0.08,
    frozenset({"US", "DE"}): -0.36,
    frozenset({"US", "TR"}): -0.48,
    frozenset({"US", "IN"}): -0.54,
    frozenset({"US", "ID"}): 0.05,
}
ISO3 = {
    "US": "USA",
    "CA": "CAN",
    "GB": "GBR",
    "DE": "DEU",
    "TR": "TUR",
    "RU": "RUS",
    "IN": "IND",
    "ID": "IDN",
}
# Offset is screen points from the dot. Leaders run back to the circle.
LABELS = {
    "US": ("United States", (-8, -22), "center", "top"),
    "CA": ("Canada", (-6, 16), "center", "bottom"),
    "GB": ("United Kingdom", (-68, -42), "center", "center"),
    "DE": ("Germany", (22, -26), "left", "top"),
    "TR": ("Türkiye", (18, -14), "left", "top"),
    "RU": ("Russia", (16, 16), "left", "bottom"),
    "IN": ("India", (4, -20), "center", "top"),
    "ID": ("Indonesia", (14, -8), "left", "top"),
}
ASSET_ORDER = ("BTC", "ETH", "USDC", "USDT")
ASSET_STYLE = {
    "BTC": ("Bitcoin", "#F0C14D"),
    "ETH": ("Ether", "#C4B5FD"),
    "USDC": ("USDC", "#7DD3FC"),
    "USDT": ("Tether", "#5EE0A0"),
}
HALO = "#141210"
LANE_METERS = 460_000.0

CENTER_LAT = 44.0
CENTER_LON = -12.0
EARTH_RADIUS_M = 6_378_137.0
HORIZON_DEGREES = 128.0
HORIZON = EARTH_RADIUS_M * math.radians(HORIZON_DEGREES)
FLOW_CRS = (
    f"+proj=aeqd +lat_0={CENTER_LAT:.1f} +lon_0={CENTER_LON:.1f} "
    "+datum=WGS84 +units=m +no_defs"
)

FIG_W, FIG_H = 16.0, 10.0
DPI = 160
# Axes width in points: 0.50 of a 16-inch figure, times 72.
METERS_PER_PT = (2 * HORIZON * 1.04) / (0.50 * FIG_W * 72)

PAPER = "#141210"
INK = "#F6F1E4"
MUTED = "#C4B8A4"
OCEAN = "#1A242C"
LAND = "#3A3834"
HUB_LAND = "#6E5840"
EDGE = "#141210"
PANEL = "#221C16"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "cts-30-day-map-challenge day-24 educational map"
LABEL_FX = [patheffects.withStroke(linewidth=3.2, foreground=PAPER)]


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = SESSION.get(url, timeout=(30, 180))
    response.raise_for_status()
    dest.write_bytes(response.content)


def check_tables() -> None:
    """Reject a transcription that no longer matches the printed shares."""
    frame = pd.DataFrame(
        CORRIDORS,
        columns=["origin", "dest", "origin_name", "dest_name", "asset", "billion", "share"],
    )
    for asset, total in TOTALS.items():
        rows = frame[frame["asset"].eq(asset)]
        if len(rows) != 5:
            raise RuntimeError(f"{asset} does not have five corridors")
        computed = float(rows["billion"].sum()) / total * 100
        if abs(computed - TOP5_SHARE[asset]) > 0.15:
            raise RuntimeError(f"{asset} top-five share {computed:.2f} != {TOP5_SHARE[asset]}")
        for billion, share in zip(rows["billion"], rows["share"], strict=True):
            printed = float(billion) / total * 100
            if abs(printed - float(share)) > 0.08:
                raise RuntimeError(f"{asset} share {share} does not match {billion}")
    senders = pd.DataFrame(
        SENDERS, columns=["iso2", "name", "asset", "sent", "share"]
    )
    for asset, total in TOTALS.items():
        rows = senders[senders["asset"].eq(asset)]
        if len(rows) != 5:
            raise RuntimeError(f"{asset} does not have five senders")
        for sent, share in zip(rows["sent"], rows["share"], strict=True):
            printed = float(sent) / total * 100
            if abs(printed - float(share)) > 0.08:
                raise RuntimeError(f"{asset} sender share {share} does not match {sent}")


def load_countries(refresh: bool) -> gpd.GeoDataFrame:
    if refresh or not COUNTRIES_PATH.is_file():
        download(COUNTRIES_URL, COUNTRIES_PATH)
    frame = gpd.read_file(COUNTRIES_PATH)
    frame = frame[frame["ADM0_A3"] != "ATA"].copy()
    frame["iso3"] = frame["ADM0_A3"]
    return frame[["iso3", "geometry"]].reset_index(drop=True)


def write_tables() -> None:
    DAY.mkdir(parents=True, exist_ok=True)
    corridors = pd.DataFrame(
        CORRIDORS,
        columns=[
            "origin_iso2",
            "dest_iso2",
            "origin",
            "dest",
            "asset",
            "billion_usd",
            "share_percent",
        ],
    )
    corridors.insert(0, "period", "2023-Q3 to 2024-Q2")
    corridors.to_csv(CORRIDORS_PATH, index=False)
    senders = pd.DataFrame(
        SENDERS,
        columns=["iso2", "name", "asset", "sent_billion_usd", "share_percent"],
    )
    senders.insert(0, "period", "2023-Q3 to 2024-Q2")
    senders.to_csv(SENDERS_PATH, index=False)


def _round_coords(value: object) -> object:
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, list):
        return [_round_coords(item) for item in value]
    if isinstance(value, dict):
        return {key: _round_coords(item) for key, item in value.items()}
    return value


def write_world(refresh: bool) -> None:
    """Simplified country outlines for the interactive page."""
    if refresh or not COUNTRIES_110.is_file():
        download(COUNTRIES_110_URL, COUNTRIES_110)
    frame = gpd.read_file(COUNTRIES_110)
    frame = frame[frame["ADM0_A3"] != "ATA"][["ADM0_A3", "NAME", "geometry"]].copy()
    frame["geometry"] = frame.geometry.make_valid().simplify(0.35, preserve_topology=True)
    frame = frame[~frame.geometry.is_empty & frame.geometry.notna()]
    frame = frame.rename(columns={"ADM0_A3": "iso3", "NAME": "name"})
    payload = _round_coords(json.loads(frame.to_json()))
    DAY.mkdir(parents=True, exist_ok=True)
    WORLD_PATH.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {WORLD_PATH.relative_to(ROOT)}", flush=True)


def _near_center(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Drop pieces near the antipode. The azimuthal projection breaks there."""
    parts = frame.explode(index_parts=False).reset_index(drop=True)
    parts = parts[~parts.geometry.is_empty & parts.geometry.notna()].copy()
    point = parts.geometry.representative_point()
    lat0 = math.radians(CENTER_LAT)
    lon0 = math.radians(CENTER_LON)
    lat = point.y.map(math.radians)
    lon = point.x.map(math.radians)
    delta_lon = lon - lon0
    cosine = (
        math.sin(lat0) * lat.map(math.sin)
        + math.cos(lat0) * lat.map(math.cos) * delta_lon.map(math.cos)
    ).clip(-1, 1)
    degrees = cosine.map(math.acos).map(math.degrees)
    kept = parts.loc[degrees < HORIZON_DEGREES + 8].copy()
    kept["geometry"] = kept.geometry.make_valid()
    return kept


def _project_anchors() -> dict[str, tuple[float, float]]:
    frame = gpd.GeoDataFrame(
        {"iso2": list(ANCHORS)},
        geometry=[Point(lon, lat) for lon, lat in ANCHORS.values()],
        crs="EPSG:4326",
    ).to_crs(FLOW_CRS)
    points = {}
    for iso2, geom in zip(frame["iso2"], frame.geometry, strict=True):
        radius = math.hypot(geom.x, geom.y)
        if radius > HORIZON * 0.93:
            raise RuntimeError(f"{iso2} anchor falls outside the map")
        points[iso2] = (float(geom.x), float(geom.y))
    return points


def _width(billion: float) -> float:
    largest = max(row[5] for row in CORRIDORS)
    return 1.15 + 7.4 * (billion / largest)


def _north_perp(
    start: tuple[float, float], end: tuple[float, float]
) -> tuple[tuple[float, float], float, float]:
    """Unit vector north of the chord, the chord length, and a direction sign.

    The sign is +1 when traveling west to east, so a positive lane stays
    on the north side of an eastbound route and the return stays south.
    """
    sx, sy = start
    ex, ey = end
    if sx <= ex:
        dx, dy = ex - sx, ey - sy
        sign = 1.0
    else:
        dx, dy = sx - ex, sy - ey
        sign = -1.0
    length = math.hypot(dx, dy) or 1.0
    return (-dy / length, dx / length), length, sign


def _curve(
    start: tuple[float, float], end: tuple[float, float], bow: float, lane: float
) -> list[tuple[float, float]]:
    sx, sy = start
    ex, ey = end
    (px, py), length, sign = _north_perp(start, end)
    offset = bow * length + lane * sign
    cx, cy = (sx + ex) / 2 + px * offset, (sy + ey) / 2 + py * offset
    points = []
    steps = 56
    for step in range(steps + 1):
        t = step / steps
        omt = 1 - t
        x = omt * omt * sx + 2 * omt * t * cx + t * t * ex
        y = omt * omt * sy + 2 * omt * t * cy + t * t * ey
        points.append((x, y))
    return points


def _trim(
    points: list[tuple[float, float]], end: tuple[float, float], gap: float
) -> list[tuple[float, float]]:
    start = points[0]
    length = math.hypot(end[0] - start[0], end[1] - start[1]) or 1.0
    # A short hop, such as Canada–United States, must keep a visible arc.
    gap = min(gap, length * 0.38)
    kept = []
    for point in points:
        if math.hypot(point[0] - end[0], point[1] - end[1]) < gap:
            break
        kept.append(point)
    if len(kept) >= 8:
        return kept
    return points[: max(8, len(points) // 3)]


def _marker_area(billion: float, largest: float) -> float:
    # Scatter area is proportional to the outbound corridors. The largest
    # radius stays near 15 points so a hub does not cover its neighbor.
    radius_pt = 14.8 * math.sqrt(billion / largest)
    return math.pi * radius_pt * radius_pt


def _gap(billion: float, largest: float) -> float:
    radius_pt = math.sqrt(_marker_area(billion, largest) / math.pi)
    return radius_pt * METERS_PER_PT + 160_000


def _lanes(assets: list[str]) -> dict[str, float]:
    present = [asset for asset in ASSET_ORDER if asset in assets]
    mid = (len(present) - 1) / 2
    return {asset: (index - mid) * LANE_METERS for index, asset in enumerate(present)}


def _arrow(points: list[tuple[float, float]], billion: float) -> list[tuple[float, float]]:
    x2, y2 = points[-1]
    x1, y1 = points[-6]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1.0
    ux, uy = dx / norm, dy / norm
    px, py = -uy, ux
    length = 260_000 + _width(billion) * 22_000
    width = length * 0.42
    tip = (x2 + ux * length * 0.2, y2 + uy * length * 0.2)
    left = (x2 - ux * length + px * width, y2 - uy * length + py * width)
    right = (x2 - ux * length - px * width, y2 - uy * length - py * width)
    return [tip, left, right]


def _draw_world(ax, countries: gpd.GeoDataFrame, points: dict[str, tuple[float, float]]) -> None:
    horizon = Point(0, 0).buffer(HORIZON)
    land = _near_center(countries).to_crs(FLOW_CRS)
    land["geometry"] = land.geometry.make_valid()
    land = gpd.clip(land, horizon)
    hub_iso = {ISO3[iso2] for iso2 in ANCHORS}
    hubs = land[land["iso3"].isin(hub_iso)]

    ax.set_facecolor(PAPER)
    ax.add_patch(Circle((0, 0), HORIZON, facecolor=OCEAN, edgecolor="none", zorder=0))
    land.plot(ax=ax, color=LAND, edgecolor=EDGE, linewidth=0.25, zorder=1)
    hubs.plot(ax=ax, color=HUB_LAND, edgecolor=EDGE, linewidth=0.35, zorder=2)

    outbound: dict[str, float] = {iso2: 0.0 for iso2 in ANCHORS}
    groups: dict[tuple[str, str], list[tuple]] = {}
    for row in CORRIDORS:
        groups.setdefault((row[0], row[1]), []).append(row)
        outbound[row[0]] += row[5]
    largest_node = max(outbound.values())

    drawn = []
    for (origin, dest), rows in groups.items():
        lanes = _lanes([row[4] for row in rows])
        start, end = points[origin], points[dest]
        bow = PAIR_BOW[frozenset({origin, dest})]
        for row in sorted(rows, key=lambda item: item[5], reverse=True):
            asset, billion = row[4], row[5]
            curve = _curve(start, end, bow, lanes[asset])
            curve = _trim(curve, end, _gap(outbound[dest], largest_node))
            drawn.append((billion, asset, curve))
    drawn.sort(key=lambda item: item[0], reverse=True)

    for billion, asset, curve in drawn:
        color = ASSET_STYLE[asset][1]
        width = _width(billion)
        xs, ys = zip(*curve, strict=True)
        ax.plot(xs, ys, color=HALO, lw=width + 1.15, solid_capstyle="round", zorder=3)
        ax.plot(xs, ys, color=color, lw=width, solid_capstyle="round", zorder=4)
        ax.add_patch(
            Polygon(
                _arrow(curve, billion),
                closed=True,
                facecolor=color,
                edgecolor=HALO,
                linewidth=0.4,
                zorder=5,
            )
        )

    for iso2, (x, y) in points.items():
        area = _marker_area(outbound[iso2], largest_node)
        ax.scatter(
            [x],
            [y],
            s=area,
            c=INK,
            edgecolors=HALO,
            linewidths=0.7,
            zorder=6,
        )
        text, offset, ha, va = LABELS[iso2]
        leader = math.hypot(*offset) > 24
        ax.annotate(
            text,
            (x, y),
            xytext=offset,
            textcoords="offset points",
            color=INK,
            fontsize=8.5,
            ha=ha,
            va=va,
            zorder=7,
            path_effects=LABEL_FX,
            arrowprops=(
                {
                    "arrowstyle": "-",
                    "color": MUTED,
                    "lw": 0.6,
                    "shrinkA": 1,
                    "shrinkB": 7,
                }
                if leader
                else None
            ),
        )

    limit = HORIZON * 1.04
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_aspect("equal")
    ax.set_axis_off()


def _sample(panel, billion: float, y: float, label: str) -> None:
    width = _width(billion)
    panel.plot([0.07, 0.24], [y, y], color=MUTED, lw=width, solid_capstyle="round")
    panel.text(0.28, y, label, fontsize=8.5, color=MUTED, va="center")


def _draw_panel(fig) -> None:
    panel = fig.add_axes((0.545, 0.105, 0.42, 0.75))
    panel.set_xlim(0, 1)
    panel.set_ylim(0, 1)
    panel.set_axis_off()
    panel.add_patch(
        FancyBboxPatch(
            (0.0, 0.0),
            1.0,
            1.0,
            boxstyle="round,pad=0.004,rounding_size=0.02",
            facecolor=PANEL,
            edgecolor="none",
            transform=panel.transAxes,
            clip_on=False,
        )
    )
    y = 0.96
    panel.text(0.06, y, "Four assets", fontsize=13, color=INK, fontweight="medium", va="top")
    y -= 0.07
    for asset in ASSET_ORDER:
        name, color = ASSET_STYLE[asset]
        panel.plot([0.07, 0.20], [y, y], color=color, lw=4.5, solid_capstyle="round")
        panel.text(0.24, y, name, fontsize=11, color=INK, va="center")
        y -= 0.058
    y -= 0.012
    panel.text(0.06, y, "Line width, billion dollars", fontsize=11, color=INK, va="top")
    y -= 0.05
    _sample(panel, 2, y, "2")
    y -= 0.055
    _sample(panel, 5, y, "5")
    y -= 0.062
    _sample(panel, 9.89, y, "9.9, the largest link")
    y -= 0.078
    panel.text(
        0.06,
        y,
        "Circle area sums the corridors\nleaving that country.",
        fontsize=10,
        color=INK,
        va="top",
        linespacing=1.3,
    )
    y -= 0.095
    panel.text(
        0.06,
        y,
        "These twenty links are 5.7% of Bitcoin,\n"
        "3.6% of Ether, 7.3% of USDC, and 2.3%\n"
        "of Tether. The rest is thinner.\n"
        "Türkiye sent 67.9 billion dollars of\n"
        "Tether and Russia 66.1, more than the\n"
        "United Kingdom. Little of that ranks as\n"
        "a single corridor. Vietnam (44.1, Tether)\n"
        "and Korea (19.2, Bitcoin) have none.",
        fontsize=9,
        color=MUTED,
        va="top",
        linespacing=1.35,
    )


def render(countries: gpd.GeoDataFrame) -> None:
    points = _project_anchors()
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI, facecolor=PAPER)
    ax = fig.add_axes((0.015, 0.075, 0.50, 0.80))
    _draw_world(ax, countries, points)
    _draw_panel(fig)
    fig.text(
        0.035,
        0.955,
        "The thickest crypto corridors",
        fontsize=26,
        color=INK,
        fontweight="medium",
        ha="left",
        va="center",
    )
    fig.text(
        0.035,
        0.905,
        "Five largest country-to-country flows in each asset, July 2023 through June 2024.",
        fontsize=11,
        color=MUTED,
        ha="left",
        va="center",
    )
    fig.text(
        0.035,
        0.028,
        "Source: BIS Working Paper 1265, Tables 1 and 2 (Auer, Lewrick, Paulick, May 2025). "
        "Exchange flows assigned to countries by app usage or web traffic. "
        "Natural Earth. Created by Colin T. Stiles.",
        fontsize=7.5,
        color=MUTED,
        ha="left",
        va="bottom",
    )
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    print(f"wrote {OUT_PNG.relative_to(ROOT)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-download the Natural Earth country files.",
    )
    args = parser.parse_args()
    check_tables()
    write_tables()
    write_world(args.refresh)
    countries = load_countries(args.refresh)
    print(f"corridors {len(CORRIDORS)} senders {len(SENDERS)}", flush=True)
    render(countries)


if __name__ == "__main__":
    main()
