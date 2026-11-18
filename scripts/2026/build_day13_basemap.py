#!/usr/bin/env python3
"""Build the Day 13 dark human-geography basemap style.

Esri's named Human Geography Dark style requires a basemap token.
This script starts from the public World Basemap v2 vector tiles,
keeps land, water, cities, roads, railways, and boundaries, and
recolors that subset to a dark monochrome style.

Output: 2026/13_interactions/human-geography-dark.json
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "2026" / "13_interactions" / "human-geography-dark.json"
SERVICE = (
    "https://basemaps.arcgis.com/arcgis/rest/services/"
    "World_Basemap_v2/VectorTileServer"
)
STYLE_URL = SERVICE + "/resources/styles/root.json"

LAND = "#23262c"
WATER = "#161b22"
URBAN = "#2c323c"
COAST = "#46505f"
RIVER = "#2c3a4a"
ROAD_CASE = "#101218"
ROAD_LOCAL = "#6d7582"
ROAD_MAJOR = "#d5dbe3"
BOUNDARY = "#aeb6c2"
BOUNDARY_CASE = "#1c2028"
LABEL = "#f4f6f8"
HALO = "#14171c"
BACKGROUND = "#14171c"

ROAD_NAMES = {
    "Road/label/Pedestrian",
    "Road/label/Local",
    "Road/label/Minor",
    "Road/label/Major, alt name",
    "Road/label/Major",
    "Road/label/Freeway Motorway, alt name",
    "Road/label/Highway",
    "Road/label/Freeway Motorway",
}
PLACE_LAYERS = {
    "Admin0 point",
    "Admin1 area/label",
    "Admin2 area/label",
    "City small scale",
    "City large scale",
    "Neighborhood",
    "Continent",
}
WATER_LABELS = {
    "Water area small scale/label",
    "Water area medium scale/label",
    "Marine waterbody/label",
}


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "cts-day13-basemap"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def keep(layer: dict) -> bool:
    kind = layer["type"]
    source = layer.get("source-layer", "")
    name = layer["id"]
    if kind == "fill":
        if source in {"Land", "Urban area"}:
            return True
        if source in {
            "Water area small scale",
            "Water area medium scale",
            "Water area large scale",
        }:
            return "intermittent" not in name.lower()
        if source == "Water area":
            return "Lake" in name or "river" in name or "bay" in name
        return False
    if kind == "line":
        if name.startswith("Water line") or name.startswith("Coastline"):
            return True
        if name.startswith("Road/") or name.startswith("Road tunnel/"):
            return True
        if name.startswith("Railroad/"):
            return True
        return name.startswith("Boundary line/")
    if kind != "symbol":
        return False
    if name in ROAD_NAMES:
        return True
    if source in PLACE_LAYERS or source in WATER_LABELS:
        return True
    return source == "Disputed label point" and name.endswith("Admin0")


def major_road(name: str) -> bool:
    return any(token in name for token in ("Freeway", "Highway", "Major"))


def recolor(layer: dict) -> dict:
    paint = dict(layer.get("paint") or {})
    name = layer["id"]
    kind = layer["type"]
    source = layer.get("source-layer", "")
    if kind == "fill":
        if source == "Land":
            color = LAND
        elif source == "Urban area":
            color = URBAN
        else:
            color = WATER
        paint["fill-color"] = color
        if "fill-outline-color" in paint:
            paint["fill-outline-color"] = color
    elif kind == "line":
        if name.startswith("Water"):
            paint["line-color"] = RIVER
        elif name.startswith("Coastline"):
            paint["line-color"] = COAST
        elif "casing" in name and name.startswith("Boundary"):
            paint["line-color"] = BOUNDARY_CASE
        elif "casing" in name:
            paint["line-color"] = ROAD_CASE
        elif name.startswith("Boundary"):
            paint["line-color"] = BOUNDARY
            if "Disputed" in name and "line-dasharray" not in paint:
                paint["line-dasharray"] = [2, 2]
        elif name.startswith("Railroad"):
            paint["line-color"] = ROAD_LOCAL
        else:
            paint["line-color"] = ROAD_MAJOR if major_road(name) else ROAD_LOCAL
    else:
        paint["text-color"] = LABEL
        paint["text-halo-color"] = HALO
        width = paint.get("text-halo-width")
        paint["text-halo-width"] = width if isinstance(width, (int, float)) and width >= 1.1 else 1.2
        layout = dict(layer.get("layout") or {})
        layout.pop("icon-image", None)
        layer["layout"] = layout
    layer["paint"] = paint
    return layer


def main() -> None:
    service = fetch_json(SERVICE + "?f=json")
    style = fetch_json(STYLE_URL)
    layers = [recolor(layer) for layer in style["layers"] if keep(layer)]
    dark = {
        "version": 8,
        "name": "Human geography dark",
        "glyphs": SERVICE + "/resources/fonts/{fontstack}/{range}.pbf",
        "sources": {
            "esri": {
                "type": "vector",
                "tiles": [SERVICE + "/tile/{z}/{y}/{x}.pbf"],
                "minzoom": 0,
                "maxzoom": int(service.get("maxzoom") or 16),
            }
        },
        "layers": [
            {
                "id": "background",
                "type": "background",
                "paint": {"background-color": BACKGROUND},
            },
            *layers,
        ],
    }
    OUT.write_text(json.dumps(dark, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes, {len(layers)} layers)")


if __name__ == "__main__":
    main()
