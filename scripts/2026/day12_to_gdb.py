#!/usr/bin/env python3
"""Load Day 12 GeoJSON into the 2026 file geodatabase.

Source files are the downloads in data/raw/day12, plus the weekly series in
data/raw/day12/weekly-2026. Each becomes one feature class in
G:\\GIS\\D_tin-topo\\project_data\\30_day_map_challenge\\2026\\2026.gdb.
Existing day12_ classes are overwritten. Other classes in the geodatabase
are left as they are.

The occupied GeoJSON has no color of its own. This writes color_hex,
color_r, color_g, color_b, and color_a onto each feature, then saves a layer
file in day12_layers next to the geodatabase. Add the layer file to the map.
Adding the feature class alone uses Pro's default symbol.

Run with ArcGIS Pro's Python:

    "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" scripts\\day12_to_gdb.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import arcpy

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "day12"
WEEKLY = SOURCE / "weekly-2026"
GDB = Path(r"G:\GIS\D_tin-topo\project_data\30_day_map_challenge\2026\2026.gdb")
LAYERS = GDB.parent / "day12_layers"
WGS84 = arcpy.SpatialReference(4326)
INK = (36, 31, 26, 100)
CLAIM_TOKENS = ("sevastopol", "kherson", "zaporiz", "donetsk", "luhansk", "luhans", "crimea", "krym")


def feature_class_name(path: Path) -> str:
    stem = path.stem
    if path.parent.name in ("gained", "retaken"):
        return f"day12_{stem}"[:60]
    if stem.startswith("deepstatemap_data_"):
        stamp = stem.replace("deepstatemap_data_", "")
        prefix = "day12_week" if path.parent.name == "weekly-2026" else "day12_occupied"
        return f"{prefix}_{stamp}"
    if stem == "ukr-adm0":
        return "day12_ukraine"
    if stem == "ukr-adm1":
        return "day12_oblasts"
    if stem.startswith("ne_50m"):
        return "day12_countries"
    safe = "".join(char if char.isalnum() else "_" for char in stem)
    return f"day12_{safe}"[:60]


def color_for(path: Path, props: dict) -> tuple[int, int, int, int, str]:
    if path.parent.name == "gained":
        return (161, 92, 56, 95, "A15C38")
    if path.parent.name == "retaken":
        return (62, 107, 88, 95, "3E6B58")
    if path.stem.startswith("deepstatemap_data_"):
        return (154, 143, 130, 85, "9A8F82")
    if path.stem == "ukr-adm0":
        return (228, 221, 210, 100, "E4DDD2")
    if path.stem.startswith("ne_50m"):
        return (230, 224, 214, 100, "E6E0D6")
    if path.stem == "ukr-adm1":
        blob = " ".join(
            str(props.get(key) or "")
            for key in ("shapeName", "shapeISO", "NAME", "name", "ADMIN")
        ).casefold()
        if any(token in blob for token in CLAIM_TOKENS):
            return (198, 161, 90, 80, "C6A15A")
        return (228, 221, 210, 100, "E4DDD2")
    return (228, 221, 210, 100, "E4DDD2")


def stage_geojson(path: Path, dest: Path) -> dict[str, tuple[int, int, int, int]]:
    """Drop the crs tag and store an explicit color on every feature."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("crs", None)
    colors: dict[str, tuple[int, int, int, int]] = {}
    for feature in payload.get("features", []):
        props = feature.get("properties")
        if not isinstance(props, dict):
            props = {}
        red, green, blue, alpha, hex_color = color_for(path, props)
        props["color_hex"] = hex_color
        props["color_r"] = red
        props["color_g"] = green
        props["color_b"] = blue
        props["color_a"] = alpha
        feature["properties"] = props
        colors[hex_color] = (red, green, blue, alpha)
    dest.write_text(json.dumps(payload), encoding="utf-8")
    return colors


def polygon_symbol(red: int, green: int, blue: int, alpha: int) -> dict:
    return {
        "type": "CIMSymbolReference",
        "symbol": {
            "type": "CIMPolygonSymbol",
            "symbolLayers": [
                {
                    "type": "CIMSolidStroke",
                    "enable": True,
                    "capStyle": "Round",
                    "joinStyle": "Round",
                    "width": 0.4,
                    "color": {"type": "CIMRGBColor", "values": list(INK)},
                },
                {
                    "type": "CIMSolidFill",
                    "enable": True,
                    "color": {"type": "CIMRGBColor", "values": [red, green, blue, alpha]},
                },
            ],
        },
    }


def write_layer_file(name: str, colors: dict[str, tuple[int, int, int, int]]) -> Path:
    classes = []
    for hex_color, (red, green, blue, alpha) in sorted(colors.items()):
        classes.append(
            {
                "type": "CIMUniqueValueClass",
                "label": f"#{hex_color}",
                "patch": "Default",
                "visible": True,
                "symbol": polygon_symbol(red, green, blue, alpha),
                "values": [{"type": "CIMUniqueValue", "fieldValues": [hex_color]}],
            }
        )
    document = {
        "type": "CIMLayerDocument",
        "version": "3.1.0",
        "build": 41833,
        "layers": [f"CIMPATH=map/{name}.json"],
        "layerDefinitions": [
            {
                "type": "CIMFeatureLayer",
                "name": name,
                "uRI": f"CIMPATH=map/{name}.json",
                "useSourceMetadata": True,
                "layerType": "Operational",
                "showLegends": True,
                "visibility": True,
                "displayCacheType": "Permanent",
                "maxDisplayCacheAge": 5,
                "showPopups": True,
                "serviceLayerID": -1,
                "refreshRate": -1,
                "refreshRateUnit": "esriTimeUnitsSeconds",
                "blendingMode": "Alpha",
                "featureTable": {
                    "type": "CIMFeatureTable",
                    "displayField": "color_hex",
                    "editable": True,
                    "dataConnection": {
                        "type": "CIMStandardDataConnection",
                        "workspaceConnectionString": f"DATABASE={GDB}",
                        "workspaceFactory": "FileGDB",
                        "dataset": name,
                        "datasetType": "esriDTFeatureClass",
                    },
                    "studyAreaSpatialRel": "esriSpatialRelUndefined",
                    "searchOrder": "esriSearchOrderSpatial",
                },
                "htmlPopupEnabled": True,
                "selectable": True,
                "featureCacheType": "Session",
                "featureBlendingMode": "Alpha",
                "scaleSymbols": True,
                "snappable": True,
                "renderer": {
                    "type": "CIMUniqueValueRenderer",
                    "fields": ["color_hex"],
                    "defaultLabel": "other",
                    "groups": [
                        {
                            "type": "CIMUniqueValueGroup",
                            "classes": classes,
                            "heading": "color_hex",
                        }
                    ],
                },
            }
        ],
    }
    LAYERS.mkdir(parents=True, exist_ok=True)
    dest = LAYERS / f"{name}.lyrx"
    dest.write_text(json.dumps(document), encoding="utf-8")
    return dest


def load_one(source: Path, scratch: Path) -> str:
    name = feature_class_name(source)
    out = str(GDB / name)
    staged = scratch / f"{name}.geojson"
    colors = stage_geojson(source, staged)
    if arcpy.Exists(out):
        arcpy.management.Delete(out)
    arcpy.conversion.JSONToFeatures(str(staged), out)
    describe = arcpy.Describe(out)
    code = describe.spatialReference.factoryCode
    if code != 4326:
        arcpy.management.DefineProjection(out, WGS84)
    layer_file = write_layer_file(name, colors)
    count = int(arcpy.management.GetCount(out)[0])
    print(f"{source.name} -> {name} ({count} features), {layer_file.name}")
    return name


def source_files() -> list[Path]:
    files = sorted(SOURCE.glob("*.geojson"))
    if WEEKLY.is_dir():
        files.extend(sorted(WEEKLY.glob("*.geojson")))
        for status in ("gained", "retaken"):
            files.extend(sorted((WEEKLY / status).glob("*.geojson")))
    return files


def main() -> None:
    if not SOURCE.is_dir():
        raise SystemExit(f"Missing source folder: {SOURCE}")
    if not GDB.exists():
        raise SystemExit(f"Missing file geodatabase: {GDB}")
    files = source_files()
    if not files:
        raise SystemExit(f"No GeoJSON files in {SOURCE}")

    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = str(GDB)
    scratch = Path(arcpy.env.scratchFolder) / "day12_geojson"
    scratch.mkdir(parents=True, exist_ok=True)

    written = []
    for path in files:
        written.append(load_one(path, scratch))
    print(f"Wrote {len(written)} feature classes to {GDB}")
    print(f"Layer files with the fill colors: {LAYERS}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
