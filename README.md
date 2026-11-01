# 30 Day Map Challenge

**colin@colinstiles.com**

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Geopandas](https://img.shields.io/badge/Geopandas-Active-success.svg)](https://geopandas.org/)
[![AGOL](https://img.shields.io/badge/ArcGIS_Online-Ready-orange.svg)](https://www.arcgis.com/)

> Source data, analysis, and planning for Colin's yearly [#30DayMapChallenge](https://30daymapchallenge.com/)
> entries, plus the `index.html` gallery page that displays each year's finished maps.
> The gallery is linked from [colinstiles.com](https://colinstiles.com) (see the `cts-portfolio` repo).

## Map Gallery

`index.html` (served via GitHub Pages from this repo) renders one card per challenge day,
pulling day/theme/concept data from `assets/js/days-data.js` and images from `<year>/images/day-NN.*`.
To add a new year:

1. Append a year entry (with its 30 days) to `assets/js/days-data.js`.
2. Create `<year>/images/` and drop in `day-01.jpg` ... `day-30.jpg` (or `.jpeg`/`.png`) as maps are finished.
3. Days without an image yet automatically show a "Coming &lt;date&gt;" placeholder card.

---

## Repository Structure

This project follows the standard `tin+topo` template structure to keep data, exploration, and production code completely separated:

```text
├── assets/                # CSS/JS for the index.html gallery page
├── data/
│   ├── processed/         # Cleaned, derived, or finalized spatial data
│   └── raw/               # Original, unaltered spatial downloads (DO NOT COMMIT to Git)
├── <year>/                # One folder per challenge year (plan markdown + images/)
├── notebooks/             # Jupyter Notebooks for spatial exploration and prototyping
├── scripts/               # Production-ready Python or Node.js scripts
├── src/                   # Reusable production Python code
├── index.html             # The gallery page, linked from colinstiles.com
├── .env.example           # Template for local environment variables and secrets
├── .gitignore             # Standard GIS ignore rules (blocks massive spatial binaries)
├── AGENTS.md and CLAUDE.md   # AI coding-agent constraints and project guidance
├── README.md              # Project documentation (You are here!)
└── requirements.txt       # Python dependencies (pandas, geopandas, arcgis, etc.)
```

## Getting Started

### 1. Clone the Repository
Clone this repository to your local machine (e.g., `C:\github\[project-name]`). Do not clone into a OneDrive-synced folder like `Documents` to avoid sync conflicts.

### 2. Configure Environment Variables
**Never commit actual credentials to GitHub.**
1. Create a copy of `.env.example` and rename it to `.env`.
2. Fill in only the values required by your project locally. Use ArcGIS named-user or OAuth authentication where available; do not put passwords, tokens, or certificates in source code.

### 3. Install Dependencies
Install the required libraries to run this project:

```sh
# To install only the core production dependencies:
pip install -r requirements.txt

# To install all development tools (like JupyterLab) as well:
pip install -r requirements-dev.txt
```

### 4. Run Local Checks

```sh
pre-commit install
pre-commit run --all-files
ruff check .
```

Run `pytest` when the project includes tests.

---

## Data Handling Rules

1. **Large Spatial Files:** Do not commit `.shp`, `.gdb`, `.tif`, or any large spatial binaries to this repository.
2. **Raw Data:** Store all raw downloads in `data/raw/`. Treat this folder as read-only.
3. **Outputs:** Write all cleaned, intermediate, and final spatial outputs to `data/processed/`.

---

## AI Agent Compatibility

This repository is pre-configured to work with `tin+topo` AI coding assistants and enterprise models.
Please refer to [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md) for specific instructions on how agents should interact with this codebase.

---

## Point of Contact

* **Project Owner:** Colin T. Stiles | colin@tinandtopo.com
* **Last Updated:** 2026-11-01
