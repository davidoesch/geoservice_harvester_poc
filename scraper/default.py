"""
Title: default scraper
Author: David Oesch
Date: 2022-11-05 (refactored 2026-11)
Purpose: Extract the metadata of one layer of an OGC service (WMS, WMTS or
    WFS, parsed by OWSLib) into a layer record.

A custom scraper for an owner can be placed next to this file as
<OWNER>.py (e.g. KT_XY.py) with the same scrape() signature.
"""

import math
import re
from urllib.parse import quote

from pyproj import Transformer

import ogc_utils

# WGS84 (lon/lat) -> Swiss LV95
TO_LV95 = Transformer.from_crs("EPSG:4326", "EPSG:2056", always_xy=True)

# map.geo.admin.ch zoom levels in LV95 (resolution in m/px for z = 0..13)
LV95_RESOLUTIONS = [650.0, 500.0, 250.0, 100.0, 50.0, 20.0, 10.0, 5.0, 2.5,
                    2.0, 1.0, 0.5, 0.25, 0.1]
SWISS_BBOX = (5.95, 45.81, 10.5, 47.81)
SWISS_CENTER_LV95 = (2660000, 1190000)

HTML_TAGS = re.compile("<.*?>")
FEDERAL_BUILTIN = re.compile(r"^https://(wms|wmts)\.geo\.admin\.ch/")


def remove_newline(toclean):
    """Remove newlines, tabs and HTML fragments from a string."""
    if not toclean:
        return ""
    text = re.sub(r"[\n\r\t\f\v]", " ", toclean)
    text = re.sub(HTML_TAGS, "", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def valid_bbox(bbox):
    """True for a finite, non-degenerate WGS84 bbox (w, s, e, n)."""
    try:
        w, s, e, n = (float(v) for v in bbox[:4])
    except (TypeError, ValueError, IndexError):
        return False
    return (all(math.isfinite(v) for v in (w, s, e, n))
            and -180 <= w <= e <= 180 and -90 <= s <= n <= 90)


def layer_bbox(layer):
    """WGS84 bbox (w, s, e, n) of a layer, or the Swiss extent."""
    bbox = getattr(layer, "boundingBoxWGS84", None)
    if bbox and valid_bbox(bbox):
        return tuple(float(v) for v in bbox[:4])
    # WFS 1.0.0: boundingBox = (minx, miny, maxx, maxy, crs)
    bbox = getattr(layer, "boundingBox", None)
    if bbox and len(bbox) >= 4:
        crs = str(bbox[4]) if len(bbox) > 4 else ""
        if ("4326" in crs or not crs) and valid_bbox(bbox):
            return tuple(float(v) for v in bbox[:4])
    return SWISS_BBOX


def lv95_view(bbox, width_px=800, height_px=600):
    """Center (E, N) and map.geo.admin.ch zoom level fitting a bbox."""
    try:
        xmin, ymin = TO_LV95.transform(bbox[0], bbox[1])
        xmax, ymax = TO_LV95.transform(bbox[2], bbox[3])
        if not all(math.isfinite(v) for v in (xmin, ymin, xmax, ymax)):
            raise ValueError("bbox outside LV95")
    except Exception:
        return SWISS_CENTER_LV95, 1
    center = (round((xmin + xmax) / 2), round((ymin + ymax) / 2))
    needed = max((xmax - xmin) / width_px, (ymax - ymin) / height_px, 0.1)
    zoom = 0
    for z, res in enumerate(LV95_RESOLUTIONS):
        if res >= needed:
            zoom = z
    return center, zoom


def encode_external(param):
    """Encode separators inside an external layer id (web-mapviewer)."""
    return (param.replace("|", "%7C").replace(",", "%2C")
            .replace(";", "%3B").replace("@", "%40"))


def mapgeo_link(prefix, layer_param, center, zoom):
    """Permalink to map.geo.admin.ch showing one layer."""
    return "%scenter=%d,%d&z=%d&layers=%s" % (
        prefix, center[0], center[1], zoom, quote(layer_param, safe=""))


def first_legend(styles):
    """Legend URL from an OWSLib styles dict."""
    if not styles:
        return ""
    if "default" in styles and isinstance(styles["default"], dict):
        return styles["default"].get("legend") or ""
    for style in styles.values():
        if isinstance(style, dict) and style.get("legend"):
            return style["legend"]
    return ""


def scrape(source, service, i, layertree, group, layer_data, prefix):
    """
    Extract the metadata of layer `i` of `service` into `layer_data`.

    Parameters:
        source (dict): sources.csv row plus "SERVICETYPE" (WMS|WMTS|WFS)
        service: OWSLib WebMapService / WebMapTileService /
            WebFeatureService
        i (str): layer name / identifier
        layertree (str): "<OWNER>/<service title>/<group>"
        group (str): name of the parent layer (WMS) or the layer itself
        layer_data (dict): empty layer record to fill
        prefix (str): map.geo.admin.ch permalink prefix

    Returns:
        dict: the filled layer record
    """
    layer = service.contents[i]
    stype = source.get("SERVICETYPE") or ogc_utils.guess_service_type(
        source["URL"])

    layer_data["OWNER"] = source["Description"]
    layer_data["TITLE"] = remove_newline(layer.title) or i
    layer_data["NAME"] = getattr(layer, "name", None) or \
        getattr(layer, "id", None) or i
    layer_data["TREE"] = layertree

    parent = getattr(layer, "parent", None)
    if parent is not None and getattr(parent, "name", None):
        layer_data["GROUP"] = parent.name
    else:
        layer_data["GROUP"] = group or ""

    layer_data["ABSTRACT"] = remove_newline(getattr(layer, "abstract", ""))

    keywords = [k.strip() for k in (getattr(layer, "keywords", None) or [])
                if k and k.strip()]
    layer_data["KEYWORDS"] = ", ".join(dict.fromkeys(keywords))

    legend = first_legend(getattr(layer, "styles", None))
    if not legend and getattr(layer, "_children", None):
        legend = first_legend(getattr(layer._children[0], "styles", None))
    layer_data["LEGEND"] = legend

    contact = ""
    provider = getattr(service, "provider", None)
    if provider is not None:
        c = getattr(provider, "contact", None)
        contact = (getattr(c, "email", None) if c else None) or \
            getattr(provider, "name", None) or ""
    layer_data["CONTACT"] = contact

    layer_data["SERVICELINK"] = ogc_utils.service_base_url(source["URL"]) \
        if stype != "WMTS" else ogc_utils.capabilities_url(source["URL"],
                                                           "WMTS")

    metadata = ""
    urls = getattr(layer, "metadataUrls", None) or []
    if urls and isinstance(urls[0], dict):
        metadata = urls[0].get("url") or ""
    if not metadata:
        metadata = getattr(service, "serviceMetadataURL", None) or ""
    layer_data["METADATA"] = metadata

    layer_data["UPDATE"] = ""
    layer_data["SERVICETYPE"] = stype

    bbox = layer_bbox(layer)
    layer_data["BBOX"] = " ".join(str(round(v, 5)) for v in bbox)
    layer_data["CENTER_LAT"] = round((bbox[1] + bbox[3]) / 2, 2)
    layer_data["CENTER_LON"] = round((bbox[0] + bbox[2]) / 2, 2)
    center, zoom = lv95_view(bbox)
    layer_data["MAX_ZOOM"] = zoom

    layer_id = layer_data["NAME"]
    # Layers of wms/wmts.geo.admin.ch are built into map.geo.admin.ch
    builtin = bool(FEDERAL_BUILTIN.match(layer_data["SERVICELINK"]))
    if stype == "WMS":
        if builtin:
            layer_param = layer_id
        else:
            layer_param = "WMS|%s|%s" % (
                encode_external(layer_data["SERVICELINK"]),
                encode_external(layer_id))
        layer_data["MAPGEO"] = mapgeo_link(prefix, layer_param, center, zoom)
    elif stype == "WMTS":
        if builtin:
            layer_param = layer_id
        else:
            layer_param = "WMTS|%s|%s" % (
                encode_external(layer_data["SERVICELINK"]),
                encode_external(layer_id))
        layer_data["MAPGEO"] = mapgeo_link(prefix, layer_param, center, zoom)
    else:
        # map.geo.admin.ch cannot display WFS
        layer_data["MAPGEO"] = ""
    return layer_data
