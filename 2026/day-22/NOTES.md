# Day 22 — Projections

**Date:** November 22, 2026
**Map:** The Mere projection
**Datum:** VAEL:2026, sphere, R = 1,250 km
**Sheet:** `2026/day-22/day-22.png`

The center is the Glass Mere on Vael. The land, the coasts, and the place names are left off this sheet. What is drawn is the projection.

Longitude and latitude are degrees on the Vael sphere. Longitude 0 is the Cape Orro meridian. These are not WGS84 degrees.

## The projection

Azimuthal equidistant. The map radius is the angular distance `c` from the center, so distance from that point is true, and so is direction away from it.

Let φ be latitude, λ longitude, and (φ0, λ0) the center, all in radians. φ0 = 5.35°, λ0 = 24.5°.

```text
cos c = sin φ0 sin φ + cos φ0 cos φ cos(λ − λ0)
sin c sin θ = cos φ sin(λ − λ0)
sin c cos θ = cos φ0 sin φ − sin φ0 cos φ cos(λ − λ0)
x = c sin θ
y = c cos θ
```

θ is measured from north toward east. Radial scale `h` is 1. Scale perpendicular to the radius is `k = c / sin c`.

On the sheet:

- Gray curves are the meridians and parallels of the charted extent, after the projection.
- Gold rings are constant `c`, labeled with `k`.
- The ellipses on the eastern radius are Tissot’s indicatrix, a small circle of equal ground radius. The radial axis is `h`. The tangent axis is `k`.
- The curve at the left is `k` from 0° to 50°. The two circles under it are the 10° and 50° indicatrices at one ground radius, drawn large enough to compare.

Rebuild the sheet with:

```text
python3 scripts/build_day22_mere.py
```

## Files

| Piece | Where |
| --- | --- |
| Sheet | `2026/day-22/day-22.png` |
| Drawing | `scripts/build_day22_mere.py` |
| Center and extent | `2026/day-10/vael-frame.json` |
| World generator | `assets/2026/js/vael-world.js` |
