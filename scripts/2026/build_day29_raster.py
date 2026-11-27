"""Day 29 — Raster: future large-fire weather on a LANDFIRE fuel grid.

Tennessee at 270 m. The fuel surface is LANDFIRE LF2022 Scott and Burgan
40, with LF2020 elevation and slope. LFPS no longer serves the LF2020
fuel mosaic. LF2022 is the closest fuel grid still on that service.

The climate signal is Riley et al. 2025. FSim was run twice on a 2020
LANDFIRE landscape: once with 2004–2018 weather, once with that weather
shifted by six CMIP5 RCP8.5 models to 2040–2054. Vegetation is not
projected forward. Burn probability is the share of simulated years in
which a large fire burned the cell.

The three pictures are the same grid. Threat brightens each fuel color
by the 2047 probability. Fuels is the LANDFIRE mosaic alone. Change
warms where the 2047 probability is higher and cools where it is lower.

Raw downloads stay in data/raw/day29/, which is gitignored. A corporate
proxy may need the local Zscaler CA on SSL_CERT_FILE. Do not disable
TLS verification. The Box archive is served over HTTP/1.1; HTTP/2 to
that host can drop the handshake.

Run from the repository root:

    python scripts/2026/build_day29_raster.py
"""

from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.features import rasterize
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds

import _env  # noqa: F401  (loads .env for SSL_CERT_FILE / REQUESTS_CA_BUNDLE)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "day29"
OUT = ROOT / "2026" / "day-29"
LF_TIF = RAW / "lf" / "j58ab8aabe86b41588b12b8bd614853c4.tif"
BP_RECENT = RAW / "fsim" / "bp2011.tif"
BP_FUTURE = RAW / "fsim" / "bp2047.tif"
COUNTIES = RAW / "tennessee_counties.geojson"
COUNTY_CHANGE = RAW / "county_change.csv"
CELL_M = 270.0
ACRE_M2 = 4046.8564224

# code, short name, group. Scott and Burgan 40, LANDFIRE numeric codes.
FUELS: dict[int, tuple[str, str]] = {
    91: ("urban", "nonburnable"),
    92: ("snow or ice", "nonburnable"),
    93: ("agriculture", "nonburnable"),
    98: ("water", "nonburnable"),
    99: ("barren", "nonburnable"),
    101: ("GR1 short sparse dry grass", "grass"),
    102: ("GR2 low dry grass", "grass"),
    103: ("GR3 coarse humid grass", "grass"),
    104: ("GR4 moderate dry grass", "grass"),
    105: ("GR5 low humid grass", "grass"),
    106: ("GR6 moderate humid grass", "grass"),
    107: ("GR7 high dry grass", "grass"),
    108: ("GR8 high coarse humid grass", "grass"),
    109: ("GR9 very high humid grass", "grass"),
    121: ("GS1 low dry grass-shrub", "grass-shrub"),
    122: ("GS2 moderate dry grass-shrub", "grass-shrub"),
    123: ("GS3 moderate humid grass-shrub", "grass-shrub"),
    124: ("GS4 high humid grass-shrub", "grass-shrub"),
    141: ("SH1 low dry shrub", "shrub"),
    142: ("SH2 moderate dry shrub", "shrub"),
    143: ("SH3 moderate humid shrub", "shrub"),
    144: ("SH4 low humid timber-shrub", "shrub"),
    145: ("SH5 high dry shrub", "shrub"),
    146: ("SH6 low humid shrub", "shrub"),
    147: ("SH7 very high dry shrub", "shrub"),
    148: ("SH8 high humid shrub", "shrub"),
    149: ("SH9 very high humid shrub", "shrub"),
    161: ("TU1 low dry timber-grass-shrub", "timber-understory"),
    162: ("TU2 moderate humid timber-shrub", "timber-understory"),
    163: ("TU3 moderate humid timber-grass-shrub", "timber-understory"),
    164: ("TU4 dwarf conifer", "timber-understory"),
    165: ("TU5 very high dry timber-shrub", "timber-understory"),
    181: ("TL1 compact conifer litter", "timber-litter"),
    182: ("TL2 broadleaf litter", "timber-litter"),
    183: ("TL3 moderate conifer litter", "timber-litter"),
    184: ("TL4 small downed logs", "timber-litter"),
    185: ("TL5 high conifer litter", "timber-litter"),
    186: ("TL6 moderate broadleaf litter", "timber-litter"),
    187: ("TL7 large downed logs", "timber-litter"),
    188: ("TL8 long-needle litter", "timber-litter"),
    189: ("TL9 very high broadleaf litter", "timber-litter"),
    201: ("SB1 low activity fuel", "slash"),
    202: ("SB2 moderate activity fuel", "slash"),
    203: ("SB3 high activity fuel", "slash"),
    204: ("SB4 high blowdown", "slash"),
}

GROUP_RGB: dict[str, tuple[int, int, int]] = {
    "grass": (186, 154, 86),
    "grass-shrub": (168, 108, 58),
    "shrub": (148, 82, 52),
    "timber-understory": (122, 70, 46),
    "timber-litter": (96, 60, 44),
    "slash": (70, 44, 36),
    "nonburnable": (58, 64, 58),
}

GROUP_ORDER = (
    "grass",
    "grass-shrub",
    "shrub",
    "timber-understory",
    "timber-litter",
    "slash",
    "nonburnable",
)

COUNTY_QUERIES = (
    (
        "https://maps.cot.tn.gov/hosting/rest/services/Hosted/TN_Counties/"
        "FeatureServer/0/query?where=1%3D1&outFields=name&outSR=4326&f=geojson"
    ),
    (
        "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
        "State_County/MapServer/1/query?where=STATE%3D%2747%27"
        "&outFields=NAME&outSR=4326&f=geojson"
    ),
)


def load_counties():
    import geopandas as gpd

    if not COUNTIES.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        last_error = "no response"
        for url in COUNTY_QUERIES:
            try:
                with urllib.request.urlopen(url, timeout=90) as response:
                    COUNTIES.write_bytes(response.read())
                break
            except OSError as error:
                last_error = str(error)
        if not COUNTIES.exists():
            raise RuntimeError(f"Could not download Tennessee counties: {last_error}")
    counties = gpd.read_file(COUNTIES)
    if counties.crs is None:
        counties = counties.set_crs(4326)
    return counties


def state_mask(shape: tuple[int, int], transform, crs, all_touched: bool = True) -> np.ndarray:
    counties = load_counties().to_crs(crs)
    state = counties.dissolve()
    burned = rasterize(
        ((geom, 1) for geom in state.geometry if geom is not None),
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype="uint8",
        all_touched=all_touched,
    )
    return burned.astype(bool)


def erode(mask: np.ndarray) -> np.ndarray:
    out = mask.copy()
    out[1:, :] &= mask[:-1, :]
    out[:-1, :] &= mask[1:, :]
    out[:, 1:] &= mask[:, :-1]
    out[:, :-1] &= mask[:, 1:]
    return out


def dilate(mask: np.ndarray) -> np.ndarray:
    out = mask.copy()
    out[1:, :] |= mask[:-1, :]
    out[:-1, :] |= mask[1:, :]
    out[:, 1:] |= mask[:, :-1]
    out[:, :-1] |= mask[:, 1:]
    return out


def boundary(mask: np.ndarray) -> np.ndarray:
    edge = mask & ~erode(mask)
    edge = dilate(edge) & mask
    return dilate(edge) & mask


def hillshade(elev: np.ndarray) -> np.ndarray:
    dy, dx = np.gradient(elev.astype(np.float64), CELL_M)
    slope = np.pi / 2.0 - np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    azimuth = np.radians(315.0)
    altitude = np.radians(42.0)
    shaded = np.sin(altitude) * np.sin(slope) + np.cos(altitude) * np.cos(slope) * np.cos(
        azimuth - aspect
    )
    return np.clip(shaded, 0.0, 1.0)


def read_bp(path: Path, bounds, transform, crs, shape: tuple[int, int]) -> np.ndarray:
    """Nearest-neighbor the national grid onto the LANDFIRE cells.

    The two 270 m grids are the same projection and cell size. This
    extract's origin is 30 m off the national origin, about a ninth of
    a cell, so the arrays are not already aligned.
    """
    pad = CELL_M * 2
    with rasterio.open(path) as src:
        window = from_bounds(
            bounds.left - pad,
            bounds.bottom - pad,
            bounds.right + pad,
            bounds.top + pad,
            transform=src.transform,
        )
        window = window.round_offsets().round_lengths()
        source = src.read(1, window=window).astype(np.float32)
        source[~np.isfinite(source) | (source < 0)] = -1.0
        destination = np.full(shape, -1.0, dtype=np.float32)
        reproject(
            source,
            destination,
            src_transform=src.window_transform(window),
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=crs,
            resampling=Resampling.nearest,
            src_nodata=-1.0,
            dst_nodata=-1.0,
        )
    destination[destination < 0] = 0.0
    return destination


def simulated_years(probability: float) -> str:
    """Say how often the cell burned, not a fire-return interval.

    Riley et al. define burn probability as times burned divided by
    simulated years, and they say that ratio is not a return interval.
    """
    if not np.isfinite(probability) or probability <= 0:
        return "no simulated large fire"
    per_10k = probability * 10000.0
    if per_10k >= 100:
        return f"{per_10k / 100:.2f}% of simulated years"
    if per_10k >= 10:
        return f"{per_10k:.1f} of 10,000 simulated years"
    return f"{per_10k:.2f} of 10,000 simulated years"


def rounded_acres(probability_sum: float) -> int:
    return int(round(probability_sum * CELL_M * CELL_M / ACRE_M2 / 100.0) * 100)


def county_declines() -> tuple[int, int] | None:
    """Count Tennessee counties whose published mean burn probability falls."""
    if not COUNTY_CHANGE.exists():
        return None
    decline = 0
    total = 0
    with COUNTY_CHANGE.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["STATE_NAME"] != "Tennessee":
                continue
            total += 1
            if float(row["mean_BP_Percent_Change"]) < 0:
                decline += 1
    if total == 0:
        return None
    return decline, total


def crop_box(mask: np.ndarray, pad: int = 8) -> tuple[int, int, int, int]:
    rows, cols = np.where(mask)
    if rows.size == 0:
        raise RuntimeError("Tennessee mask is empty")
    height, width = mask.shape
    row0 = max(0, int(rows.min()) - pad)
    row1 = min(height, int(rows.max()) + pad + 1)
    col0 = max(0, int(cols.min()) - pad)
    col1 = min(width, int(cols.max()) + pad + 1)
    return row0, row1, col0, col1


def to_u8(rgb: np.ndarray) -> np.ndarray:
    return np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)


def save_rgba(path: Path, rgb: np.ndarray, alpha: np.ndarray) -> None:
    image = np.dstack([to_u8(rgb), alpha]).astype(np.uint8)
    Image.fromarray(image, "RGBA").save(path, optimize=True)


def pack_probability(probability: np.ndarray, scale: float) -> tuple[np.ndarray, np.ndarray]:
    quantized = np.clip(np.round(probability / scale * 65535.0), 0, 65535).astype(np.uint16)
    high = (quantized >> 8).astype(np.uint8)
    low = (quantized & 255).astype(np.uint8)
    return high, low


def main() -> None:
    if not LF_TIF.exists():
        raise SystemExit(f"Missing LANDFIRE extract: {LF_TIF}")
    if not BP_RECENT.exists() or not BP_FUTURE.exists():
        raise SystemExit("Missing FSim burn probability rasters in data/raw/day29/fsim/")

    with rasterio.open(LF_TIF) as src:
        elev = src.read(1).astype(np.float32)
        slope = src.read(2).astype(np.float32)
        fuel = src.read(3).astype(np.int16)
        transform = src.transform
        crs = src.crs
        bounds = src.bounds
        nodata = src.nodata

    if nodata is not None:
        missing = fuel == int(nodata)
    else:
        missing = np.zeros(fuel.shape, dtype=bool)

    inside = state_mask(fuel.shape, transform, crs) & ~missing
    burnable_codes = [code for code, (_, group) in FUELS.items() if group != "nonburnable"]
    burnable = inside & np.isin(fuel, burnable_codes)
    recent = read_bp(BP_RECENT, bounds, transform, crs, fuel.shape)
    future = read_bp(BP_FUTURE, bounds, transform, crs, fuel.shape)
    if recent.shape != fuel.shape or future.shape != fuel.shape:
        raise RuntimeError(
            f"Grid mismatch landfire {fuel.shape} recent {recent.shape} future {future.shape}"
        )

    shade = hillshade(np.where(missing, np.nanmedian(elev), elev))
    shade = 0.78 + 0.22 * shade

    present = sorted(int(code) for code in np.unique(fuel[inside]) if int(code) in FUELS)
    index_of = {code: i + 1 for i, code in enumerate(present)}
    fuel_index = np.zeros(fuel.shape, dtype=np.uint8)
    for code, index in index_of.items():
        fuel_index[fuel == code] = index
    fuel_index[~inside] = 0

    color = np.zeros(fuel.shape + (3,), dtype=np.float32)
    for code, index in index_of.items():
        group = FUELS[code][1]
        rgb = np.array(GROUP_RGB[group], dtype=np.float32) / 255.0
        color[fuel == code] = rgb
    color[~inside] = 0

    hot = future[burnable]
    scale98 = float(np.percentile(hot, 98)) if hot.size else 1e-4
    scale98 = max(scale98, 1e-6)
    threat_t = np.zeros(fuel.shape, dtype=np.float32)
    threat_t[burnable] = np.clip(np.sqrt(future[burnable] / scale98), 0, 1)
    ember = np.array([0.86, 0.40, 0.18], dtype=np.float32)
    dark = color * 0.20
    bright = np.minimum(1.0, color * 1.05 + ember * 0.55)
    threat_rgb = dark * (1.0 - threat_t[..., None]) + bright * threat_t[..., None]
    threat_rgb *= shade[..., None]
    quiet = np.array([0.11, 0.12, 0.11], dtype=np.float32)
    nonburn = inside & ~burnable
    threat_rgb[nonburn] = quiet * shade[nonburn, None]

    fuel_rgb = color * (0.42 + 0.58 * ((shade - 0.78) / 0.22))[..., None]
    fuel_rgb = np.clip(fuel_rgb, 0, 1)
    fuel_rgb[nonburn] = quiet * 1.15

    delta = future - recent
    change_scale = float(np.percentile(np.abs(delta[burnable]), 98)) if hot.size else 1e-4
    change_scale = max(change_scale, 1e-8)
    signed = np.zeros(fuel.shape, dtype=np.float32)
    signed[burnable] = np.clip(delta[burnable] / change_scale, -1, 1)
    cool = np.array([0.38, 0.52, 0.56], dtype=np.float32)
    magnitude = np.abs(signed)[..., None]
    tint = np.where(signed[..., None] >= 0, ember, cool)
    change_rgb = (color * 0.25) * (1.0 - magnitude) + tint * magnitude
    change_rgb *= shade[..., None]
    change_rgb[nonburn] = quiet * shade[nonburn, None]

    line = boundary(inside)
    ink = np.array([0.95, 0.93, 0.88], dtype=np.float32)
    for picture in (threat_rgb, fuel_rgb, change_rgb):
        picture[line] = ink

    alpha = np.where(inside, np.uint8(255), np.uint8(0))
    row0, row1, col0, col1 = crop_box(inside)
    sl = np.s_[row0:row1, col0:col1]
    OUT.mkdir(parents=True, exist_ok=True)
    save_rgba(OUT / "day-29.png", threat_rgb[sl], alpha[sl])
    save_rgba(OUT / "fuels.png", fuel_rgb[sl], alpha[sl])
    save_rgba(OUT / "change.png", change_rgb[sl], alpha[sl])

    peak = float(max(future[burnable].max(initial=0), recent[burnable].max(initial=0), 1e-6))
    future_hi, future_lo = pack_probability(future, peak)
    recent_hi, recent_lo = pack_probability(recent, peak)
    slope_u8 = np.clip(np.round(slope), 0, 90).astype(np.uint8)
    values = np.dstack([future_hi, future_lo, fuel_index])[sl]
    recent_pack = np.dstack([recent_hi, recent_lo, slope_u8])[sl]
    Image.fromarray(values, "RGB").save(OUT / "values.png", optimize=True)
    Image.fromarray(recent_pack, "RGB").save(OUT / "recent.png", optimize=True)

    # Acre totals use cell centers inside the state, every fuel class.
    # LF2022 non-burnable ground still carries some 2020-landscape
    # probability, so a burnable-only sum would drop real simulated area.
    # The picture still leaves that ground dark.
    counted = state_mask(fuel.shape, transform, crs, all_touched=False) & ~missing
    median_recent = float(np.median(recent[burnable]))
    median_future = float(np.median(future[burnable]))
    recent_p98 = float(np.percentile(recent[burnable], 98))
    share_up = float(np.mean(future[burnable] > recent[burnable] + 1e-8))
    share_down = float(np.mean(future[burnable] < recent[burnable] - 1e-8))
    acres = int(round(int(burnable.sum()) * CELL_M * CELL_M / ACRE_M2))
    expected_recent = rounded_acres(float(recent[counted].sum()))
    expected_future = rounded_acres(float(future[counted].sum()))
    declines = county_declines()
    county_sentence = ""
    if declines is not None:
        fell, counties = declines
        county_sentence = f" Published county means fall in {fell} of {counties} counties."
    summary = (
        f"Summed over Tennessee, the burn probabilities come to about "
        f"{expected_recent:,} acres a year under 2004–2018 weather and about "
        f"{expected_future:,} under 2040–2054 weather.{county_sentence}"
    )
    fuels_meta = [
        {
            "index": index_of[code],
            "code": code,
            "name": FUELS[code][0],
            "group": FUELS[code][1],
        }
        for code in present
    ]
    groups = [
        {"id": name, "color": "#{:02x}{:02x}{:02x}".format(*GROUP_RGB[name])}
        for name in GROUP_ORDER
    ]
    meta = {
        "summary": summary,
        "cellMeters": CELL_M,
        "bpScale": peak,
        "threatPercentile": scale98,
        "changeScale": change_scale,
        "burnableAcres": acres,
        "expectedAcresRecent": expected_recent,
        "expectedAcresFuture": expected_future,
        "shareHigher": share_up,
        "shareLower": share_down,
        "medianRecent": median_recent,
        "medianFuture": median_future,
        "recentPercentile": recent_p98,
        "fuels": fuels_meta,
        "groups": groups,
        "notes": {
            "threat": (
                "Brightness is the share of simulated years a large fire burned the cell "
                f"under 2040–2054 weather. The scale tops out at the 98th percentile, "
                f"{simulated_years(scale98)}. Color is the fuel group."
            ),
            "fuels": "LANDFIRE LF2022 fire-behavior fuel model. Relief is LF2020 elevation.",
            "change": (
                "Ember where the 2047 probability is higher than 2004–2018. "
                "Slate where it is lower. The stretch is the 98th percentile "
                "of the absolute difference."
            ),
        },
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(summary)
    print(f"burnable acres {acres:,}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
