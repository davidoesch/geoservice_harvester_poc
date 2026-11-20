# -*- coding: utf-8 -*-
"""
Title: Topic packages
Purpose: For every automatic topic of enrich.py (datasets of several
    providers about the same thing, e.g. "Bienenstandorte" of nine cantons)
    write static files that open all of them at once:

    data/topics/index.json      all topics with members, owners, links
    data/topics/<id>.qlr        QGIS layer definition (one group)
    data/topics/<id>.lyrx       ArcGIS Pro layer file
    data/topics/<id>.ows.json   OGC OWS Context (GeoJSON encoding)
    map.geo.admin.ch link       in index.json

GitHub Pages is static, so a topic is a bundle of the providers' services,
not one cascaded service. index.json can serve as the configuration of a
cascading server (e.g. QGIS Server) later.

Run after enrich.py and build_catalog.py:  python build_topics.py
"""

import copy
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from urllib.parse import quote
from xml.sax.saxutils import escape, quoteattr
from zoneinfo import ZoneInfo

from pyproj import Transformer

import build_catalog as bc
import configuration as config
import ogc_utils

sys.path.insert(0, config.SOURCE_SCRAPER_DIR)
import default as layer_tools  # noqa: E402  (scraper/default.py)

OUT_DIR = os.path.join("data", "topics")
SITE = config.SITE_URL + "data/topics/"
TO_LV95 = Transformer.from_crs("EPSG:4326", "EPSG:2056", always_xy=True)
CH_EXTENT = (2485000, 1075000, 2834000, 1296000)

SRS_2056 = (
    "<srs><spatialrefsys><proj4>+proj=somerc +lat_0=46.9524055555556 "
    "+lon_0=7.43958333333333 +k_0=1 +x_0=2600000 +y_0=1200000 +ellps=bessel "
    "+towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs</proj4>"
    "<srid>2056</srid><authid>EPSG:2056</authid>"
    "<description>CH1903+ / LV95</description>"
    "<projectionacronym>somerc</projectionacronym>"
    "<ellipsoidacronym>EPSG:7004</ellipsoidacronym>"
    "<geographicflag>false</geographicflag></spatialrefsys></srs>")


def pick_service(members_services, order=("WMS", "WMTS", "WFS")):
    for t in order:
        for svc in members_services:
            if svc["type"] == t:
                return svc
    return None


# ------------------------------------------------------------ WMTS details

_wmts_cache = {}


def wmts_info(url, layer):
    """Matrix set, style, format and CRS of a WMTS layer (from capabilities)."""
    if url not in _wmts_cache:
        cap = ogc_utils.fetch_capabilities(url, "WMTS", timeout=60)
        _wmts_cache[url] = ET.fromstring(cap["xml"]) if cap["ok"] else None
    root = _wmts_cache[url]
    info = {"matrixSet": "", "style": "default", "format": "image/png",
            "crs": "EPSG:2056"}
    if root is None:
        return info
    local = lambda el: el.tag.rsplit("}", 1)[-1]  # noqa: E731
    sets = {}
    for tms in root.iter():
        if local(tms) == "TileMatrixSet":
            ident = crs = None
            for ch in tms:
                if local(ch) == "Identifier":
                    ident = (ch.text or "").strip()
                elif local(ch) == "SupportedCRS":
                    crs = (ch.text or "").strip()
            if ident and crs:
                sets[ident] = crs
    for lyr in root.iter():
        if local(lyr) != "Layer":
            continue
        ident = next((c.text for c in lyr if local(c) == "Identifier"), None)
        if ident != layer:
            continue
        links = [t.text for c in lyr if local(c) == "TileMatrixSetLink"
                 for t in c if local(t) == "TileMatrixSet"]
        for want in ("2056", "3857", "900913"):
            hit = [l for l in links if want in sets.get(l, "")]
            if hit:
                info["matrixSet"] = hit[0]
                break
        else:
            info["matrixSet"] = links[0] if links else ""
        code = re.search(r"(\d{4,6})\s*$", sets.get(info["matrixSet"], ""))
        if code:
            info["crs"] = "EPSG:" + ("3857" if code.group(1) == "900913"
                                     else code.group(1))
        styles = [c for c in lyr if local(c) == "Style"]
        default = [s for s in styles if s.get("isDefault") == "true"] or styles
        if default:
            info["style"] = next((c.text for c in default[0]
                                  if local(c) == "Identifier"), "default")
        fmt = next((c.text for c in lyr if local(c) == "Format"), None)
        info["format"] = fmt or info["format"]
        break
    return info


# --------------------------------------------------------------- exporters

def lv95_extent(bbox):
    if not bbox:
        return CH_EXTENT
    x1, y1 = TO_LV95.transform(bbox[0], bbox[1])
    x2, y2 = TO_LV95.transform(bbox[2], bbox[3])
    return (round(x1), round(y1), round(x2), round(y2))


def qgis_value(value):
    """
    Value inside a QGIS WMS/WMTS data source string. QGIS expects layer
    names unencoded (e.g. "workspace:layer"); only "&" would break the
    string.
    """
    return str(value).replace("&", "%26")


def qlr(topic_label, items):
    tree, layers = [], []
    for n, it in enumerate(items):
        svc = it["service"]
        lid = "geoharvester_%s_%d" % (it["topic"], n)
        url = quote(svc["url"], safe="") if "&" in svc["url"] else svc["url"]
        kind, provider, crs = "raster", "wms", "EPSG:2056"
        if svc["type"] == "WMS":
            source = ("contextualWMSLegend=0&crs=EPSG:2056&dpiMode=7"
                      "&featureCount=10&format=image/png&layers=%s&styles"
                      "&url=%s" % (qgis_value(svc["layer"]), url))
        elif svc["type"] == "WMTS":
            info = wmts_info(svc["url"], svc["layer"])
            crs = info["crs"]
            source = ("contextualWMSLegend=0&crs=%s&dpiMode=7&featureCount=10"
                      "&format=%s&layers=%s&styles=%s&tileMatrixSet=%s&url=%s"
                      % (crs, info["format"], qgis_value(svc["layer"]),
                         qgis_value(info["style"]),
                         qgis_value(info["matrixSet"]), url))
        else:
            kind, provider = "vector", "WFS"
            source = (" pagingEnabled='true' preferCoordinatesForWfsT11='false'"
                      " restrictToRequestBBOX='1' srsname='EPSG:2056' "
                      "typename='%s' url='%s' version='auto'"
                      % (svc["layer"], svc["url"]))
        e = lv95_extent(it["bbox"])
        name = "%s (%s)" % (it["title"], it["owner_short"])
        srs = SRS_2056 if crs == "EPSG:2056" else \
            "<srs><spatialrefsys><authid>%s</authid></spatialrefsys></srs>" % crs
        tree.append('      <layer-tree-layer expanded="0" checked="Qt::Checked" '
                    'id=%s name=%s source=%s providerKey="%s"/>'
                    % (quoteattr(lid), quoteattr(name), quoteattr(source),
                       provider))
        layers.append(
            '    <maplayer type="%s" hasScaleBasedVisibilityFlag="0" '
            'minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories">'
            "\n      <extent><xmin>%d</xmin><ymin>%d</ymin><xmax>%d</xmax>"
            "<ymax>%d</ymax></extent>\n      <id>%s</id>\n      <datasource>%s"
            "</datasource>\n      <layername>%s</layername>\n      %s\n"
            "      <provider>%s</provider>\n    </maplayer>"
            % (kind, e[0], e[1], e[2], e[3], escape(lid), escape(source),
               escape(name), srs, provider))
    return ("<!DOCTYPE qgis-layer-definition>\n<qlr>\n"
            '  <layer-tree-group expanded="1" checked="Qt::Checked" name="">\n'
            '    <layer-tree-group expanded="1" checked="Qt::Checked" name=%s>\n'
            "%s\n    </layer-tree-group>\n  </layer-tree-group>\n"
            "  <maplayers>\n%s\n  </maplayers>\n</qlr>\n"
            % (quoteattr("GeoHarvester – " + topic_label), "\n".join(tree),
               "\n".join(layers)))


_templates = {}


def lyrx(items):
    doc, defs = None, []
    for n, it in enumerate(items):
        svc = it["service"]
        t = svc["type"].lower()
        if t not in _templates:
            with open(os.path.join("templates", "arcgispro_%s_template.lyrx" % t),
                      encoding="utf-8") as f:
                _templates[t] = f.read()
        js = lambda v: json.dumps(str(v))[1:-1]  # noqa: E731
        name = "%s (%s)" % (it["title"], it["owner_short"])
        url = ogc_utils.capabilities_url(svc["url"], "WMTS") \
            if svc["type"] == "WMTS" else svc["url"]
        text = (_templates[t].replace("{{NAME}}", js(svc["layer"]))
                .replace("{{TITLE}}", js(name))
                .replace("{{SERVICELINK}}", js(url))
                .replace("{{OWNER}}", js(it["owner"])))
        parsed = json.loads(text)
        d = parsed["layerDefinitions"][0]
        d["name"] = name
        d["uRI"] = "CIMPATH=geoharvester/layer_%d.json" % n
        if svc["type"] == "WMTS":
            info = wmts_info(svc["url"], svc["layer"])
            d["serviceConnection"]["style"] = info["style"]
            d["serviceConnection"]["imageFormat"] = info["format"]
            if info["matrixSet"]:
                d["serviceConnection"]["tileMatrixSet"] = info["matrixSet"]
        defs.append(d)
        doc = doc or copy.deepcopy(parsed)
    if doc is None:
        return None
    doc["layers"] = [d["uRI"] for d in defs]
    doc["layerDefinitions"] = defs
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":"))


def owc(topic_id, label, items, updated):
    feats = []
    for it in items:
        svc = it["service"]
        b = it["bbox"]
        geom = None
        if b:
            geom = {"type": "Polygon", "coordinates": [[
                [b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]],
                [b[0], b[1]]]]}
        cap = ogc_utils.capabilities_url(svc["url"], svc["type"])
        offering = {"code": "http://www.opengis.net/spec/owc-geojson/1.0/req/%s"
                    % svc["type"].lower(),
                    "operations": [{"code": "GetCapabilities", "method": "GET",
                                    "type": "application/xml", "href": cap}]}
        feats.append({
            "type": "Feature",
            "id": "%s#%s" % (svc["url"], svc["layer"]),
            "geometry": geom,
            "properties": {"title": it["title"], "updated": updated,
                           "publisher": it["owner_label"],
                           "layer": svc["layer"],
                           "offerings": [offering]}})
    return json.dumps({
        "type": "FeatureCollection",
        "id": SITE + topic_id + ".ows.json",
        "properties": {
            "lang": "de", "title": label, "updated": updated,
            "subtitle": "GeoHarvester topic: %d providers" % len(items),
            "links": {"profiles": [{"href": "http://www.opengis.net/spec/"
                                    "owc-geojson/1.0/req/core"}]}},
        "features": feats}, ensure_ascii=False, indent=1)


def write_if_changed(path, text, ignore=None):
    """
    Write a file only if its content changed (optionally ignoring a pattern
    such as a timestamp), so the weekly run does not rewrite unchanged
    topic packages and bloat the git history.
    """
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
        strip = (lambda t: re.sub(ignore, "", t)) if ignore else (lambda t: t)
        if strip(old) == strip(text):
            return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def mapgeo_link(items):
    parts, used = [], []
    for it in items:
        svc = it["service"]
        if svc["type"] not in ("WMS", "WMTS"):
            continue
        if layer_tools.FEDERAL_BUILTIN.match(svc["url"]):
            layer_id = layer_tools.encode_external(svc["layer"])
        else:
            url = ogc_utils.capabilities_url(svc["url"], "WMTS") \
                if svc["type"] == "WMTS" else svc["url"]
            layer_id = "%s|%s|%s" % (svc["type"],
                                     layer_tools.encode_external(url),
                                     layer_tools.encode_external(svc["layer"]))
        parts.append(layer_id + ",t,0.85")
        used.append(it["bbox"])
    if not parts:
        return None
    boxes = [b for b in used if b]
    bbox = (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)) if boxes \
        else layer_tools.SWISS_BBOX
    center, zoom = layer_tools.lv95_view(bbox, 1100, 700)
    return ("https://map.geo.admin.ch/#/map?lang=de&center=%d,%d&z=%d"
            "&bgLayer=ch.swisstopo.pixelkarte-grau&layers=%s"
            % (center[0], center[1], zoom, quote(";".join(parts), safe="")))


# -------------------------------------------------------------------- main

def main():
    with open(config.OWNERS_JSON, encoding="utf-8") as f:
        owner_info = json.load(f)
    owners, services, datasets = bc.merge_datasets(bc.load_layers(),
                                                   owner_info)
    by_key = {bc.dataset_key(ds, owners, services): ds for ds in datasets}

    topics = defaultdict(lambda: {"label": "", "members": []})
    with open(os.path.join("data", "enrichment.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["TOPIC_ID"] and row["DATASET_KEY"] in by_key:
                t = topics[row["TOPIC_ID"]]
                t["label"] = row["TOPIC_LABEL"]
                t["members"].append(by_key[row["DATASET_KEY"]])

    os.makedirs(OUT_DIR, exist_ok=True)
    written = set()
    changed = 0
    updated = datetime.now(ZoneInfo("Europe/Zurich")).isoformat(
        timespec="seconds")
    index = []
    for tid in sorted(topics):
        t = topics[tid]
        items = []
        for ds in sorted(t["members"], key=lambda d: owners[d["o"]]["code"]):
            svcs = [{"type": services[s][0], "url": services[s][1],
                     "layer": layer} for s, layer in ds["s"]]
            svc = pick_service(svcs)
            o = owners[ds["o"]]
            items.append({
                "topic": tid, "title": ds["t"], "bbox": ds["b"],
                "service": svc, "owner": o["code"],
                "owner_label": (o.get("label") or {}).get("de", o["code"]),
                "owner_short": o.get("region") if o.get("kind") == "canton"
                else o.get("municipality") or o["code"],
                "key": bc.dataset_key(ds, owners, services)})
        files = {}
        outputs = [("qlr", ".qlr", qlr(t["label"], items), None),
                   ("lyrx", ".lyrx", lyrx(items), None),
                   ("owc", ".ows.json", owc(tid, t["label"], items, updated),
                    r'"updated": "[^"]*"')]
        for key, ext, text, ignore in outputs:
            if not text:
                continue
            name = tid + ext
            changed += write_if_changed(os.path.join(OUT_DIR, name), text,
                                        ignore)
            written.add(name)
            files[key] = SITE + name
        index.append({
            "id": tid, "label": t["label"],
            "owners": [it["owner"] for it in items],
            "members": [{"key": it["key"], "title": it["title"],
                         "owner": it["owner"], "service": it["service"]}
                        for it in items],
            "mapgeo": mapgeo_link(items), **files})
    # remove packages of topics that no longer exist
    removed = 0
    for name in os.listdir(OUT_DIR):
        if name != "index.json" and name not in written:
            os.remove(os.path.join(OUT_DIR, name))
            removed += 1
    write_if_changed(os.path.join(OUT_DIR, "index.json"),
                     json.dumps({"generated": updated, "topics": index},
                                ensure_ascii=False, indent=1),
                     r'"generated": "[^"]*"')
    print("%d topic packages in %s: %d files written, %d removed" % (
        len(index), OUT_DIR, changed, removed))


if __name__ == "__main__":
    main()
