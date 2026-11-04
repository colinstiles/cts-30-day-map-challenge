# 30 Day Map Challenge

**colin@colinstiles.com**

[![Live Site](https://img.shields.io/badge/Live_Site-challenge.colinstiles.com-brightgreen?logo=githubpages&logoColor=white)](https://challenge.colinstiles.com)
[![Validate](https://github.com/colinstiles/cts-30-day-map-challenge/actions/workflows/ci.yml/badge.svg)](https://github.com/colinstiles/cts-30-day-map-challenge/actions/workflows/ci.yml)
[![30 Day Map Challenge](https://img.shields.io/badge/30_Day_Map_Challenge-2026-8B4513?logo=maplibre&logoColor=white)](https://30daymapchallenge.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Geopandas](https://img.shields.io/badge/Geopandas-Active-139C5A.svg)](https://geopandas.org/)
[![ArcGIS Online](https://img.shields.io/badge/ArcGIS_Online-Ready-orange.svg)](https://www.arcgis.com/)

Colin's yearly entries for the [#30DayMapChallenge](https://30daymapchallenge.com/), covering
planning notes, source data workflows, and the gallery site at
[challenge.colinstiles.com](https://challenge.colinstiles.com) that shows each year's finished maps.
The gallery is linked from [colinstiles.com](https://colinstiles.com) (see the `cts-portfolio` repo).

## Contents

- [30 Day Map Challenge](#30-day-map-challenge)
  - [Contents](#contents)
  - [Map Gallery](#map-gallery)
  - [Yearly Plans](#yearly-plans)
  - [Repository Structure](#repository-structure)
  - [Point of Contact](#point-of-contact)

## Map Gallery

`index.html` is a static page served by GitHub Pages with HTTPS enforced. It has no build step.

- **Year tabs** switch between challenge years. The newest year loads by default, and `?year=2026` links to a specific one.
- **Day cards** show the day number, theme, concept, date, and tools. Each card links to the full-size map.
- **Interactive maps** can live as HTML pages (for example `2026/day-04.html`) and embed in a card via the `embed` field in `days-data.js`.
- **Placeholders** show "Coming Nov N" for any day that doesn't have an image yet.

The page is driven by two folders:

| Path | Purpose |
| --- | --- |
| `assets/js/days-data.js` | One entry per day for every year: date, theme, concept, and tool. Optional `embed` points at an interactive HTML map. |
| `<year>/images/day-NN.png` | The finished map for each day. `.jpg` and `.jpeg` also work. |

The page itself lives in `index.html`, with styling in `assets/css/style.css` and logic in `assets/js/gallery.js`.

Open `index.html` directly in a browser, or run `python -m http.server` from the repository root and visit `http://localhost:8000`.

## Yearly Plans

Each year has a planning document in its own folder:

- `2026/30-Day-Map-Challenge-2026-Plan.md`: the day-by-day plan, with the table of themes, concepts, and effort levels at the top.

Keep the table and the `assets/js/days-data.js` concepts in sync when a day's topic changes.

## Repository Structure

```text
├── .devcontainer/            # VS Code dev container config
├── .github/workflows/        # CI workflow (ci.yml) and Dependabot config
├── assets/
│   ├── css/style.css         # Gallery styling
│   └── js/                   # Gallery logic, day data, and optional Mars globe script
├── 2026/                     # 2026 plan, interactive maps, and map images
├── 2027/                     # 2027 folder (images/ ready for the next challenge)
├── data/
│   ├── processed/            # Derived outputs and archived originals (gitignored)
│   └── raw/                  # Unaltered downloads, read-only (gitignored)
├── notebooks/                # Jupyter notebooks for exploration
├── scripts/                  # Production-ready Python or Node.js scripts
├── src/                      # Reusable production Python code
├── index.html                # Gallery page, served at challenge.colinstiles.com
├── requirements.txt          # Core Python dependencies (pinned)
├── requirements-dev.txt      # Development tools (JupyterLab, ruff, pytest, pre-commit)
├── AGENTS.md / CLAUDE.md     # Instructions for AI coding agents
└── README.md                 # This file
```

Dependabot checks GitHub Actions and pip dependencies monthly.

## Point of Contact

* **Project Owner:** Colin T. Stiles | colin@colinstiles.com
* **Last Updated:** 2026-11-04