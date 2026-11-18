#!/usr/bin/env python3
"""Clip Natural Earth countries to the Day 13 Europe window.

The page no longer draws this file. The map uses the dark basemap
from scripts/build_day13_basemap.py. This output remains a present-day
reference, not a historical boundary. Working CRS for the area filter
is EPSG:3035. The written file is EPSG:4326.

Raw download: data/raw/day13/ (gitignored).
Output: 2026/13_interactions/europe.geojson
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "day13" / "ne_110m_admin_0_countries.geojson"
OUT = ROOT / "2026" / "13_interactions" / "europe.geojson"
SOURCE = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "v5.1.2/geojson/ne_110m_admin_0_countries.geojson"
)

# Display window used by the map. West of the Urals, north of the Mediterranean,
# far enough east to include western Anatolia and Cyprus.
WINDOW = box(-12.0, 34.0, 46.0, 71.0)
KEEP = {
    "ALB",
    "AUT",
    "BEL",
    "BGR",
    "BIH",
    "BLR",
    "CHE",
    "CYP",
    "CZE",
    "DEU",
    "DNK",
    "ESP",
    "EST",
    "FIN",
    "FRA",
    "GBR",
    "GEO",
    "GRC",
    "HRV",
    "HUN",
    "IRL",
    "ISL",
    "ITA",
    "LTU",
    "LUX",
    "LVA",
    "MDA",
    "MKD",
    "MNE",
    "NLD",
    "NOR",
    "POL",
    "PRT",
    "ROU",
    "RUS",
    "SRB",
    "SVK",
    "SVN",
    "SWE",
    "TUR",
    "UKR",
}

# 110m is already coarse. A light simplify keeps the gallery file small
# without moving a coastline by more than a few kilometers on screen.
SIMPLIFY_M = 6000
MIN_KM2 = 1500
# Anchors sit inside the clipped country. They are orientation labels,
# not a full name plate for every state.
LABEL_AT = {
    "United Kingdom": [-1.5, 52.6],
    "France": [2.4, 46.6],
    "Spain": [-3.6, 40.2],
    "Italy": [12.4, 42.8],
    "Germany": [10.4, 51.1],
    "Poland": [19.4, 52.1],
    "Ukraine": [31.4, 49.0],
    "Russia": [37.5, 56.2],
    "Turkey": [32.5, 39.4],
    "Sweden": [15.2, 62.8],
    "Finland": [26.2, 63.8],
    "Norway": [8.5, 61.8],
    "Romania": [24.8, 45.9],
    "Greece": [22.0, 39.3],
}
# Natural Earth 5.1.2 assigns Crimea to Russia. This reference keeps it with
# Ukraine. The map paints Russian administration since 2014 as a separate layer.
CRIMEA = Point(34.10, 44.95)


def main() -> None:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    if not RAW.exists():
        urllib.request.urlretrieve(SOURCE, RAW)

    world = gpd.read_file(RAW)
    if world.crs is None:
        world = world.set_crs(4326)
    else:
        world = world.to_crs(4326)

    world["iso"] = world["ADM0_A3"].where(world["ADM0_A3"].notna(), world["ISO_A3"])
    europe = world[world["iso"].isin(KEEP)].copy()

    clipped = gpd.clip(europe, WINDOW)
    clipped = clipped[~clipped.geometry.is_empty & clipped.geometry.notna()].copy()

    # Area filter in an equal-area CRS so overseas fragments and clip slivers drop.
    measured = clipped.to_crs(3035)
    measured["geometry"] = measured.geometry.simplify(SIMPLIFY_M, preserve_topology=True)
    measured = measured[measured.geometry.area >= MIN_KM2 * 1_000_000]
    measured = measured.to_crs(4326)
    # Contains-test in EPSG:4326. Crimea is a separate part of the Russia
    # multipolygon; Kaliningrad is the other exclave and stays with Russia.
    rus_rows = measured.index[measured["iso"] == "RUS"]
    ukr_rows = measured.index[measured["iso"] == "UKR"]
    if len(rus_rows) and len(ukr_rows):
        rus_geom = measured.at[rus_rows[0], "geometry"]
        rus_parts = list(rus_geom.geoms) if rus_geom.geom_type == "MultiPolygon" else [rus_geom]
        crimea_parts = [part for part in rus_parts if part.contains(CRIMEA)]
        other_parts = [part for part in rus_parts if not part.contains(CRIMEA)]
        if crimea_parts and other_parts:
            measured.at[rus_rows[0], "geometry"] = unary_union(other_parts)
            measured.at[ukr_rows[0], "geometry"] = unary_union(
                [measured.at[ukr_rows[0], "geometry"], *crimea_parts]
            )

    features = []
    for _, row in measured.iterrows():
        name = row["NAME"]
        if name == "Bosnia and Herz.":
            name = "Bosnia and Herzegovina"
        anchor = LABEL_AT.get(name)
        label_at = None
        if anchor is not None and row.geometry.intersects(Point(anchor)):
            label_at = anchor
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": name,
                    "iso": row["iso"],
                    "labelAt": label_at,
                },
                "geometry": json.loads(gpd.GeoSeries([row.geometry], crs=4326).to_json())[
                    "features"
                ][0]["geometry"],
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    collection = {"type": "FeatureCollection", "features": features}
    OUT.write_text(json.dumps(collection, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {len(features)} countries, {OUT.stat().st_size} bytes")
    print(", ".join(sorted(feature["properties"]["name"] for feature in features)))


if __name__ == "__main__":
    main()
