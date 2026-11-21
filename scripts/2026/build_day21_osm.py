"""Choropleth of recent OpenStreetMap contributors per capita.

A contributor is a distinct OSM account that edited in the country
between 2024-01-01 and 2026-07-01, from the HeiGIT ohsomeNow country
stats (no hashtag filter). Someone who edited in two countries is
counted in both. The map shows where mapping happened, not the
mapper's nationality.

Population is World Bank SP.POP.TOTL for 2025 from the Open Knowledge
population table. Taiwan is not in that series. Its population is the
Ministry of the Interior household-registration total at 31 December
2025, 23,299,132 people. The color is contributors per 100,000
residents. Countries with no population figure stay blank.

Countries are Natural Earth 1:50m. Antarctica is left off the sheet.
Two Lambert azimuthal equal-area maps share one scale. The cut is in
the Atlantic, so the Americas are on the left and Europe, Africa, Asia,
and Oceania are on the right. A country stays whole on the side of its
main landmass.

Downloads are cached under data/2026/raw/, which is gitignored. The
country table is 2026/day-21/contributors.csv. The gallery sheet is
2026/day-21/day-21.png.

A corporate proxy may need the local Zscaler CA on SSL_CERT_FILE. Do
not disable TLS verification.

Run from the repository root:

    python scripts/2026/build_day21_osm.py
    python scripts/2026/build_day21_osm.py --refresh
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib.colors import LogNorm
from matplotlib.patches import FancyBboxPatch
import _env  # noqa: F401  (loads .env for SSL_CERT_FILE / REQUESTS_CA_BUNDLE)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "2026" / "raw"
DAY = ROOT / "2026" / "day-21"
OUT_PNG = DAY / "day-21.png"
COUNTRIES_PATH = RAW / "ne_50m_admin_0_countries.geojson"
OHSOME_PATH = RAW / "day21_ohsome_users.json"
POP_PATH = RAW / "day21_worldbank_pop.csv"
TABLE_PATH = DAY / "contributors.csv"

COUNTRIES_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "v5.1.2/geojson/ne_50m_admin_0_countries.geojson"
)
OHSOME_URL = "https://stats.now.ohsome.org/api/stats/country"
# World Bank SP.POP.TOTL, republished as a CSV. The live API was
# returning 502 while this map was built.
POP_URL = (
    "https://raw.githubusercontent.com/datasets/population/main/data/population.csv"
)
# Inclusive start, exclusive end. ohsomeNow has no hashtag, so this is
# every mapped country, not a campaign subset.
START = "2024-01-01T00:00:00Z"
END = "2026-07-01T00:00:00Z"
# Natural Earth and ohsome codes that are not the World Bank ISO3.
ISO_FIX = {"KOS": "XKX", "XK": "XKX"}
# World Bank SP.POP.TOTL omits Taiwan. Household-registration population
# at 31 December 2025, Ministry of the Interior, Republic of China.
# https://www.ris.gov.tw/app/en/2121?sn=26245250
TAIWAN_ISO = "TWN"
TAIWAN_POPULATION = 23_299_132
TAIWAN_YEAR = 2025

FIG_W, FIG_H = 16.0, 10.0
DPI = 160

PAPER = "#141210"
INK = "#F6F1E4"
MUTED = "#C4B8A4"
OCEAN = "#1A242C"
NODATA = "#3A3834"
EDGE = "#141210"
PANEL = "#221C16"
# Light purple (fewer) through mauve to dark gold (more).
RAMP = ("#D9C6F2", "#B794D4", "#A67C8C", "#C49A4E", "#6E5424", "#3F3014")
# Atlantic cut. Land to the west is the Americas map. A few Siberian
# islands sit west of the date line; they stay with Asia.
ATLANTIC_CUT = -30.0
WEST_CRS = "+proj=laea +lat_0=12 +lon_0=-80 +datum=WGS84 +units=m +no_defs"
EAST_CRS = "+proj=laea +lat_0=8 +lon_0=45 +datum=WGS84 +units=m +no_defs"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "cts-30-day-map-challenge day-21 educational map"


def download(url: str, dest: Path, params: dict | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = SESSION.get(url, params=params, timeout=(30, 180))
    response.raise_for_status()
    dest.write_bytes(response.content)


def load_countries() -> gpd.GeoDataFrame:
    if not COUNTRIES_PATH.is_file():
        download(COUNTRIES_URL, COUNTRIES_PATH)
    frame = gpd.read_file(COUNTRIES_PATH)
    frame = frame[frame["ADM0_A3"] != "ATA"].copy()
    # ISO_A3 is -99 for France, Norway, and Kosovo. ISO_A3_EH keeps
    # those, and South Sudan as SSD rather than the disputed SDS code.
    # Dependencies such as Ashmore use the parent code in ISO_A3_EH.
    # Keep their own ADM0_A3 so they do not inherit the parent's rate.
    own_country = frame["ADM0_A3"].eq(frame["ISO_A3_EH"]) | frame["ISO_A3"].ne("-99")
    usable = own_country & ~frame["ISO_A3_EH"].isin(["-99", ""])
    iso = frame["ISO_A3_EH"].where(usable, frame["ADM0_A3"])
    frame["iso3"] = iso.replace(ISO_FIX)
    frame["name"] = frame["NAME"]
    return frame[["iso3", "name", "geometry"]].reset_index(drop=True)


def fetch_users(refresh: bool) -> pd.DataFrame:
    if not OHSOME_PATH.is_file() or refresh:
        download(
            OHSOME_URL,
            OHSOME_PATH,
            params={"topics": "contributor", "startdate": START, "enddate": END},
        )
    payload = json.loads(OHSOME_PATH.read_text(encoding="utf-8"))
    rows = payload["result"]["topics"]["contributor"]
    frame = pd.DataFrame(rows).rename(columns={"country": "iso3", "value": "contributors"})
    frame["iso3"] = frame["iso3"].replace(ISO_FIX)
    frame = frame.groupby("iso3", as_index=False)["contributors"].sum()
    return frame[["iso3", "contributors"]]


def fetch_population(refresh: bool) -> pd.DataFrame:
    if not POP_PATH.is_file() or refresh:
        download(POP_URL, POP_PATH)
    frame = pd.read_csv(POP_PATH)
    frame = frame.rename(
        columns={"Country Code": "iso3", "Year": "year", "Value": "population"}
    )
    frame["population"] = pd.to_numeric(frame["population"], errors="coerce")
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame = frame.dropna(subset=["population", "iso3"])
    frame = frame[frame["iso3"].str.len() == 3]
    frame = frame.sort_values("year").groupby("iso3", as_index=False).tail(1)
    return frame[["iso3", "year", "population"]]


def build_table(countries: gpd.GeoDataFrame, refresh: bool) -> gpd.GeoDataFrame:
    users = fetch_users(refresh)
    people = fetch_population(refresh)
    table = countries.merge(users, on="iso3", how="left").merge(people, on="iso3", how="left")
    taiwan = table["iso3"].eq(TAIWAN_ISO)
    table.loc[taiwan, "population"] = TAIWAN_POPULATION
    table.loc[taiwan, "year"] = TAIWAN_YEAR
    table["per_100k"] = table["contributors"] / table["population"] * 100_000
    DAY.mkdir(parents=True, exist_ok=True)
    export = table.drop(columns="geometry").sort_values("per_100k", ascending=False)
    export.to_csv(TABLE_PATH, index=False)
    return table


def _ranked(table: gpd.GeoDataFrame, high: bool) -> list[tuple[str, float]]:
    eligible = table[table["population"] >= 1_000_000].dropna(subset=["per_100k"])
    ordered = eligible.sort_values("per_100k", ascending=not high).head(5)
    return list(zip(ordered["name"], ordered["per_100k"], strict=True))


def _split_hemispheres(table: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    parts = table.explode(index_parts=False).reset_index(drop=True)
    parts = parts[~parts.geometry.is_empty & parts.geometry.notna()].copy()
    point = parts.geometry.representative_point()
    # Far eastern Russia crosses the date line and would otherwise land
    # on the Americas map.
    with_asia = (point.x < -160) & (point.y > 50)
    western = (point.x < ATLANTIC_CUT) & ~with_asia
    return parts.loc[western].copy(), parts.loc[~western].copy()


def _draw_hemisphere(ax, frame: gpd.GeoDataFrame, crs: str, norm, cmap) -> None:
    projected = frame.to_crs(crs)
    ax.set_facecolor(OCEAN)
    projected.plot(
        ax=ax,
        column="per_100k",
        cmap=cmap,
        norm=norm,
        linewidth=0.3,
        edgecolor=EDGE,
        missing_kwds={"color": NODATA, "linewidth": 0.3, "edgecolor": EDGE},
    )
    bounds = projected.total_bounds
    pad_x = (bounds[2] - bounds[0]) * 0.04
    pad_y = (bounds[3] - bounds[1]) * 0.05
    ax.set_xlim(bounds[0] - pad_x, bounds[2] + pad_x)
    ax.set_ylim(bounds[1] - pad_y, bounds[3] + pad_y)
    ax.set_axis_off()


def render(table: gpd.GeoDataFrame) -> None:
    # Log scale. The dark end is the highest rate among countries of at
    # least one million people, so Monaco and St-Martin do not stretch it.
    # They share that darkest gold.
    big = table.loc[table["population"] >= 1_000_000, "per_100k"].dropna()
    vmin = 0.5
    vmax = max(float(big.max()), vmin * 10)
    norm = LogNorm(vmin=vmin, vmax=vmax)
    cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list("osm", RAMP)
    western, eastern = _split_hemispheres(table)

    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI, facecolor=PAPER)
    west_ax = fig.add_axes((0.015, 0.22, 0.33, 0.60))
    east_ax = fig.add_axes((0.34, 0.22, 0.40, 0.60))
    _draw_hemisphere(west_ax, western, WEST_CRS, norm, cmap)
    _draw_hemisphere(east_ax, eastern, EAST_CRS, norm, cmap)

    fig.text(
        0.035,
        0.93,
        "Contributors to OpenStreetMap",
        fontsize=26,
        color=INK,
        fontweight="medium",
        ha="left",
        va="center",
    )
    fig.text(
        0.035,
        0.885,
        "Distinct contributors per 100,000 people, January 2024 – July 2026",
        fontsize=12,
        color=MUTED,
        ha="left",
        va="center",
    )

    map_left, map_right = 0.015, 0.74
    bar_width = 0.42
    bar_left = (map_left + map_right) / 2 - bar_width / 2
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    cax = fig.add_axes((bar_left, 0.145, bar_width, 0.016))
    bar = fig.colorbar(sm, cax=cax, orientation="horizontal")
    bar.outline.set_visible(False)
    ticks = [0.5, 1, 2, 5, 10, 25, 50, 100, 200, 500, 1000]
    ticks = [tick for tick in ticks if vmin * 0.8 <= tick <= vmax * 1.15]
    bar.set_ticks(ticks)
    bar.set_ticklabels([f"{tick:g}" for tick in ticks])
    bar.ax.tick_params(labelsize=8, colors=MUTED, length=0)
    fig.text(bar_left, 0.168, "Fewer Contributors", fontsize=9, color=MUTED, ha="left", va="bottom")
    fig.text(
        bar_left + bar_width,
        0.168,
        "More Contributors",
        fontsize=9,
        color=MUTED,
        ha="right",
        va="bottom",
    )

    panel = fig.add_axes((0.755, 0.520, 0.215, 0.340))
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

    def write_rank(title: str, rows: list[tuple[str, float]], y: float) -> float:
        panel.text(0.07, y, title, fontsize=11, color=INK, fontweight="medium", va="top")
        y -= 0.072
        for name, rate in rows:
            label = f"{rate:.0f}" if rate >= 10 else f"{rate:.1f}"
            panel.text(0.07, y, name, fontsize=10, color=INK, va="top")
            panel.text(0.93, y, label, fontsize=10, color=MUTED, ha="right", va="top")
            y -= 0.064
        return y - 0.018

    y = 0.95
    panel.text(0.07, y, "Countries over 1 million", fontsize=9, color=MUTED, va="top")
    y = write_rank("Highest per 100,000", _ranked(table, high=True), y - 0.075)
    write_rank("Lowest per 100,000", _ranked(table, high=False), y)

    fig.text(
        0.02,
        0.028,
        "Sources: HeiGIT ohsomeNow, World Bank, Taiwan Ministry of the Interior, "
        "Natural Earth. Created by Colin T. Stiles.",
        fontsize=8,
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
        help="Ignore cached ohsome counts and World Bank population.",
    )
    args = parser.parse_args()
    countries = load_countries()
    table = build_table(countries, args.refresh)
    counted = int(table["contributors"].notna().sum())
    rated = int(table["per_100k"].notna().sum())
    print(f"countries {len(table)} with counts {counted} with rates {rated}", flush=True)
    render(table)


if __name__ == "__main__":
    main()
