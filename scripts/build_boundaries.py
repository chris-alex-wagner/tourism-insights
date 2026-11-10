"""Build small, simplified boundary files for the choropleth maps.

Input:  the official NUTS 2021 GeoJSON (EPSG:3857, ~70 MB, all levels)
Output: static/geo/nuts0.json (countries) and static/geo/nuts2.json (regions),
        simplified with the Douglas-Peucker algorithm and converted to lon/lat.

Usage: python scripts/build_boundaries.py path/to/nuts_2021.geojson
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

R = 6378137.0
OUT_DIR = Path(__file__).resolve().parent.parent / "static" / "geo"
TOLERANCE_M = {0: 2500, 2: 1500}  # simplification tolerance in metres per NUTS level
MIN_AREA_M2 = {0: 30e6, 2: 15e6}   # drop tiny islands below this area


def simplify(points, tol):
    """Iterative Douglas-Peucker on an (n, 2) array; keeps first and last point."""
    n = len(points)
    if n < 4:
        return points
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = points[i], points[j]
        seg = b - a
        seg_len = np.hypot(*seg)
        pts = points[i + 1:j]
        if seg_len == 0:
            d = np.hypot(*(pts - a).T)
        else:
            d = np.abs(seg[0] * (pts[:, 1] - a[1]) - seg[1] * (pts[:, 0] - a[0])) / seg_len
        k = int(np.argmax(d))
        if d[k] > tol:
            m = i + 1 + k
            keep[m] = True
            stack.append((i, m))
            stack.append((m, j))
    return points[keep]


def ring_area(pts):
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def to_lonlat(pts):
    lon = np.degrees(pts[:, 0] / R)
    lat = np.degrees(2 * np.arctan(np.exp(pts[:, 1] / R)) - math.pi / 2)
    return np.round(np.column_stack([lon, lat]), 4).tolist()


def process(geometry, level):
    polys = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    out = []
    for poly in polys:
        rings = []
        for idx, ring in enumerate(poly):
            pts = np.asarray(ring, dtype=float)
            if ring_area(pts) < MIN_AREA_M2[level]:
                if idx == 0:
                    break  # drop the whole polygon (tiny island)
                continue   # drop tiny hole
            s = simplify(pts, TOLERANCE_M[level])
            if len(s) >= 4:
                rings.append(to_lonlat(s))
        if rings:
            out.append(rings)
    if not out:
        return None
    return {"type": "MultiPolygon", "coordinates": out}


def main():
    geo = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for level, name in ((0, "nuts0"), (2, "nuts2")):
        features = []
        for f in geo["features"]:
            p = f["properties"]
            if p["LEVL_CODE"] != level:
                continue
            g = process(f["geometry"], level)
            if g:
                features.append({"type": "Feature", "properties": {"id": p["NUTS_ID"], "name": p["NUTS_NAME"]}, "geometry": g})
        out = OUT_DIR / f"{name}.json"
        out.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"{name}: {len(features)} features, {out.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
