# -*- coding: utf-8 -*-
"""
Title: Build the web catalogue
Purpose: Turn data/geoservices_CH.csv (one row per service layer) into
    data/catalog.json, the compact search index used by index.html.

- Layers of the same owner offered by several services (WMS, WMTS, WFS) are
  merged into one dataset (at most one layer per service type).
- Each dataset knows its coverage region (canton, municipality, CH) so the
  web app can show where data exists and where it is missing. For
  geodienste.ch topics the cantons that actually publish data are taken from
  the geodienste.ch API.

Run after scraper.py:  python build_catalog.py
"""

import csv
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

import configuration as config

ABSTRACT_MAX = 320
FALLBACK_BBOXES = {(5.95, 45.81, 10.5, 47.81), (5.889, 45.785, 10.889, 47.785)}
TYPE_ORDER = {"WMS": 0, "WMTS": 1, "WFS": 2}


def norm_title(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def base_name(name):
    name = (name or "").split(":")[-1].lower()
    # Purely numeric names (ArcGIS "0", "1", ...) are not identifiers
    return name if len(name) > 3 and not name.isdigit() else None


def clean(value):
    value = (value or "").strip()
    return "" if value in ("n.a.", "n.a", "None") else value


def parse_bbox(text):
    try:
        bbox = tuple(round(float(v), 3) for v in text.split())
    except ValueError:
        return None
    if len(bbox) != 4 or bbox in FALLBACK_BBOXES:
        return None
    w, s, e, n = bbox
    # Ignore boxes that are clearly not about Switzerland (e.g. whole world)
    if e - w > 20 or n - s > 15 or e < 5 or w > 11 or n < 45 or s > 48.5:
        return None
    return list(bbox)


def geodienste_coverage():
    """Map geodienste.ch database names to the cantons publishing data."""
    try:
        r = requests.get("https://geodienste.ch/info/services.json",
                         params={"language": "de"}, timeout=120)
        r.raise_for_status()
    except Exception as e:
        print("geodienste.ch API not available (%s); assuming CH-wide" % e)
        return {}
    coverage = defaultdict(set)
    for svc in r.json()["services"]:
        free = "Frei erhältlich" in (svc.get("publication_wms") or "",
                                     svc.get("publication_data") or "")
        for url in (svc.get("getcapabilities_wms") or []) + \
                (svc.get("getcapabilities_wfs") or []):
            m = re.search(r"/db/([^/]+)/", url)
            if m:
                coverage[m.group(1)]  # make sure the key exists
                if free and svc.get("canton"):
                    coverage[m.group(1)].add(svc["canton"])
    return coverage


def main():
    with open(config.OWNERS_JSON, encoding="utf-8") as f:
        owner_info = json.load(f)
    with open(config.GEOSERVICES_CH_CSV, encoding="utf-8") as f:
        layers = list(csv.DictReader(f))
    layers.sort(key=lambda r: TYPE_ORDER.get(r["SERVICETYPE"], 9))
    gd_coverage = geodienste_coverage()

    owners, owner_index = [], {}
    services, service_index = [], {}
    datasets = []
    by_key = defaultdict(list)

    for row in layers:
        owner = row["OWNER"]
        stype = row["SERVICETYPE"]
        if stype not in TYPE_ORDER:
            continue
        if owner not in owner_index:
            owner_index[owner] = len(owners)
            info = owner_info.get(owner, {"kind": "other", "region": None,
                                          "label": {"de": owner}})
            owners.append(dict(info, code=owner))
        url = row["SERVICELINK"]
        skey = (stype, url)
        if skey not in service_index:
            service_index[skey] = len(services)
            services.append([stype, url])
        sidx = service_index[skey]

        title = clean(row["TITLE"]) or clean(row["NAME"])
        keys = [(owner, "t", norm_title(title))]
        bn = base_name(row["NAME"])
        if bn:
            keys.append((owner, "n", bn))

        target = None
        for key in keys:
            for ds in by_key[key]:
                if stype not in ds["types"]:
                    target = ds
                    break
            if target:
                break
        if target is None:
            target = {"o": owner_index[owner], "t": title,
                      "n": clean(row["NAME"]), "a": "", "k": [], "b": None,
                      "l": "", "m": "", "s": [], "g": "", "types": set(),
                      "r": None}
            datasets.append(target)
        for key in keys:
            if target not in by_key[key]:
                by_key[key].append(target)

        target["types"].add(stype)
        target["s"].append([sidx, clean(row["NAME"])])
        abstract = clean(row["ABSTRACT"])
        if len(abstract) > len(target["a"]):
            target["a"] = abstract
        for k in clean(row["KEYWORDS"]).split(","):
            k = k.strip()
            if k and k not in target["k"] and len(target["k"]) < 12:
                target["k"].append(k)
        if target["b"] is None:
            target["b"] = parse_bbox(row["BBOX"])
        target["l"] = target["l"] or clean(row["LEGEND"])
        target["m"] = target["m"] or clean(row["METADATA"])
        if not target["g"]:
            tree = clean(row["TREE"]).split("/")
            target["g"] = " / ".join(p for p in tree[1:] if p and p != title)[:120]
        if owner == "Geodienste" and target["r"] is None:
            m = re.search(r"/db/([^/]+)/", url)
            cantons = gd_coverage.get(m.group(1)) if m else None
            if cantons:
                target["r"] = sorted(cantons)

    # Repeated strings (legend / metadata URL templates, group paths) are
    # stored once in "strings"; "{L}" in a template stands for the layer name
    strings, string_index = [], {}

    def intern(value, layer_name=None):
        if not value:
            return -1
        if layer_name and len(layer_name) > 2 and layer_name in value:
            value = value.replace(layer_name, "{L}")
        if value not in string_index:
            string_index[value] = len(strings)
            strings.append(value)
        return string_index[value]

    out_ds = []
    for ds in datasets:
        abstract = ds["a"]
        if len(abstract) > ABSTRACT_MAX:
            abstract = abstract[:ABSTRACT_MAX].rsplit(" ", 1)[0] + " …"
        name = ds["s"][0][1]
        out_ds.append([ds["o"], ds["t"], abstract, ", ".join(ds["k"]),
                       ds["b"], intern(ds["l"], name), intern(ds["m"], name),
                       ds["s"], intern(ds["g"]), ds["r"]])

    # Per owner statistics for the "about / quality" section
    stats = defaultdict(lambda: {"layers": 0, "WMS": 0, "WMTS": 0, "WFS": 0,
                                 "abstract": 0, "keywords": 0, "metadata": 0,
                                 "contact": 0})
    for row in layers:
        s = stats[row["OWNER"]]
        s["layers"] += 1
        s[row["SERVICETYPE"]] = s.get(row["SERVICETYPE"], 0) + 1
        for field in ("abstract", "keywords", "metadata", "contact"):
            if clean(row[field.upper()]):
                s[field] += 1
    with open(config.SOURCE_COLLECTION_CSV, encoding="utf-8") as f:
        endpoints = defaultdict(int)
        for src in csv.DictReader(f):
            endpoints[src["Description"]] += 1
    for owner, s in stats.items():
        s["endpoints"] = endpoints.get(owner, 0)

    catalog = {
        "generated": datetime.now(ZoneInfo("Europe/Zurich")).isoformat(
            timespec="minutes"),
        "fields": ["owner", "title", "abstract", "keywords", "bbox",
                   "legend", "metadata", "services", "group", "regions"],
        "owners": owners,
        "services": services,
        "strings": strings,
        "datasets": out_ds,
        "stats": stats,
    }
    with open(config.CATALOG_JSON, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(",", ":"))
    print("Wrote %s: %d datasets, %d services, %d owners" % (
        config.CATALOG_JSON, len(out_ds), len(services), len(owners)))


if __name__ == "__main__":
    main()
