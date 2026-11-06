# 2026 — 30 Day Map Challenge

Year folder for the challenge plan, working notes, interactive embeds, and gallery exports.

## Layout

```text
2026/
├── 30-Day-Map-Challenge-2026-Plan.md   # Master plan (linked from the gallery)
├── images/                             # Finished maps for challenge.colinstiles.com
│   └── day-NN.png|jpg|jpeg             # Gallery picks these up automatically
├── day-NN.html                         # Optional interactive map (register `embed` in days-data.js)
├── 00_reference/                       # Shared basemaps, templates, style notes
├── 01_points/ … 30_pen_paper/          # Per-day working notes, deps, scratch
└── README.md                           # This file
```

## Conventions

| Kind | Where | Notes |
| --- | --- | --- |
| Gallery raster | `images/day-NN.png` (or `.jpg` / `.jpeg`) | Do not put finals in day folders |
| Interactive HTML | `2026/day-NN.html` | Keep at year root so `../assets/` paths stay simple |
| Day notes / deps | `NN_theme/` | e.g. `06_vintage/NOTES.md` |
| Raw / processed GIS | `data/raw/`, `data/processed/` | Gitignored; never commit large binaries |
| Production scripts | `scripts/` | e.g. `scripts/day06_vintage_chattanooga.py` |

Gallery metadata lives in `assets/js/days-data.js` (`imageDir: "2026/images"`). Keep day concepts there in sync with the plan table.
