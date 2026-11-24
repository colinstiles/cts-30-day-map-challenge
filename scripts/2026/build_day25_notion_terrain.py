"""Hamilton County terrain as a Notion table.

Day 25 asks for a map made without mapping software. The map is a
Notion table of colored cells. This script only collects the numbers
and writes the table markup. It does not draw a map.

Each cell is the USGS 3DEP elevation at the cell center, kept when
that center falls inside the Census TIGER outline of Hamilton County,
Tennessee (GEOID 47065). Cells outside the county stay blank. North
is the first row. Color is one of six Notion background colors, from
low ground to high ground.

The county outline is cached at data/raw/day25_hamilton_county.geojson.
The cell table is 2026/day-25/grid.json. The Notion markup is
2026/day-25/notion-body.md. The gallery page is 2026/day-25/day-25.html.

A corporate proxy may need the local Zscaler CA on SSL_CERT_FILE. Do
not disable TLS verification.

Run from the repository root:

    python scripts/2026/build_day25_notion_terrain.py
    python scripts/2026/build_day25_notion_terrain.py --refresh
"""

from __future__ import annotations

import argparse
import json
import math
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import _env  # noqa: F401  (loads .env for SSL_CERT_FILE)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "day25_hamilton_county.geojson"
OUT_DIR = ROOT / "2026" / "day-25"
GRID_PATH = OUT_DIR / "grid.json"
NOTION_PATH = OUT_DIR / "notion-body.md"
HTML_PATH = OUT_DIR / "day-25.html"

COUNTY_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
    "State_County/MapServer/1/query?where=GEOID%3D%2747065%27"
    "&outFields=NAME,GEOID&f=geojson&outSR=4326"
)
ELEVATION_URL = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer/getSamples"
)

# Columns across the county bounding box. Rows are chosen so a cell is
# about as tall as it is wide on the ground.
NCOLS = 36

# Upper bound of each class, in international feet, and the Notion color.
# Purple is the highest class Notion can set apart from red.
BREAKS = (
    (700, "blue", "Below 700 ft"),
    (1000, "green", "700–1,000 ft"),
    (1400, "yellow", "1,000–1,400 ft"),
    (1800, "orange", "1,400–1,800 ft"),
    (2100, "red", "1,800–2,100 ft"),
    (math.inf, "purple", "Above 2,100 ft"),
)

# Screen colors for the gallery page. Notion's own background swatches
# are paler than these. The class names match the Notion colors.
SCREEN = {
    "blue": "#2f6f9f",
    "green": "#4e8d4a",
    "yellow": "#d4b23a",
    "orange": "#d0782c",
    "red": "#b23b2e",
    "purple": "#6c4c86",
}

PLACES = (
    ("Lookout Point", 35.0106, -85.3434),
    ("Signal Mountain", 35.1273, -85.3455),
    ("Downtown Chattanooga", 35.0456, -85.3094),
    ("Chickamauga Dam", 35.1042, -85.2294),
    ("Chickamauga Lake", 35.1500, -85.1800),
    ("Missionary Ridge", 35.0360, -85.2630),
    ("Moccasin Bend", 35.0480, -85.3320),
    ("East Ridge", 34.9990, -85.2280),
    ("Ooltewah", 35.0650, -85.0620),
    ("Soddy-Daisy", 35.2360, -85.1810),
    ("Sale Creek", 35.3830, -85.1090),
    ("Red Bank", 35.1110, -85.2960),
    ("Elder Mountain", 35.0780, -85.3920),
    ("Apison", 35.0330, -85.0210),
)

M_TO_FT = 1 / 0.3048


def fetch_json(url: str, data: bytes | None = None, timeout: int = 90) -> dict:
    request = urllib.request.Request(url, data=data)
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, context=context, timeout=timeout) as response:
        return json.load(response)


def load_county(refresh: bool) -> dict:
    if RAW.is_file() and not refresh:
        return json.loads(RAW.read_text(encoding="utf-8"))
    payload = fetch_json(COUNTY_URL)
    features = payload.get("features") or []
    if not features:
        raise SystemExit(f"County query returned no features: {payload}")
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def rings_of(geometry: dict) -> list[list[list[float]]]:
    kind = geometry["type"]
    if kind == "Polygon":
        return geometry["coordinates"]
    if kind == "MultiPolygon":
        return [ring for polygon in geometry["coordinates"] for ring in polygon]
    raise SystemExit(f"Unexpected geometry type: {kind}")


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat):
            edge = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < edge:
                inside = not inside
        j = i
    return inside


def in_county(lon: float, lat: float, exterior: list, holes: list) -> bool:
    if not point_in_ring(lon, lat, exterior):
        return False
    return not any(point_in_ring(lon, lat, hole) for hole in holes)


def color_for(feet: float) -> str:
    for limit, name, _label in BREAKS:
        if feet < limit:
            return name
    return BREAKS[-1][1]


def sample_elevations(points: list[list[float]]) -> list[float]:
    """Return meters for each [lon, lat], using USGS 3DEP."""
    values = [math.nan] * len(points)
    pending = list(range(len(points)))
    batch_size = 80
    while pending:
        batch = pending[:batch_size]
        pending = pending[batch_size:]
        body = urllib.parse.urlencode(
            {
                "geometry": json.dumps(
                    {
                        "points": [points[i] for i in batch],
                        "spatialReference": {"wkid": 4326},
                    }
                ),
                "geometryType": "esriGeometryMultipoint",
                "returnFirstValueOnly": "true",
                "interpolation": "RSP_BilinearInterpolation",
                "f": "json",
            }
        ).encode()
        try:
            payload = fetch_json(ELEVATION_URL, data=body)
        except Exception as error:  # noqa: BLE001 — split and retry a smaller batch
            if batch_size == 1:
                raise SystemExit(f"Elevation sample failed: {error}") from error
            batch_size = max(1, batch_size // 2)
            pending = batch + pending
            print(f"elevation batch failed ({error}); retrying at {batch_size}", file=sys.stderr)
            continue
        samples = payload.get("samples") or []
        if len(samples) != len(batch):
            raise SystemExit(
                f"Expected {len(batch)} elevation samples, got {len(samples)}: "
                f"{json.dumps(payload)[:400]}"
            )
        for sample in samples:
            location_id = sample.get("locationId")
            if location_id is None or not (0 <= location_id < len(batch)):
                raise SystemExit(f"Unexpected locationId in {sample}")
            raw = sample.get("value")
            values[batch[location_id]] = float(raw)
        print(f"sampled {len(points) - len(pending)}/{len(points)}", file=sys.stderr)
    return values


def build_grid(geometry: dict) -> dict:
    all_rings = rings_of(geometry)
    exterior = all_rings[0]
    holes = all_rings[1:]
    lons = [point[0] for point in exterior]
    lats = [point[1] for point in exterior]
    lon_min, lon_max = min(lons), max(lons)
    lat_min, lat_max = min(lats), max(lats)
    mid_lat = (lat_min + lat_max) / 2
    km_per_deg_lon = 111.32 * math.cos(math.radians(mid_lat))
    width_km = (lon_max - lon_min) * km_per_deg_lon
    height_km = (lat_max - lat_min) * 111.32
    cell_km = width_km / NCOLS
    nrows = max(1, round(height_km / cell_km))
    dlon = (lon_max - lon_min) / NCOLS
    dlat = (lat_max - lat_min) / nrows

    cells = []
    wanted: list[list[float]] = []
    index_of: list[int] = []
    for row in range(nrows):
        lat = lat_max - (row + 0.5) * dlat
        line = []
        for col in range(NCOLS):
            lon = lon_min + (col + 0.5) * dlon
            inside = in_county(lon, lat, exterior, holes)
            line.append(
                {
                    "lon": round(lon, 5),
                    "lat": round(lat, 5),
                    "feet": None,
                    "color": None,
                }
            )
            if inside:
                index_of.append(len(cells))
                wanted.append([lon, lat])
            cells.append(line[-1])
        # cells is flat; line was just for clarity
    meters = sample_elevations(wanted)
    for slot, meters_value in zip(index_of, meters):
        feet = round(meters_value * M_TO_FT)
        cells[slot]["feet"] = feet
        cells[slot]["color"] = color_for(feet)

    rows = [cells[i * NCOLS : (i + 1) * NCOLS] for i in range(nrows)]
    return {
        "ncols": NCOLS,
        "nrows": nrows,
        "cell_km": round(cell_km, 2),
        "width_km": round(width_km, 1),
        "height_km": round(height_km, 1),
        "bbox": [lon_min, lat_min, lon_max, lat_max],
        "rows": rows,
    }


def nearest_cell(grid: dict, lat: float, lon: float) -> tuple[int, int, dict]:
    best = None
    best_dist = math.inf
    for r, row in enumerate(grid["rows"]):
        for c, cell in enumerate(row):
            dist = (cell["lat"] - lat) ** 2 + (cell["lon"] - lon) ** 2
            if dist < best_dist:
                best_dist = dist
                best = (r, c, cell)
    if best is None:
        raise SystemExit("Grid is empty")
    return best


def notion_table(grid: dict) -> str:
    width = 28
    cols = "".join(f'<col width="{width}" />' for _ in range(grid["ncols"]))
    lines = [
        '<table fit-page-width="true" header-row="false" header-column="false">',
        f"<colgroup>{cols}</colgroup>",
    ]
    for row in grid["rows"]:
        cells = []
        for cell in row:
            color = cell["color"]
            if color is None:
                cells.append("<td> </td>")
            else:
                cells.append(f'<td color="{color}_bg"> </td>')
        lines.append("<tr>" + "".join(cells) + "</tr>")
    lines.append("</table>")
    return "\n".join(lines)


def landforms(grid: dict) -> dict:
    cells = [cell for row in grid["rows"] for cell in row if cell["feet"] is not None]
    lookout = max(cells, key=lambda cell: cell["feet"])
    ridge_cells = [cell for cell in cells if cell["lon"] < -85.28 and cell["lat"] > 35.10]
    ridge = max(ridge_cells, key=lambda cell: cell["feet"])
    river_cells = [cell["feet"] for cell in cells if cell["color"] == "blue" and cell["feet"] >= 600]
    return {
        "lookout_ft": lookout["feet"],
        "ridge_ft": ridge["feet"],
        "river_low_ft": min(river_cells),
        "river_high_ft": max(river_cells),
    }


def notion_body(grid: dict, places: list[dict]) -> str:
    form = landforms(grid)
    by_name = {place["name"]: place for place in places}
    legend = "\n".join(
        f'<callout color="{name}_bg">{label}</callout>' for _limit, name, label in BREAKS
    )
    downtown = by_name["Downtown Chattanooga"]["feet"]
    dam = by_name["Chickamauga Dam"]["feet"]
    bend = by_name["Moccasin Bend"]["feet"]
    return "\n".join(
        [
            "Hamilton County stands up on two sides. The purple cell on the southwest point is Lookout Mountain, "
            f"{form['lookout_ft']:,} feet, the highest sample in the table. The red cells along the northwest are "
            f"Walden's Ridge and Signal Mountain, up to {form['ridge_ft']:,} feet. The blue cells between them are "
            "the Tennessee River. That low ground widens into Chickamauga Lake toward the northeast. Nearly all of "
            "the remaining cells are the valley, where Chattanooga sits.",
            "",
            "Each colored cell is the USGS 3DEP elevation at that cell's center, kept only when the center is inside "
            "Hamilton County. Blank cells are outside the county. North is the top row. The colors are Notion's own "
            "background colors. Nothing in a mapping program drew this table.",
            "",
            notion_table(grid),
            "",
            f"The frame is {grid['height_km']} km north to south and {grid['width_km']} km east to west. "
            f"Each cell is about {grid['cell_km']} km on a side. Along the river the blue cells run from "
            f"{form['river_low_ft']:,} to {form['river_high_ft']:,} feet. "
            f"Moccasin Bend is {bend:,} feet, the Chickamauga Dam cell is {dam:,} feet, and downtown Chattanooga is "
            f"{downtown:,} feet. Missionary Ridge is narrower than a cell, so it disappears into the valley color.",
            "",
            "## Elevation",
            "",
            legend,
            "",
            "## Record",
            "",
            "Day 25 of the 30 Day Map Challenge, 25 November 2026. The theme is whether this still counts as a map.",
            "",
            "The outline is the U.S. Census Bureau TIGER county polygon for Hamilton County, GEOID 47065. "
            "Elevation is a bilinear sample from the USGS 3DEP elevation service, converted from meters to "
            "international feet. The page that holds the color is Notion.",
        ]
    )


def html_page(grid: dict, places: list[dict]) -> str:
    cells = []
    for row in grid["rows"]:
        for cell in row:
            if cell["color"] is None:
                cells.append('<i></i>')
            else:
                feet = f"{cell['feet']:,} ft"
                cells.append(
                    f'<i class="{cell["color"]}" title="{feet}" aria-label="{feet}"></i>'
                )
    legend = "\n".join(
        f'<li><i class="{name}"></i><span>{label}</span></li>'
        for _limit, name, label in BREAKS
    )
    form = landforms(grid)
    by_name = {place["name"]: place for place in places}
    shown = [
        ("Lookout Mountain", form["lookout_ft"]),
        ("Walden's Ridge", form["ridge_ft"]),
        ("Moccasin Bend", by_name["Moccasin Bend"]["feet"]),
        ("Chickamauga Dam", by_name["Chickamauga Dam"]["feet"]),
        ("Downtown Chattanooga", by_name["Downtown Chattanooga"]["feet"]),
    ]
    place_bits = [f"<li>{name}, {feet:,} ft</li>" for name, feet in shown]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Day 25 — Hamilton County in a table</title>
  <meta name="description" content="Hamilton County, Tennessee, drawn as a table of elevation colors. The map of record is a Notion page.">
  <style>
    :root {{
      --paper: #f4f0e6;
      --ink: #1c1914;
      --muted: #5e584e;
      --blue: {SCREEN["blue"]};
      --green: {SCREEN["green"]};
      --yellow: {SCREEN["yellow"]};
      --orange: {SCREEN["orange"]};
      --red: {SCREEN["red"]};
      --purple: {SCREEN["purple"]};
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; height: 100%; background: var(--paper); color: var(--ink); }}
    body {{
      font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
      display: flex;
      flex-direction: column;
      min-height: 100%;
    }}
    header, footer {{ padding: 12px 16px 0; }}
    .kicker {{
      font-family: "IBM Plex Mono", ui-monospace, monospace;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    h1 {{ font-size: 22px; font-weight: 500; margin: 4px 0; }}
    a {{ color: inherit; }}
    .stage {{
      flex: 1;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 220px;
      gap: 16px;
      padding: 12px 16px 16px;
      min-height: 0;
    }}
    .map {{
      display: grid;
      grid-template-columns: repeat({grid["ncols"]}, minmax(0, 1fr));
      grid-auto-rows: 1fr;
      gap: 1px;
      background: transparent;
      align-self: stretch;
      min-height: 0;
    }}
    .map i {{ display: block; background: transparent; }}
    i.blue {{ background: var(--blue); }}
    i.green {{ background: var(--green); }}
    i.yellow {{ background: var(--yellow); }}
    i.orange {{ background: var(--orange); }}
    i.red {{ background: var(--red); }}
    i.purple {{ background: var(--purple); }}
    aside h2 {{
      font-family: "IBM Plex Mono", ui-monospace, monospace;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-weight: 500;
      margin: 0 0 8px;
    }}
    ol, ul {{ list-style: none; margin: 0 0 16px; padding: 0; }}
    li {{ display: flex; gap: 8px; align-items: center; font-size: 13px; margin: 4px 0; }}
    aside li i {{ width: 14px; height: 14px; display: block; flex: none; }}
    .places li {{ display: block; color: var(--muted); font-size: 12px; }}
    footer {{
      font-family: "IBM Plex Mono", ui-monospace, monospace;
      font-size: 11px;
      color: var(--muted);
      padding-bottom: 12px;
    }}
    body.embed header p, body.embed .back, body.embed footer {{ display: none; }}
    body.embed h1 {{ font-size: 16px; }}
    body.embed .stage {{ grid-template-columns: minmax(0, 1fr) 150px; gap: 10px; padding-top: 4px; }}
    @media (max-width: 720px) {{
      .stage {{ grid-template-columns: 1fr; }}
      .map {{ min-height: 70vw; }}
    }}
  </style>
</head>
<body>
  <header>
    <a class="back" href="../../index.html">← Gallery</a>
    <div class="kicker">Day 25 · Is this a map?</div>
    <h1>Hamilton County, Tennessee</h1>
    <p>Elevation of the county, one table cell at a time. North is up. The map of record is the Notion page. This page repeats the same cells for the gallery. The colors here are stronger than Notion's own swatches.</p>
  </header>
  <div class="stage">
    <div class="map" role="img" aria-label="Colored table of elevation in Hamilton County, Tennessee. North is up.">
      {"".join(cells)}
    </div>
    <aside>
      <h2>Elevation</h2>
      <ol>
        {legend}
      </ol>
      <h2>On the grid</h2>
      <ul class="places">
        {"".join(place_bits)}
      </ul>
    </aside>
  </div>
  <footer>
    Each cell is about {grid["cell_km"]} km. USGS 3DEP at the cell center, inside the Census county outline.
    <a id="notion-link" href="NOTION_URL">Open the Notion table</a>
  </footer>
  <script>
    if (new URLSearchParams(location.search).has("embed")) {{
      document.body.classList.add("embed");
    }}
  </script>
</body>
</html>
"""


def ascii_preview(grid: dict) -> str:
    mark = {"blue": "~", "green": ".", "yellow": "+", "orange": "o", "red": "#", "purple": "@"}
    lines = []
    for row in grid["rows"]:
        lines.append("".join(" " if cell["color"] is None else mark[cell["color"]] for cell in row))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Download the county outline again")
    parser.add_argument(
        "--markup-only",
        action="store_true",
        help="Rewrite the Notion markup and gallery page from grid.json",
    )
    args = parser.parse_args()
    if args.markup_only:
        grid = json.loads(GRID_PATH.read_text(encoding="utf-8"))
        places = grid["places"]
        NOTION_PATH.write_text(notion_body(grid, places), encoding="utf-8")
        HTML_PATH.write_text(html_page(grid, places), encoding="utf-8")
        print(f"rewrote {NOTION_PATH.name} and {HTML_PATH.name}")
        return
    county = load_county(args.refresh)
    geometry = county["features"][0]["geometry"]
    grid = build_grid(geometry)
    places = []
    for name, lat, lon in PLACES:
        _row, _col, cell = nearest_cell(grid, lat, lon)
        # Reject a snap that landed outside, or far from the named point.
        # 0.02 degrees is a little over 2 km.
        far = abs(cell["lat"] - lat) > 0.02 or abs(cell["lon"] - lon) > 0.02
        if cell["feet"] is None or far:
            places.append({"name": name, "feet": None, "color": None})
        else:
            places.append(
                {"name": name, "feet": cell["feet"], "color": cell["color"], "lat": cell["lat"], "lon": cell["lon"]}
            )
    grid["places"] = places
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GRID_PATH.write_text(json.dumps(grid), encoding="utf-8")
    NOTION_PATH.write_text(notion_body(grid, places), encoding="utf-8")
    HTML_PATH.write_text(html_page(grid, places), encoding="utf-8")
    inside = sum(cell["feet"] is not None for row in grid["rows"] for cell in row)
    print(f"{grid['nrows']} rows x {grid['ncols']} cols, {inside} cells inside the county")
    print(f"cell {grid['cell_km']} km, frame {grid['width_km']} x {grid['height_km']} km")
    print(ascii_preview(grid))
    for place in places:
        if place["feet"] is None:
            print(f"{place['name']}: outside")
        else:
            print(f"{place['name']}: {place['feet']} ft {place['color']}")


if __name__ == "__main__":
    main()
