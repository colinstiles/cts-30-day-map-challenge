"""Render the Day 5 static viewshed map.

Uses the same Pinnacle Mountain Fire Tower observer, USGS 3DEP grid, and
line-of-sight rules as ``scripts/build_day05_terrain.py``. The picture is a
north-up poster: gold terrain is in sight from the platform, and the rest
stays in shaded relief.

The GeoTIFF is cached under data/raw/, which is gitignored. A corporate
proxy may need the local Zscaler CA on SSL_CERT_FILE. Do not disable TLS
verification.

Run from the repository root:

    python scripts/build_day05_static_map.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "2026" / "images" / "day-05.png"
BG = "#15150F"
PANEL = "#15150FE0"
LINE = "#3A3B2D"
CREAM = "#F2EFE4"
MUTED = "#B8B5A8"
GOLD = "#E8C46A"
OLIVE = "#9CBB74"


def load_terrain():
    path = ROOT / "scripts" / "build_day05_terrain.py"
    spec = importlib.util.spec_from_file_location("day05_terrain", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hillshade(elev: np.ndarray, cell_m: float) -> np.ndarray:
    """Horn hillshade lit from the northwest, matching the interactive map."""
    padded = np.pad(elev, 1, mode="edge")
    dzdx = (
        padded[:-2, 2:] + 2 * padded[1:-1, 2:] + padded[2:, 2:]
        - (padded[:-2, :-2] + 2 * padded[1:-1, :-2] + padded[2:, :-2])
    ) / (8 * cell_m)
    dzdy = (
        padded[2:, :-2] + 2 * padded[2:, 1:-1] + padded[2:, 2:]
        - (padded[:-2, :-2] + 2 * padded[:-2, 1:-1] + padded[:-2, 2:])
    ) / (8 * cell_m)
    slope = np.arctan(np.hypot(dzdx, dzdy))
    aspect = np.arctan2(dzdy, -dzdx)
    zenith = np.deg2rad(48)
    azimuth = np.deg2rad(315)
    shaded = np.cos(zenith) * np.cos(slope) + np.sin(zenith) * np.sin(slope) * np.cos(azimuth - aspect)
    return np.clip(shaded, 0, 1).astype(np.float32)


def colorize(elev: np.ndarray, visible: np.ndarray, shade: np.ndarray) -> np.ndarray:
    """Gold where the platform can see; shaded relief everywhere else."""
    span = max(float(elev.max() - elev.min()), 1.0)
    height = (elev - float(elev.min())) / span
    hidden_low = np.array([0.07, 0.10, 0.07], dtype=np.float32)
    hidden_high = np.array([0.28, 0.25, 0.20], dtype=np.float32)
    seen_low = np.array([0.45, 0.36, 0.12], dtype=np.float32)
    seen_high = np.array([0.96, 0.80, 0.40], dtype=np.float32)
    hidden = hidden_low + (hidden_high - hidden_low) * height[..., None]
    seen = seen_low + (seen_high - seen_low) * height[..., None]
    color = np.where(visible[..., None], seen, hidden)
    lit = (0.34 + 0.85 * shade)[..., None]
    return np.clip(color * lit, 0, 1)


def load_grid(terrain):
    cache = terrain.RAW_PATH.with_name("day05-static-viewshed.npz")
    if cache.exists():
        stored = np.load(cache)
        print(f"loaded {cache.name}", flush=True)
        return stored["elev"], stored["visible"]
    tiff = terrain.RAW_PATH.read_bytes()
    dem, west, south, east, north = terrain.read_usgs_elevation(tiff)
    scale_x = (east - west) / dem.shape[1]
    scale_y = (north - south) / dem.shape[0]
    n_view = int(terrain.RADIUS_M * 2 / terrain.VIEW_M) + 1
    elev = terrain.sample_grid(dem, west, north, scale_x, scale_y, n_view, terrain.VIEW_M)
    if not np.isfinite(elev).all():
        raise ValueError("Sampled elevation grid contains non-finite values.")
    print(f"viewshed {n_view}x{n_view} at {terrain.VIEW_M} m", flush=True)
    visible = terrain.mesh_viewshed(elev, terrain.PLATFORM_HEIGHT_M, terrain.VIEW_M, 1)
    np.savez_compressed(cache, elev=elev, visible=visible)
    print(f"in sight {visible.mean():.1%}", flush=True)
    return elev, visible


def draw_map(terrain, elev: np.ndarray, visible: np.ndarray) -> None:
    shade = hillshade(elev, terrain.VIEW_M)
    image = colorize(elev, visible, shade)
    radius = terrain.RADIUS_M
    cell = terrain.VIEW_M
    n = elev.shape[0]
    m_lat, m_lon = terrain.meters_per_degree(terrain.TOWER_LAT)
    places = terrain.place_records(elev, visible, cell)
    ground = float(elev[n // 2, n // 2])
    share = visible.mean()

    plt.rcParams["font.family"] = "DejaVu Sans"
    fig = plt.figure(figsize=(12, 12), dpi=180, facecolor=BG)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.imshow(
        image,
        origin="upper",
        extent=(-radius, radius, -radius, radius),
        interpolation="bilinear",
        zorder=0,
    )
    ax.set_xlim(-radius, radius)
    ax.set_ylim(-radius, radius)
    ax.set_axis_off()

    def panel(x, y, w, h):
        ax.add_patch(
            Rectangle(
                (x, y),
                w,
                h,
                transform=ax.transAxes,
                facecolor=PANEL,
                edgecolor=LINE,
                linewidth=1,
                zorder=4,
            )
        )

    panel(0.028, 0.78, 0.46, 0.19)
    ax.text(0.048, 0.925, "DAY 5  ·  SENSES: SIGHT", transform=ax.transAxes,
            color="#D99A5B", fontsize=11, fontweight="bold", zorder=5)
    ax.text(0.048, 0.878, "View from the fire tower", transform=ax.transAxes,
            color=OLIVE, fontsize=18, zorder=5)
    ax.text(
        0.048,
        0.805,
        "Pinnacle Mountain Lookout, Buffalo Mountain\n"
        f"{share:.0%} of this window is in sight from the platform",
        transform=ax.transAxes,
        color=MUTED,
        fontsize=10,
        linespacing=1.45,
        zorder=5,
    )

    panel(0.78, 0.86, 0.19, 0.105)
    for i, (label, swatch) in enumerate((("In sight", GOLD), ("Hidden", "#2A3124"))):
        y = 0.925 - i * 0.038
        ax.add_patch(
            Rectangle((0.80, y - 0.008), 0.018, 0.022, transform=ax.transAxes,
                      facecolor=swatch, edgecolor=LINE, linewidth=0.6, zorder=5)
        )
        ax.text(0.828, y, label, transform=ax.transAxes, color=CREAM, fontsize=10,
                va="center", zorder=5)

    stroke = [path_effects.withStroke(linewidth=3.5, foreground=BG)]
    ax.plot(0, 0, marker="o", markersize=7, color=GOLD, markeredgecolor=BG, markeredgewidth=1.2, zorder=6)
    ax.text(
        -1400,
        3200,
        "Fire tower",
        color=GOLD,
        fontsize=12,
        fontweight="bold",
        ha="right",
        va="bottom",
        zorder=6,
        path_effects=stroke,
    )

    for place in places:
        east = (place["lon"] - terrain.TOWER_LON) * m_lon
        north = (place["lat"] - terrain.TOWER_LAT) * m_lat
        seen = place["seen"]
        ax.plot(east, north, marker="o", markersize=4.5,
                color=GOLD if seen else MUTED, zorder=6)
        ha = "left" if east < radius * 0.55 else "right"
        dx = 700 if ha == "left" else -700
        name = place["name"] if seen else f"{place['name']}  ·  hidden"
        ax.text(
            east + dx,
            north + 500,
            name,
            color=CREAM if seen else MUTED,
            fontsize=10,
            ha=ha,
            va="bottom",
            zorder=6,
            path_effects=stroke,
        )

    bar = 10_000
    x0, y0 = -radius + 2800, -radius + 5200
    ax.plot([x0, x0 + bar], [y0, y0], color=CREAM, linewidth=2.4, solid_capstyle="butt", zorder=6)
    ax.plot([x0, x0], [y0 - 280, y0 + 280], color=CREAM, linewidth=1.4, zorder=6)
    ax.plot([x0 + bar, x0 + bar], [y0 - 280, y0 + 280], color=CREAM, linewidth=1.4, zorder=6)
    ax.text(x0 + bar / 2, y0 + 500, "10 km", color=CREAM, fontsize=10, ha="center", va="bottom",
            zorder=6, path_effects=stroke)

    nx, ny = radius - 2800, -radius + 3600
    ax.annotate(
        "",
        xy=(nx, ny + 2200),
        xytext=(nx, ny),
        arrowprops={"arrowstyle": "-|>", "color": CREAM, "lw": 1.4, "mutation_scale": 12},
        zorder=6,
    )
    ax.text(nx, ny + 2600, "N", color=CREAM, fontsize=12, fontweight="bold", ha="center",
            va="bottom", zorder=6, path_effects=stroke)

    ax.text(
        0.5,
        0.028,
        "USGS 3DEP  ·  30 m viewshed  ·  earth curvature and refraction  ·  "
        f"{terrain.TOWER_LAT:.5f}°N, {abs(terrain.TOWER_LON):.5f}°W  ·  tower {ground:.0f} m",
        transform=ax.transAxes,
        color=MUTED,
        fontsize=8.5,
        ha="center",
        va="bottom",
        zorder=6,
        path_effects=stroke,
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"wrote {OUT_PATH.relative_to(ROOT)}", flush=True)


def main() -> None:
    terrain = load_terrain()
    if not terrain.RAW_PATH.exists():
        raise SystemExit("Missing data/raw/day05-3dep-pinnacle.tif. Run scripts/build_day05_terrain.py first.")
    elev, visible = load_grid(terrain)
    draw_map(terrain, elev, visible)


if __name__ == "__main__":
    main()
