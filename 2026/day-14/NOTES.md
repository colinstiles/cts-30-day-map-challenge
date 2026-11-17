# Day 14 — Borgesian map

**Date:** November 14, 2026
**Theme:** Borgesian map
**Working title:** On exactitude
**Tools:** HTML, CSS, JavaScript
**Gallery:** `2026/day-14.html` (embed in `days-data.js`)

## Map

The photograph is the map. It is shown at 1:1: one centimeter of sidewalk is one centimeter on the screen, after the scale bar is matched to a ruler.

There is no zoom. Drag, the wheel, or the arrow keys move across the slab. Double-click returns to the white oak.

The subject leaf is the one the 4 ft line crosses between the 30 cm and 40 cm ticks. A point there opens a popup with *Quercus alba* and links to the [Tennessee White Oak Initiative](https://naturalresources.tennessee.edu/tennessee-white-oak-initiative/) and the [FEIS review](https://research.fs.usda.gov/feis/species-reviews/quealb). The links stay hidden until the point is clicked.

Centimeter values stay pinned to the top of the screen while the photograph pans. The photograph's timestamp is read from the file and shown at the top right.

## Static sheet

```text
python scripts/build_day14_static_map.py
```

Writes `2026/images/day-14.jpg`: the whole sidewalk, the grid, the point, the photo time, and a 10 cm bar.

## Scale

1. If the JPEG has a focus distance and a 35 mm-equivalent focal length, and that pair puts the frame between 0.9 m and 2.2 m wide, the page uses it. Portrait frames use the 24 mm side of the 35 mm film gate; landscape frames use the 36 mm side.
2. Otherwise the concrete between the grass edges is taken as **4 ft** (1.219 m). Change `SIDEWALK_WIDTH_M` in `assets/js/day14-borges.js` if this slab is a different width. `SCALE_LINE` is that measurement, in fractions of the image, at the oak leaf.

The camera is not straight down, so the centimeter grid is exact along the measured line and approximate toward the edges of the frame.

The `−` / `+` buttons change how many screen pixels stand for one centimeter and remember that correction in this browser. Reset returns to the browser's own centimeter.

## Files

| Path | Role |
| --- | --- |
| `2026/day-14.html` | Page and gallery embed |
| `assets/js/day14-borges.js` | Scale, centimeter grid, pan |
| `assets/css/day14.css` | Sheet and collar |
| `2026/14_borgesian/borgesian-leaf.jpg` | Source photograph |

## Coordinates

The page does not print the photograph's coordinates. A 1:1 map of the slab has no room for a locator, and the geotag is the sidewalk itself. If the JPEG still carries a GPS tag, strip it before a public push so the gallery does not publish that location:

```text
exiftool -gps:all= -overwrite_original 2026/14_borgesian/borgesian-leaf.jpg
```
