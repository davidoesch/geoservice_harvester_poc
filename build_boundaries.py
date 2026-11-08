# -*- coding: utf-8 -*-
"""
Build data/boundaries.json: simplified outlines (LV95 / EPSG:2056) of all
cantons, Liechtenstein and the municipalities that publish services, used by
the coverage map of the web application.

Only needs to be re-run when owners.json gets new municipalities.
Requires shapely >= 2.1 (not needed by the weekly pipeline).

Encoding: regions[code] is a list of polygons, each a list of rings (first
ring exterior, then holes). Coordinates are quantised to 10 m and every ring
is a flat list [x0, y0, dx1, dy1, ...] (first point absolute, then deltas).
"""

import json

import requests
import shapely
from shapely.geometry import shape

API = "https://api3.geo.admin.ch/rest/services/api/MapServer"
CANTON_LAYER = "ch.swisstopo.swissboundaries3d-kanton-flaeche.fill"
LAND_LAYER = "ch.swisstopo.swissboundaries3d-land-flaeche.fill"
MUNI_LAYER = "ch.swisstopo.swissboundaries3d-gemeinde-flaeche.fill"
Q = 10  # quantisation in metres


def feature(layer, fid):
    r = requests.get("%s/%s/%s" % (API, layer, fid), timeout=120,
                     params={"geometryFormat": "geojson", "sr": 2056})
    r.raise_for_status()
    return r.json()["feature"]


def municipality(name, canton):
    r = requests.get("%s/find" % API, timeout=120, params={
        "layer": MUNI_LAYER, "searchText": name, "searchField": "gemname",
        "contains": "false", "returnGeometry": "true",
        "geometryFormat": "geojson", "sr": 2056})
    r.raise_for_status()
    hits = [f for f in r.json()["results"]
            if f["properties"].get("kanton") == canton and
            f["properties"].get("is_current_jahr")]
    if not hits:
        raise ValueError("Municipality %s (%s) not found" % (name, canton))
    return hits[0]


def encode_ring(ring):
    pts = [(round(x / Q), round(y / Q)) for x, y in ring.coords]
    flat, prev = [], None
    for p in pts:
        if prev is None:
            flat += [p[0], p[1]]
        elif p != prev:
            flat += [p[0] - prev[0], p[1] - prev[1]]
        prev = p
    return flat if len(flat) >= 8 else None


def encode(geom):
    """
    Encode a (Multi)Polygon as a list of polygons, each a list of
    delta-encoded rings (first ring = exterior, further rings = holes).
    """
    polygons = []
    for poly in getattr(geom, "geoms", [geom]):
        if poly.is_empty or poly.area < 2e5:   # drop tiny islands (< 0.2 km2)
            continue
        rings = [encode_ring(poly.exterior)]
        rings += [encode_ring(r) for r in poly.interiors
                  if shapely.Polygon(r).area >= 2e5]
        rings = [r for r in rings if r]
        if rings:
            polygons.append(rings)
    return polygons


def main():
    with open("owners.json", encoding="utf-8") as f:
        owners = json.load(f)

    print("Cantons ...")
    cantons = {}
    for fid in range(1, 27):
        feat = feature(CANTON_LAYER, fid)
        cantons[feat["properties"]["ak"]] = shape(feat["geometry"])
    print("Liechtenstein / Switzerland ...")
    land = {k: shape(feature(LAND_LAYER, k)["geometry"]) for k in
            ("CH", "LI")}

    codes = list(cantons) + ["LI"]
    geoms = [cantons[c] for c in cantons] + [land["LI"]]
    # Topology-preserving simplification of the whole coverage (no gaps)
    simplified = shapely.coverage_simplify(geoms, tolerance=250)
    regions = {code: encode(g) for code, g in zip(codes, simplified)}
    regions["CH"] = encode(shapely.simplify(land["CH"], 250))

    print("Municipalities ...")
    for code, owner in owners.items():
        if owner.get("kind") != "city":
            continue
        geom = shape(municipality(owner["municipality"],
                                  owner["canton"])["geometry"])
        regions[owner["region"]] = encode(shapely.simplify(geom, 40))

    out = {"crs": "EPSG:2056", "quantisation": Q,
           "encoding": "polygons > rings > [x0,y0,dx,dy,...] * quantisation",
           "regions": regions}
    with open("data/boundaries.json", "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    print("Wrote data/boundaries.json with %d regions" % len(regions))


if __name__ == "__main__":
    main()
