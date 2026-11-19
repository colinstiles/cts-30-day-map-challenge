#!/usr/bin/env python3
"""Draw the Day 22 sheet: the Mere azimuthal equidistant, without the land.

The center is the Glass Mere on the Vael sphere (VAEL:2026). Coordinates are
degrees on that sphere, not WGS84. Output: 2026/day-22/day-22.png
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "2026" / "day-22" / "day-22.png"

# Published center and charted extent. World longitude is design longitude minus 3.2.
PHI0 = math.radians(5.35)
LAM0 = math.radians(24.5)
WEST, EAST, SOUTH, NORTH = -11.2, 88.8, -36.0, 40.0

W, H = 2400, 1800
SCALE_UP = 2

INK = (16, 32, 38)
LINE = (186, 204, 206)
GOLD = (228, 197, 106)
CREAM = (242, 239, 228)
DIM = (168, 176, 174)
AXIS = (120, 146, 150)


def project(lon_deg, lat_deg):
    phi = math.radians(lat_deg)
    dlam = math.radians(lon_deg) - LAM0
    cosc = (
        math.sin(PHI0) * math.sin(phi)
        + math.cos(PHI0) * math.cos(phi) * math.cos(dlam)
    )
    cosc = max(-1.0, min(1.0, cosc))
    c = math.acos(cosc)
    sinc = math.sin(c)
    if sinc < 1e-8:
        return 0.0, 0.0, 0.0
    sin_t = math.cos(phi) * math.sin(dlam) / sinc
    cos_t = (
        math.cos(PHI0) * math.sin(phi)
        - math.sin(PHI0) * math.cos(phi) * math.cos(dlam)
    ) / sinc
    return c * sin_t, c * cos_t, c


def k_of(c_rad):
    if c_rad < 1e-8:
        return 1.0
    return c_rad / math.sin(c_rad)


def font(size, serif=False):
    path = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
        if serif
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    return ImageFont.truetype(path, size * SCALE_UP)


def main():
    img = Image.new("RGB", (W * SCALE_UP, H * SCALE_UP), INK)
    draw = ImageDraw.Draw(img)
    s = SCALE_UP

    samples = []
    for i in range(33):
        t = i / 32
        lon = WEST + t * (EAST - WEST)
        lat = SOUTH + t * (NORTH - SOUTH)
        for point in ((lon, SOUTH), (lon, NORTH), (WEST, lat), (EAST, lat)):
            x, y, _ = project(*point)
            samples.append((x, y))
    min_x = min(p[0] for p in samples)
    max_x = max(p[0] for p in samples)
    min_y = min(p[1] for p in samples)
    max_y = max(p[1] for p in samples)
    box = (760 * s, 90 * s, 2320 * s, 1710 * s)
    bw = max_x - min_x or 1
    bh = max_y - min_y or 1
    scale = min((box[2] - box[0]) / bw, (box[3] - box[1]) / bh) * 0.92
    origin = ((box[0] + box[2]) / 2 - (min_x + max_x) / 2 * scale,
              (box[1] + box[3]) / 2 + (min_y + max_y) / 2 * scale)

    def px(x, y):
        return origin[0] + x * scale, origin[1] - y * scale

    def polyline(points, fill, width):
        if len(points) < 2:
            return
        draw.line(points, fill=fill, width=width, joint="curve")

    # Graticule of the charted sheet, every 10 degrees, after the projection.
    for lon in range(math.ceil(WEST / 10) * 10, math.floor(EAST) + 1, 10):
        pts = []
        lat = SOUTH
        while lat <= NORTH + 1e-6:
            x, y, _ = project(lon, lat)
            pts.append(px(x, y))
            lat += 1.25
        polyline(pts, (70, 96, 100), 2 * s)
    lat = math.ceil(SOUTH / 10) * 10
    while lat <= NORTH:
        pts = []
        lon = WEST
        while lon <= EAST + 1e-6:
            x, y, _ = project(lon, lat)
            pts.append(px(x, y))
            lon += 1.25
        polyline(pts, (70, 96, 100), 2 * s)
        lat += 10

    # Azimuth rays. θ is measured from north toward east, which is the forward formula.
    c_max = 0.95
    for deg in range(0, 360, 30):
        theta = math.radians(deg)
        pts = []
        step = 0
        while step <= 48:
            c = c_max * step / 48
            pts.append(px(c * math.sin(theta), c * math.cos(theta)))
            step += 1
        polyline(pts, (92, 118, 122), 2 * s)

    # Rings of constant angular distance. Map radius equals c, so distance is true.
    rings = (10, 20, 30, 40, 50)
    for deg in rings:
        c = math.radians(deg)
        pts = []
        for i in range(97):
            theta = 2 * math.pi * i / 96
            pts.append(px(c * math.sin(theta), c * math.cos(theta)))
        polyline(pts, GOLD, 3 * s)
        label_theta = math.radians(148)
        lx, ly = px(c * math.sin(label_theta), c * math.cos(label_theta))
        text = f"{deg}°   k {k_of(c):.3f}"
        draw.text((lx + 8 * s, ly - 8 * s), text, font=font(15), fill=GOLD)

    # Tissot ellipses along the eastern radius. Radial axis is true; the tangent axis is k.
    for deg in (10, 20, 30, 40):
        c = math.radians(deg)
        theta = math.radians(90)
        k = k_of(c)
        radius = math.radians(3.2)
        cx = c * math.sin(theta)
        cy = c * math.cos(theta)
        rx, ry = math.sin(theta), math.cos(theta)
        tx, ty = math.cos(theta), -math.sin(theta)
        pts = []
        for i in range(73):
            a = 2 * math.pi * i / 72
            pts.append(px(
                cx + math.cos(a) * radius * k * tx + math.sin(a) * radius * rx,
                cy + math.cos(a) * radius * k * ty + math.sin(a) * radius * ry,
            ))
        polyline(pts, CREAM, 2 * s)

    # One ellipse, at 40°, with the two scale axes called out.
    c = math.radians(40)
    radius = math.radians(3.2)
    k = k_of(c)
    center = px(c, 0)
    radial_end = px(c + radius, 0)
    tangent_end = px(c, -radius * k)
    draw.line([center, radial_end], fill=CREAM, width=2 * s)
    draw.line([center, tangent_end], fill=CREAM, width=2 * s)
    draw.text((radial_end[0] + 6 * s, radial_end[1] - 18 * s), "h = 1", font=font(14), fill=CREAM)
    draw.text((tangent_end[0] + 8 * s, tangent_end[1] - 6 * s), "k = c / sin c", font=font(14), fill=CREAM)

    ox, oy = px(0, 0)
    draw.line([(ox - 10 * s, oy), (ox + 10 * s, oy)], fill=GOLD, width=2 * s)
    draw.line([(ox, oy - 10 * s), (ox, oy + 10 * s)], fill=GOLD, width=2 * s)
    draw.text((ox + 14 * s, oy + 8 * s), "φ0, λ0", font=font(16), fill=GOLD)

    # Title and the forward equations. This is the sheet, not a control.
    title = font(34, serif=True)
    body = font(16)
    small = font(15)
    x0, y = 72 * s, 78 * s
    draw.text((x0, y), "DAY 22  ·  PROJECTIONS", font=font(13), fill=GOLD)
    y += 28 * s
    draw.text((x0, y), "The Mere projection", font=title, fill=CREAM)
    y += 58 * s
    lines = [
        "Azimuthal equidistant on a sphere.",
        "The map radius is the angular distance c",
        "from the center, so that distance is true.",
        "Direction away from the center is true too.",
        "",
        "φ0 = 5.35°     λ0 = 24.5°",
        "R = 1,250 km     not WGS84",
        "",
        "cos c = sin φ0 sin φ + cos φ0 cos φ cos(λ − λ0)",
        "sin c sin θ = cos φ sin(λ − λ0)",
        "sin c cos θ = cos φ0 sin φ − sin φ0 cos φ cos(λ − λ0)",
        "",
        "x = c sin θ",
        "y = c cos θ",
        "",
        "h = 1          along the radius",
        "k = c / sin c          across it",
    ]
    for line in lines:
        draw.text((x0, y), line, font=body, fill=CREAM if line else DIM)
        y += 26 * s

    # k(c) from the center out to 50°.
    y += 18 * s
    draw.text((x0, y), "Cross-radial scale", font=font(15), fill=GOLD)
    y += 28 * s
    gx0, gy0 = x0, y + 150 * s
    gw, gh = 520 * s, 150 * s
    draw.line([(gx0, gy0 - gh), (gx0, gy0), (gx0 + gw, gy0)], fill=AXIS, width=2 * s)
    curve = []
    for i in range(51):
        deg = i
        c = math.radians(deg)
        kx = gx0 + (deg / 50) * gw
        ky = gy0 - ((k_of(c) - 1) / 0.16) * gh
        curve.append((kx, ky))
    polyline(curve, GOLD, 3 * s)
    for deg in rings:
        c = math.radians(deg)
        kx = gx0 + (deg / 50) * gw
        ky = gy0 - ((k_of(c) - 1) / 0.16) * gh
        r = 4 * s
        draw.ellipse((kx - r, ky - r, kx + r, ky + r), fill=CREAM)
    draw.text((gx0, gy0 + 8 * s), "0°", font=small, fill=DIM)
    draw.text((gx0 + gw - 28 * s, gy0 + 8 * s), "50°", font=small, fill=DIM)
    draw.text((gx0 + 8 * s, gy0 - gh - 4 * s), "k", font=small, fill=DIM)
    draw.text((gx0 + gw / 2 - 20 * s, gy0 + 28 * s), "c", font=small, fill=DIM)
    draw.text((gx0 + 8 * s, gy0 - 4 * s), "1.00", font=font(12), fill=DIM)

    # Same ground radius, drawn large enough to see k. The map ellipses use this shape.
    y = gy0 + 64 * s
    draw.text((x0, y), "Same ground circle, true shape", font=font(15), fill=GOLD)
    y += 36 * s
    detail_r = 42 * s
    for i, deg in enumerate((10, 50)):
        k = k_of(math.radians(deg))
        cx = x0 + (70 + i * 230) * s
        cy = y + detail_r
        pts = []
        for t in range(73):
            a = 2 * math.pi * t / 72
            pts.append((cx + math.cos(a) * detail_r * k, cy + math.sin(a) * detail_r))
        polyline(pts, CREAM, 2 * s)
        draw.line([(cx - detail_r * k, cy), (cx + detail_r * k, cy)], fill=GOLD, width=2 * s)
        draw.text((cx - 18 * s, cy + detail_r + 10 * s), f"{deg}°   k {k:.3f}", font=font(14), fill=CREAM)

    sheet = img.resize((W, H), Image.Resampling.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT, "PNG", optimize=True)
    print(OUT, sheet.size)


if __name__ == "__main__":
    main()
