# 2026 — 30 Day Map Challenge

Year folder for the challenge plan, working notes, interactive embeds, and gallery exports.

## Layout

```text
2026/
├── 30-Day-Map-Challenge-2026-Plan.md   # Master plan (linked from the gallery)
├── day-01/ … day-30/                   # Per-day folders
│   ├── day-NN.png|jpg|jpeg             # Gallery raster (auto-detected or via `image` field)
│   ├── day-NN.html                     # Optional interactive map (registered in `embed` field)
│   └── day-NN-*.png|json               # Working assets, variants, bounds
├── images/                             # Deprecated; kept for history. Now empty.
├── 00_reference/                       # Shared basemaps, templates, style notes
├── 01_points/ … 30_pen_paper/          # Per-day working notes, deps, scratch (optional)
└── README.md                           # This file
```

## Conventions

| Kind | Where | Notes |
| --- | --- | --- |
| Gallery raster | `day-NN/day-NN.png` (or `.jpg` / `.jpeg`) | Each day's final map in its folder. Registered via `image` field in days-data.js. |
| Interactive HTML | `day-NN/day-NN.html` | Optional. Registered via `embed` field in days-data.js. Uses `../../assets/` for relative paths. |
| Working assets | `day-NN/day-NN-*.png|json` | Variants, overlays, bounds, process files. |
| Day notes / deps | `NN_theme/` | e.g. `06_vintage/NOTES.md`. Optional; for context and reference. |
| Raw / processed GIS | `data/raw/`, `data/processed/` | Gitignored; never commit large binaries |
| Production scripts | `scripts/` | e.g. `scripts/day06_vintage_chattanooga.py` |

Gallery metadata lives in `assets/js/days-data.js`. Each day with an image or embed has an explicit `image` or `embed` field. Keep day concepts in sync with the plan table.
