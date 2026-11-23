# Day 23 — Senses: Taste

**Date:** November 23, 2026
**Map:** Taste of Tennessee
**Sheet:** `2026/day-23/day-23.png`

Fiscal year 2025, October 2024 through September 2025. That is the latest complete year in the USDA ERS file.

The sheet is distilled spirits only. The other foods in the ERS table are not drawn. The lines leave the point between Jack Daniel's and George Dickel.

The globes are orthographic. An azimuthal equidistant disk centered on Tennessee pushed Australia to the rim and stretched it. Europe is on the large Atlantic globe. Australia is on a second globe centered on the continent. Each buyer has its own color. Width is stretched from the smallest of these five buyers to the largest, because the dollar amounts sit close together and a true zero-based scale made the strokes look alike. The strokes run onto each country. They are translucent, and the borders are drawn over them, so the coasts stay visible. Names and amounts are in the buyer panel.

Type is Playfair Display. Jack Daniel's marketing headlines use JD Serif Bold, a proprietary brand face, so the sheet uses this open serif in its place. The font files are `scripts/2026/fonts/`.

| Buyer | Million dollars |
| --- | ---: |
| Netherlands | 101 |
| Poland | 73.3 |
| United Kingdom | 72.8 |
| France | 66.9 |
| Australia | 56.9 |

Those five are the buyers ERS publishes for this commodity. They sum to 371 million dollars, 44 percent of the 842 million dollar World total. Smaller buyers are not in the table.

The dollars are Census origin-of-movement exports. The state is where the shipment was consolidated, not a brand and not necessarily the distillery that made the spirit. The lines are not split between makers.

Jack Daniel's at Lynchburg and George Dickel at Cascade Hollow are marked because they are the two largest Tennessee whiskey producers. The coordinates are OpenStreetMap, retrieved 23 November 2026. Jack Daniel's is the visitor grounds on Lynchburg Highway. George Dickel is the works on Cascade Hollow Road.

Rebuild the sheet from the repository root:

```text
python3 scripts/2026/build_day23_taste.py
```

`ers.usda.gov` may fail to resolve on the corporate DNS. The script then needs the cached CSV at `data/2026/raw/day23_ers_exports_by_country.csv`. A corporate proxy may need the local Zscaler CA on `SSL_CERT_FILE`. Do not disable TLS verification.

## Files

| Piece | Where |
| --- | --- |
| Sheet | `2026/day-23/day-23.png` |
| Drawing | `scripts/2026/build_day23_taste.py` |
| Type | `scripts/2026/fonts/` |
| Named buyers | `2026/day-23/destinations.csv` |
| Makers | `2026/day-23/makers.csv` |
| ERS source, cached | `data/2026/raw/day23_ers_exports_by_country.csv` |
