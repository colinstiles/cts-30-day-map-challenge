# Day 12 — Power

**Date:** November 12, 2026
**Theme:** Power
**Working title:** Year 5: the claim and the hold
**Tools:** Python (`geopandas`), MapLibre, GeoLibre, ArcGIS Pro
**Script:** `scripts/build_day12_power.py`

## Setup

From the repository root:

```text
pip install -r requirements.txt
python scripts/build_day12_power.py
```

The first run downloads Ukraine's outline, the oblasts, a Natural Earth country file, and a weekly stack of occupied-area assessments from 24 February 2026 through the latest snapshot on or before 12 November 2026. Those files stay in `data/raw/day12/` and `data/processed/day12/`. Both folders are gitignored.

`--refresh` ignores that cache. `--opening-m` is the width of redraw left off the change layer (default 150). `--min-km2` drops change pieces smaller than that (default 0.5).

Behind Zscaler, trust the local corporate certificate if HTTPS fails. Do not disable TLS for routine runs.

## What the color means

Year 5 of the full-scale war starts on 24 February 2026. This map runs from that day to the latest assessment on or before 12 November 2026.

Three layers come from one source:

- **Ochre** is the claim: Crimea, Sevastopol, and all of Luhansk, Donetsk, Zaporizhzhia, and Kherson. Ochre still visible at the end is claimed and not assessed as occupied.
- **Stone** is the hold: assessed occupation on the first day of Year 5, clipped to the Ukraine outline.
- **Clay** passed to Russian control after that day. **Green** passed back to Ukrainian control.

The change layer is opened by 150 m before it is drawn. A sliver thinner than that, including a vertex edit along an otherwise stable line, stays off the sheet. The log prints the unfiltered gain and loss beside the drawn figures. The national occupied-area totals are the clipped assessments, before that opening.

Areas use a Ukraine Albers equal-area projection: standard parallels 46°N and 52°N, origin 48°N, 32°E, WGS84. Working polygons are simplified by 100 m before the difference, so the square-kilometer totals are fit to that line.

Calendar-year 2026 figures published elsewhere, including ISW totals for January through October, use another method and another window. They are context for why this year is worth drawing. They are not the numbers on the sheet.

## Dates

- Year 5 begins 24 February 2026, the anniversary of the full-scale invasion on 24 February 2022.
- The sheet's end date is the newest cached assessment on or before 12 November 2026. If that day has no file, the script walks backward up to six days and prints the date it used.
- Weekly frames step seven days from the baseline. The interactive scrubber uses those frames.

## Sheet

The gallery raster is a portrait tabloid, 11 by 17 inches, at 150 dpi. Type is Georgia when the machine has it.

The national map keeps the year's change small on purpose: the ochre is the power that has not been taken. An inset frames the unheld claim and whatever change survived the 150 m opening. A bar chart is the net change from the baseline at each month's last frame.

## Time map

`2026/day-12.html` is a MapLibre page. It reads `2026/12_power/frames.json` and paints clay and green against the 24 February hold.

`2026/12_power/year5-the-claim-and-the-hold.geolibre.json` is the same week stack inside GeoLibre. Open that project and turn on the time slider. It is bound to `assess_date`, with a six-day lookback so each weekly polygon stays visible until the next snapshot.

## Outputs

- `2026/12_power/gis/year5-power.gpkg` — all layers in one GeoPackage for ArcGIS Pro or GeoLibre. Git ignores `*.gpkg`, so this file stays on the machine that built it.
- `2026/12_power/gis/*.geojson` — the same layers as GeoJSON, EPSG:4326
- `2026/12_power/year5-the-claim-and-the-hold.geolibre.json` — GeoLibre project. The time slider is bound to `assess_date`.
- `2026/images/day-12.png` — draft sheet, replaced when the Pro or GeoLibre layout is done
- `2026/12_power/frames.json` — simplified claim, hold, and weekly change for the MapLibre page
- `data/raw/day12/` — downloaded assessments and boundaries
- `data/processed/day12/` — clipped working polygons

Layer dictionary: `2026/12_power/DATA.md`.

## Sources

- Assessed control: [DeepStateMap.live](https://deepstatemap.live/). Daily GeoJSON is read from [cyterat/deepstate-map-data](https://github.com/cyterat/deepstate-map-data). Their license allows visual material to be reused when the work links the source. This page links it. It is an assessment, and it is not a copy of their map.
- Ukraine outline and oblasts: [geoBoundaries](https://www.geoboundaries.org/) GB Open UKR ADM0 and ADM1, CC BY 4.0.
- Neighboring countries on the sheet: Natural Earth 50m admin-0, public domain.

## Cities

City dots are ordinary centers, used as anchors so the oblasts can be read. They are not a survey of the front.

| Place | Latitude | Longitude |
| --- | --- | --- |
| Kyiv | 50.4501 | 30.5234 |
| Kharkiv | 49.9935 | 36.2304 |
| Sumy | 50.9077 | 34.7981 |
| Dnipro | 48.4647 | 35.0462 |
| Zaporizhzhia | 47.8388 | 35.1396 |
| Donetsk | 48.0159 | 37.8028 |
| Luhansk | 48.5740 | 39.3078 |
| Mariupol | 47.0971 | 37.5434 |
| Kherson | 46.6354 | 32.6169 |
| Simferopol | 44.9521 | 34.1024 |
| Sevastopol | 44.6166 | 33.5254 |
| Odesa | 46.4825 | 30.7233 |
| Kupiansk | 49.7064 | 37.6165 |
| Kramatorsk | 48.7233 | 37.5564 |
| Pokrovsk | 48.2820 | 37.1758 |
