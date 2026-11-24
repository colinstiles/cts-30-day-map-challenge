# Day 24 — Network

**Date:** November 24, 2026
**Map:** The thickest crypto corridors
**Sheet:** `2026/day-24/day-24.png`
**Interactive:** `2026/day-24/day-24.html`

July 2023 through June 2024, the latest four quarters in BIS Working Paper 1265 (Auer, Lewrick, and Paulick, May 2025).

The sheet draws the five largest directional country pairs in each of Bitcoin, Ether, USDC, and Tether. That is Table 1. The bilateral matrix is not public, so thinner links are absent. Together the twenty lines are 5.7 percent of Bitcoin's cross-border flow, 3.6 percent of Ether, 7.3 percent of USDC, and 2.3 percent of Tether (Table 3).

Line width is billion dollars. A circle's area is the sum of the corridors drawn leaving that country. It is not the country's full outflow. Table 2 is the full published outflow for the five largest senders in each asset. Türkiye sent 67.9 billion dollars of Tether and Russia 66.1, ahead of the United Kingdom, but little of that gathers into one top-five corridor. Vietnam sent 44.1 billion of Tether and Korea 19.2 billion of Bitcoin, and neither has a corridor on the sheet.

The dots are drawing points, not cities and not exchange domiciles. The United Kingdom's dot is in northern Scotland and Germany's is in Bavaria, so the two circles can sit apart. Western Indonesia is used rather than New Guinea, and European Russia rather than Siberia. Bitcoin flows are Iknaio exchange flows weighted by Sensor Tower app usage. Ether, USDC, and Tether are Chainalysis flows weighted by web traffic. The country is an estimate of where the exchange's users are.

Germany appears because of one Bitcoin corridor, 4.89 billion dollars to the United States. It is not a top-five sender in any of the four assets.

The gallery card opens `2026/day-24/day-24.html`, a tilted kepler.gl map. The same twenty corridors rise as 3D arcs. Thickness is billion dollars and color is the asset. Where several assets share a country pair, each asset is on its own lane, and the two directions sit side by side. The side panel filters by asset. The static sheet is the print version.

Rebuild the sheet from the repository root:

```text
python3 scripts/2026/build_day24_network.py
```

The numbers are transcribed from Tables 1 and 2 into the script. The script checks each printed share against the row amount and the asset total. Natural Earth is cached at `data/2026/raw/ne_50m_admin_0_countries.geojson`. A corporate proxy may need the local Zscaler CA on `SSL_CERT_FILE`. Do not disable TLS verification.

## Files

| Piece | Where |
| --- | --- |
| Sheet | `2026/day-24/day-24.png` |
| Interactive map | `2026/day-24/day-24.html` |
| Drawing | `scripts/2026/build_day24_network.py` |
| Corridors, Table 1 | `2026/day-24/corridors.csv` |
| Senders, Table 2 | `2026/day-24/senders.csv` |
