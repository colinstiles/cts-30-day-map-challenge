"""Choropleth of recent OpenStreetMap contributors per capita.

A contributor is a distinct OSM account that edited in the country
between 2024-01-01 and 2026-07-01, from the HeiGIT ohsomeNow country
stats (no hashtag filter). Someone who edited in two countries is
counted in both. The map shows where mapping happened, not the
mapper's nationality.

Population is World Bank SP.POP.TOTL from the Open Knowledge
population table, the latest year published for each country. The
color is contributors per 100,000 residents. Countries with no
population figure stay blank.

Countries are Natural Earth 1:50m. Antarctica is left off the sheet.
The projection is EPSG:8857, Equal Earth.

Downloads are cached under data/raw/, which is gitignored. The country
table is 2026/21_osm/contributors.csv. The gallery sheet is
2026/images/day-21.png.

A corporate proxy may need the local Zscaler CA on SSL_CERT_FILE. Do
not disable TLS verification.

Run from the repository root:

    python scripts/build_day21_osm.py
    python scripts/build_day21_osm.py --refresh
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

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DAY = ROOT / "2026" / "21_osm"
OUT_PNG = ROOT / "2026" / "images" / "day-21.png"
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

FIG_W, FIG_H = 16.0, 10.0
DPI = 160

PAPER = "#F4F0E6"
INK = "#1C2430"
MUTED = "#5C6570"
OCEAN = "#D5E0E4"
NODATA = "#E4E0D6"
EDGE = "#F4F0E6"
# Sequential green, light enough that the lowest class still reads on paper.
RAMP = ("#E7F2EA", "#A9D3B5", "#5AAA78", "#1F7A4D", "#0C3D28")

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
    table["per_100k"] = table["contributors"] / table["population"] * 100_000
    DAY.mkdir(parents=True, exist_ok=True)
    export = table.drop(columns="geometry").sort_values("per_100k", ascending=False)
    export.to_csv(TABLE_PATH, index=False)
    return table


def _ranked(table: gpd.GeoDataFrame, high: bool) -> list[tuple[str, float]]:
    eligible = table[table["population"] >= 1_000_000].dropna(subset=["per_100k"])
    ordered = eligible.sort_values("per_100k", ascending=not high).head(5)
    return list(zip(ordered["name"], ordered["per_100k"], strict=True))


def render(table: gpd.GeoDataFrame) -> None:
    mapped = table.to_crs("EPSG:8857")
    # Log scale. The top is the highest rate among countries of at
    # least one million people, so Monaco and St-Martin do not squeeze
    # the rest of the world into one pale green. They share the darkest color.
    big = mapped.loc[mapped["population"] >= 1_000_000, "per_100k"].dropna()
    vmin = 0.5
    vmax = max(float(big.max()), vmin * 10)
    norm = LogNorm(vmin=vmin, vmax=vmax)
    cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list("osm", RAMP)

    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI, facecolor=PAPER)
    ax = fig.add_axes((0.03, 0.12, 0.72, 0.74))
    ax.set_facecolor(OCEAN)
    mapped.plot(
        ax=ax,
        column="per_100k",
        cmap=cmap,
        norm=norm,
        linewidth=0.25,
        edgecolor=EDGE,
        missing_kwds={"color": NODATA, "linewidth": 0.25, "edgecolor": EDGE},
    )
    bounds = mapped.total_bounds
    pad_x = (bounds[2] - bounds[0]) * 0.02
    pad_y = (bounds[3] - bounds[1]) * 0.03
    ax.set_xlim(bounds[0] - pad_x, bounds[2] + pad_x)
    ax.set_ylim(bounds[1] - pad_y, bounds[3] + pad_y)
    ax.set_axis_off()

    fig.text(
        0.035,
        0.93,
        "Who maps OpenStreetMap",
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

    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    cax = fig.add_axes((0.08, 0.075, 0.36, 0.018))
    bar = fig.colorbar(sm, cax=cax, orientation="horizontal")
    bar.outline.set_visible(False)
    ticks = [0.5, 1, 2, 5, 10, 25, 50, 100, 200, 500, 1000]
    ticks = [tick for tick in ticks if vmin * 0.8 <= tick <= vmax * 1.15]
    bar.set_ticks(ticks)
    bar.set_ticklabels([f"{tick:g}" for tick in ticks])
    bar.ax.tick_params(labelsize=8, colors=MUTED, length=0)
    fig.text(
        0.08,
        0.108,
        "Contributors per 100,000 residents. Darkest green is the top of this scale or higher.",
        fontsize=9,
        color=MUTED,
    )

    panel = fig.add_axes((0.76, 0.12, 0.21, 0.74))
    panel.set_xlim(0, 1)
    panel.set_ylim(0, 1)
    panel.set_axis_off()
    panel.add_patch(
        FancyBboxPatch(
            (0.0, 0.02),
            0.98,
            0.96,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            facecolor="#EFEBE1",
            edgecolor="none",
            transform=panel.transAxes,
        )
    )

    def write_rank(title: str, rows: list[tuple[str, float]], y: float) -> float:
        panel.text(0.08, y, title, fontsize=11, color=INK, fontweight="medium", va="top")
        y -= 0.055
        for name, rate in rows:
            label = f"{rate:.0f}" if rate >= 10 else f"{rate:.1f}"
            panel.text(0.08, y, name, fontsize=10, color=INK, va="top")
            panel.text(0.92, y, label, fontsize=10, color=MUTED, ha="right", va="top")
            y -= 0.048
        return y - 0.03

    y = 0.90
    panel.text(0.08, y, "Countries over 1 million", fontsize=9, color=MUTED, va="top")
    y = write_rank("Highest per 100,000", _ranked(mapped, high=True), y - 0.06)
    write_rank("Lowest per 100,000", _ranked(mapped, high=False), y)

    fig.text(
        0.035,
        0.035,
        "A person is counted in every country they edited.  "
        "Blank countries have no World Bank population.  "
        "Sources: HeiGIT ohsomeNow, World Bank population, Natural Earth.",
        fontsize=8,
        color=MUTED,
        ha="left",
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
