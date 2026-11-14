"""Render the Day 14 static gallery sheet.

The photograph is the map. This sheet shows the whole sidewalk, the
centimeter grid, the white oak point, and the photo time. The life-size
page is 2026/day-14.html.

Run from the repository root:

    python scripts/build_day14_static_map.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "2026" / "14_borgesian" / "borgesian-leaf.jpg"
OUT = ROOT / "2026" / "images" / "day-14.jpg"

# Same control as assets/js/day14-borges.js.
SCALE_X0 = 0.08
SCALE_X1 = 0.95
SCALE_Y = 0.52
SIDEWALK_M = 1.2192
LEAF_CM = 35
LONG_EDGE = 2000

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def font(size: int, serif: bool = False) -> ImageFont.ImageFont:
    names = ["georgia.ttf", "arial.ttf"] if serif else ["arial.ttf", "georgia.ttf"]
    roots = [Path(r"C:\Windows\Fonts"), Path("/usr/share/fonts/truetype/dejavu")]
    files = {
        "georgia.ttf": ["georgia.ttf", "DejaVuSerif.ttf"],
        "arial.ttf": ["arial.ttf", "DejaVuSans.ttf"],
    }
    for name in names:
        for root in roots:
            for candidate in files[name]:
                path = root / candidate
                if path.exists():
                    return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def format_when(raw: str) -> str:
    text = (raw or "").strip().replace("-", ":").replace("T", " ")
    parts = text.replace(" ", ":").split(":")
    if len(parts) < 5:
        return ""
    try:
        year, month, day, hour, minute = (int(parts[i]) for i in range(5))
    except ValueError:
        return ""
    if not 1 <= month <= 12:
        return ""
    h12 = hour % 12 or 12
    ampm = "PM" if hour >= 12 else "AM"
    return f"{day} {MONTHS[month - 1]} {year}, {h12}:{minute:02d} {ampm}"


def photo_time(image: Image.Image) -> str:
    exif = image.getexif()
    raw = ""
    if exif:
        try:
            raw = exif.get_ifd(34665).get(36867) or ""
        except (AttributeError, KeyError):
            raw = ""
        if not raw:
            raw = exif.get(306) or ""
    if isinstance(raw, bytes):
        raw = raw.split(b"\x00", 1)[0].decode("ascii", "ignore")
    return format_when(str(raw))


def main() -> None:
    source = Image.open(SRC)
    taken = photo_time(source)
    image = ImageOps.exif_transpose(source).convert("RGB")
    scale = LONG_EDGE / max(image.size)
    if scale < 1:
        image = image.resize(
            (round(image.width * scale), round(image.height * scale)),
            Image.Resampling.LANCZOS,
        )
    width, height = image.size
    ground_m = SIDEWALK_M / (SCALE_X1 - SCALE_X0)
    px_per_m = width / ground_m
    x0 = SCALE_X0 * width
    x1 = SCALE_X1 * width
    y_line = SCALE_Y * height

    draw = ImageDraw.Draw(image)
    cell = 0.1 * px_per_m
    x = x0
    index = 0
    while x <= x1 + 1:
        major = index % 5 == 0
        weight = 3 if major else 1
        draw.line([(x, 0), (x, height)], fill=(36, 31, 26), width=weight + 2)
        draw.line([(x, 0), (x, height)], fill=(244, 241, 234), width=weight)
        index += 1
        x = x0 + index * cell
    y = 0.0
    index = 0
    while y < height:
        major = index % 5 == 0
        weight = 3 if major else 1
        draw.line([(x0, y), (x1, y)], fill=(36, 31, 26), width=weight + 2)
        draw.line([(x0, y), (x1, y)], fill=(244, 241, 234), width=weight)
        index += 1
        y = index * cell
    draw.line([(x0, y_line), (x1, y_line)], fill=(36, 31, 26), width=6)
    draw.line([(x0, y_line), (x1, y_line)], fill=(228, 197, 106), width=3)

    label_font = font(max(16, round(cell * 0.18)))
    for i in range(15):
        lx = x0 + (i * 0.1) * px_per_m
        if lx < x0 - 2 or lx > x1 + 2:
            continue
        text = "0 cm" if i == 0 else str(i * 10)
        box = draw.textbbox((0, 0), text, font=label_font)
        tw = box[2] - box[0]
        draw.text((lx - tw / 2, 8), text, font=label_font, fill=(247, 244, 234), stroke_width=3, stroke_fill=(36, 31, 26))

    leaf_x = x0 + (LEAF_CM / 100) * px_per_m
    radius = max(8, round(width * 0.008))
    draw.ellipse(
        [leaf_x - radius, y_line - radius, leaf_x + radius, y_line + radius],
        fill=(61, 79, 40),
        outline=(247, 244, 234),
        width=3,
    )

    banner_h = 210
    sheet = Image.new("RGB", (width, height + banner_h), (243, 240, 234))
    sheet.paste(image, (0, 0))
    pen = ImageDraw.Draw(sheet)
    title_font = font(42, serif=True)
    name_font = font(28, serif=True)
    body_font = font(20)
    y_text = height + 18
    pen.text((28, y_text), "On Exactitude", font=title_font, fill=(36, 31, 26))
    y_text += 50
    pen.text((28, y_text), "White oak, Quercus alba", font=name_font, fill=(105, 65, 42))
    y_text += 40
    when = f"Photographed {taken}" if taken else "Photograph time was not in the file"
    pen.text((28, y_text), when, font=body_font, fill=(36, 31, 26))
    y_text += 30
    pen.text(
        (28, y_text),
        "Concrete between the grass is taken as 4 ft. The life-size map is 1:1.",
        font=body_font,
        fill=(36, 31, 26),
    )
    bar = 0.1 * px_per_m
    bar_y = height + banner_h - 36
    pen.line([(28, bar_y), (28 + bar, bar_y)], fill=(36, 31, 26), width=3)
    pen.line([(28, bar_y - 6), (28, bar_y + 6)], fill=(36, 31, 26), width=3)
    pen.line([(28 + bar, bar_y - 6), (28 + bar, bar_y + 6)], fill=(36, 31, 26), width=3)
    pen.text((36 + bar, bar_y - 10), "10 cm", font=body_font, fill=(36, 31, 26))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT, "JPEG", quality=90, optimize=True)
    print(f"wrote {OUT}")
    print(f"timestamp {taken or 'missing'}")


if __name__ == "__main__":
    main()
