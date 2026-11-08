# -*- coding: utf-8 -*-
"""
Title: Source discovery for the Geoservice Harvester
Purpose: Find WMS / WMTS / WFS endpoints of Swiss public authorities, validate
    them and (re)write sources.csv.

Sources of candidate endpoints
- sources.csv itself (curated entries are always re-validated)
- opendata.swiss (CKAN API, all resources of format WMS / WFS / WMTS)
- geocat.ch (national metadata catalogue: service links of all ~21k
  records, recognised by protocol or URL pattern; ArcGIS REST links are
  converted to their WMS/WFS endpoints)
- geodienste.ch (official list of intercantonal services)
- the sources.csv of the FHNW Geoharvester project
  (https://github.com/FHNW-IGEO/Geoharvester)
- ArcGIS Server REST catalogues of cantonal and municipal portals
- a small list of manually researched endpoints (MANUAL_SOURCES)

Every candidate is validated with a real GetCapabilities request. Only
endpoints that return a valid WMS, WMTS or WFS capabilities document end up
in sources.csv. A full report of all candidates is written to
tools/sources_report.csv.

Usage
    python discover_sources.py            # update sources.csv
    python discover_sources.py --dry-run  # only write the report
    python discover_sources.py --keep-invalid  # keep failing curated entries
"""

import argparse
import csv
import logging
import math
import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qsl, urlsplit

import requests

import configuration as config
import ogc_utils

log = logging.getLogger("discover")

REPORT_FILE = os.path.join("tools", "sources_report.csv")

# --------------------------------------------------------------------------
# Owner mapping
# --------------------------------------------------------------------------

# opendata.swiss organisation -> OWNER code
ODS_ORGANISATIONS = {
    "agis_service_center": "KT_AG",
    "kanton-basel-stadt": "KT_BS",
    "geoinformation_kanton_freiburg": "KT_FR",
    "canton-geneve": "KT_GE",
    "geneve-aeroport": "KT_GE", "hes-so-geneve": "KT_GE", "tpg": "KT_GE",
    "imad-ge": "KT_GE", "services-industriels-geneve": "KT_GE",
    "chancellerie-etat-geneve": "KT_GE", "fti-ge": "KT_GE", "cern": "KT_GE",
    "fachstelle-geoinformation-des-kantons-glarus": "KT_GL",
    "geoinformation-kt-gr": "KT_GR",
    "canton-du-jura": "KT_JU",
    "amt-fuer-raumentwicklung-und-geoinformation-areg-kanton-st-gallen":
        "KT_SG",
    "amt-geoinformation-kanton-schaffhausen": "KT_SH",
    "amt-geoinformation-sz": "KT_SZ",
    "kanton-thurgau": "KT_TG",
    "geoinformation-kanton-uri": "KT_UR",
    "canton-du-valais-cc-geo": "KT_VS",
    "kanton-zug": "KT_ZG",
    "geoinformation-kanton-zuerich": "KT_ZH",
    "amt-fuer-tiefbau-und-geoinformation-fl": "FL_LI",
    "stadt-zurich": "CITY_Zuerich",
    "geoinformation-der-stadt-bern": "CITY_Bern",
    "stadt-luzern": "CITY_Luzern",
    "stadt-winterthur": "CITY_Winterthur",
    "stadt-zug": "CITY_Zug",
    "ville-geneve": "CITY_Geneve",
    "gemeinde_emmen": "CITY_Emmen",
    "dienstzweig-geomatik-gemeinde-koeniz": "CITY_Koeniz",
    "planung-umwelt-biel-bienne": "CITY_Biel",
}
ODS_FEDERAL_PREFIXES = ("bundesamt-", "staatssekretariat-", "gruppe-",
                        "bundeskanzlei", "eidgenoessische-")

# Host (optionally host/path-prefix) -> OWNER code. Used for catalogue
# entries without a usable organisation (geocat.ch, ArcGIS catalogues).
HOST_OWNERS = [
    ("www.gis-daten.ch/wms/nw", "KT_NW"),
    ("www.gis-daten.ch/wms/ow", "KT_OW"),
    ("public.geo.lu.ch", "KT_LU"),
    ("sitn.ne.ch", "KT_NE"),
    ("vector.sitg.ge.ch", "KT_GE"), ("raster.sitg.ge.ch", "KT_GE"),
    ("app2.ge.ch", "KT_GE"),
    ("wms.geo.ag.ch", "KT_AG"),
    ("map.bern.ch", "CITY_Bern"),
    ("ows.geo.tg.ch", "KT_TG"), ("ows-raster.geo.tg.ch", "KT_TG"),
    ("maps.fr.ch", "KT_FR"),
    ("map.stadtluzern.ch", "CITY_Luzern"),
    ("services.geo.zg.ch", "KT_ZG"), ("go.geodatenonline.ch", "KT_ZG"),
    ("ows.geodatenonline.ch", "CITY_Zug"),
    ("wms.zh.ch", "KT_ZH"), ("maps.zh.ch", "KT_ZH"),
    ("services.geo.sg.ch", "KT_SG"),
    ("www.geoservice.apps.be.ch", "KT_BE"),
    ("stadtplan.winterthur.ch", "CITY_Winterthur"),
    ("www.ogd.stadt-zuerich.ch", "CITY_Zuerich"),
    ("www.ogc.stadt-zuerich.ch", "CITY_Zuerich"),
    ("tile.osm.ch", "SOSM"),
    ("wms.geo.gr.ch", "KT_GR"), ("wfs.geo.gr.ch", "KT_GR"),
    ("sit.vs.ch", "KT_VS"),
    ("service.geo.llv.li", "FL_LI"), ("geoservices.llv.li", "FL_LI"),
    ("geoportal.koeniz.ch", "CITY_Koeniz"),
    ("geo.ur.ch", "KT_UR"),
    ("map.geo.sz.ch", "KT_SZ"), ("wfs.geo.sz.ch", "KT_SZ"),
    ("www.sigip.ch", "CITY_Pully"),
    ("wms.geo.sh.ch", "KT_SH"), ("wfs.geo.sh.ch", "KT_SH"),
    ("gis.gict.ch/ows/emmen", "CITY_Emmen"),
    ("wms.asit-asso.ch/fonds-asit", "KT_VD"), ("wmts.asit-asso.ch", "KT_VD"),
    ("www.ogc.vd.ch", "KT_VD"),
    ("wms.geo.bs.ch", "KT_BS"), ("wfs.geo.bs.ch", "KT_BS"),
    ("wmts.geo.bs.ch", "KT_BS"),
    ("biel-bienne.mapplus.ch", "CITY_Biel"),
    ("geoservices.jura.ch", "KT_JU"), ("geo.jura.ch", "KT_JU"),
    ("map.geo.gl.ch", "KT_GL"), ("wms.geo.gl.ch", "KT_GL"),
    ("wfs.geo.gl.ch", "KT_GL"),
    ("www.gis-service.ch", "Bund"),
    ("map.lausanne.ch", "CITY_Lausanne"),
    ("geowms.bl.ch", "KT_BL"), ("tile.geoview.bl.ch", "KT_BL"),
    ("geodienste.ch", "Geodienste"),
]

# Endpoints that are ignored: covered elsewhere, duplicates or out of scope
SKIP_PATTERNS = [
    "wms.geo.admin.ch",            # "Bund" has the main endpoints
    "wmts.geo.admin.ch",
    "wfs.geodienste.ch",           # legacy alias of geodienste.ch
    "wms.geo.ag.ch/public/ch_ag_",  # per-layer copies of the AG main WMS
    "portailsig.atmo-grandest.eu",  # foreign / cross-border
    "geoportal.georhena.eu",
    "geodatasolutions.ch", "gishosting.ch",  # private OSM services
    "wms.asit-asso.ch/swisscom",
    "map.cjl.ch",
    ".csv",
    "_fr_ms_wms/", "_fr_ms_wfs/",  # Bern: French copies of the DE services
]

# ArcGIS Server REST catalogues to crawl: (owner, rest_root, folder, filter)
ARCGIS_CATALOGUES = [
    ("KT_LU", "https://public.geo.lu.ch/ogd", "managed", None),
    ("KT_LU", "https://public.geo.lu.ch/ogd", "basis", None),
    ("KT_FR", "https://maps.fr.ch/ags", "OpenData", None),
    ("KT_FR", "https://maps.fr.ch/ags", "OpenData_Raster", None),
    ("KT_VS", "https://sit.vs.ch/arcgis", "", lambda n: "TEST" not in n),
    ("KT_GE", "https://vector.sitg.ge.ch/arcgis", "", None),
    ("CITY_Bern", "https://map.bern.ch/arcgis", "Geoportal", None),
    ("CITY_Luzern", "https://map.stadtluzern.ch/server", "OGD", None),
    ("KT_BE", "https://www.geoservice.apps.be.ch/geoservice3", "a42geo",
     lambda n: n.startswith("of_") and "_de_" in n),
]

# Manually researched endpoints (owner, url)
MANUAL_SOURCES = [
    # Neuchâtel (SITN) - https://sitn.ne.ch/services/docs/api/WMS/
    ("KT_NE", "https://sitn.ne.ch/services/wms?SERVICE=WMS&REQUEST=GetCapabilities"),
    ("KT_NE", "https://sitn.ne.ch/services/wmts?SERVICE=WMTS&REQUEST=GetCapabilities"),
    ("KT_NE", "https://sitn.ne.ch/ogc-sitn-climat/wms?SERVICE=WMS&REQUEST=GetCapabilities"),
    # Luzern basemap WMTS - https://geoportal.lu.ch/geodaten/geodienste
    ("KT_LU", "https://public.geo.lu.ch/ogd/rest/services/managed/OF23HI08_DS_V1_IM/ImageServer/WMTS/1.0.0/WMTSCapabilities.xml"),
    # Nidwalden / Obwalden (GIS Daten AG)
    ("KT_NW", "https://www.gis-daten.ch/wms/nw/service?SERVICE=WMS&REQUEST=GetCapabilities"),
    ("KT_OW", "https://www.gis-daten.ch/wms/ow/service?SERVICE=WMS&REQUEST=GetCapabilities"),
    # Jura (new GeoServer endpoint)
    ("KT_JU", "https://geoservices.jura.ch/wms?SERVICE=WMS&REQUEST=GetCapabilities"),
    ("KT_JU", "https://geoservices.jura.ch/wfs?SERVICE=WFS&REQUEST=GetCapabilities"),
    # Zug overview plan WMTS
    ("KT_ZG", "https://services.geo.zg.ch/tc/wmts/1.0.0/WMTSCapabilities.xml"),
    # Vaud raster WMS
    ("KT_VD", "https://www.ogc.vd.ch/raster/services/OGC/wmsVD/Mapserver/WMSServer?SERVICE=WMS&REQUEST=GetCapabilities"),
    # Basel-Landschaft WFS, Glarus WFS
    ("KT_BL", "https://geowms.bl.ch/?SERVICE=WFS&REQUEST=GetCapabilities"),
    ("KT_GL", "https://map.geo.gl.ch/ows/mainmap?SERVICE=WFS&REQUEST=GetCapabilities"),
    # Stadt Lausanne (GeoMapFish)
    ("CITY_Lausanne", "https://map.lausanne.ch/mapserv_proxy?ogcserver=source+for+image%2Fpng&SERVICE=WMS&REQUEST=GetCapabilities"),
    # Liechtenstein
    ("FL_LI", "https://service.geo.llv.li/wmsli/service?SERVICE=WMS&REQUEST=GetCapabilities"),
    ("FL_LI", "https://geoservices.llv.li/oerebli/service?SERVICE=WMS&REQUEST=GetCapabilities"),
]


def owner_for_url(url):
    parts = urlsplit(url)
    hostpath = (parts.netloc + parts.path).lower()
    for prefix, owner in HOST_OWNERS:
        if hostpath.startswith(prefix.lower()):
            return owner
    return None


def is_skipped(url):
    low = url.lower()
    return any(p in low for p in SKIP_PATTERNS)


def unwrap_url(url):
    """Unwrap viewer links such as katalog.geo.gr.ch/geoviewer?url=..."""
    parts = urlsplit(url)
    if "geoviewer" in parts.path:
        inner = dict(parse_qsl(parts.query)).get("url")
        if inner:
            return inner if inner.startswith("http") else "https://" + inner
    return url


# --------------------------------------------------------------------------
# Collectors. Each returns a list of (owner, service_type, url, origin).
# --------------------------------------------------------------------------

def collect_existing():
    out = []
    with open(config.SOURCE_COLLECTION_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = row["URL"].strip()
            if url:
                out.append((row["Description"].strip(), None, url,
                            "sources.csv"))
    return out


def collect_opendata_swiss():
    api = "https://ckan.opendata.swiss/api/3/action/package_search"
    out, start = [], 0
    while True:
        # opendata.swiss rejects some clients; the plain python-requests
        # client is accepted.
        r = requests.get(api, params={
            "fq": "res_format:(WMS OR WFS OR WMTS)", "rows": 1000,
            "start": start}, timeout=120)
        r.raise_for_status()
        result = r.json()["result"]
        for pkg in result["results"]:
            org = (pkg.get("organization") or {}).get("name", "")
            for res in pkg.get("resources", []):
                fmt = (res.get("format") or "").upper()
                url = (res.get("url") or "").strip()
                if fmt not in ogc_utils.SERVICE_TYPES or \
                        not url.startswith("http"):
                    continue
                url = unwrap_url(url)
                owner = ODS_ORGANISATIONS.get(org)
                if owner is None and org.startswith(ODS_FEDERAL_PREFIXES):
                    owner = "Bund"
                owner = owner_for_url(url) if owner is None else owner
                if org == "ville-geneve":
                    owner = "CITY_Geneve"
                if owner:
                    out.append((owner, fmt, url, "opendata.swiss"))
                else:
                    log.info("opendata.swiss: unmapped organisation %s (%s)",
                             org, url)
        start += 1000
        if start >= result["count"]:
            break
    return out


GEOCAT_API = "https://www.geocat.ch/geonetwork/srv/api/search/records/_search"
SERVICE_URL = re.compile(
    r"(service=(wms|wfs|wmts))|wmtscapabilities\.xml|/(wms|wfs)server|"
    r"/(wms|wfs|wmts|ows)(\?|/|$)|mapserv", re.I)
ARCGIS_REST = re.compile(
    r"^(https?://[^?#]+?)/rest/services/(.+?)/(MapServer|ImageServer)\b", re.I)
# Hosts in geocat.ch that are covered elsewhere or out of scope
GEOCAT_SKIP_HOSTS = ("api3.geo.admin.ch", "map.geo.admin.ch", "lgrb-bw.de",
                     "georhena.eu")


def service_candidates(url, protocol=""):
    """
    Turn a catalogue link into (service_type, url) candidates. ArcGIS REST
    links (.../rest/services/X/MapServer) become WMS and WFS endpoints;
    GetMap / GetLegendGraphic requests are reduced to the service URL.
    """
    m = ARCGIS_REST.match(url)
    if m:
        base = "%s/services/%s/%s" % m.groups()
        out = [("WMS", base + "/WMSServer")]
        if m.group(3).lower() == "mapserver":
            out.append(("WFS", base + "/WFSServer"))
        return out
    proto = protocol.upper()
    if not (SERVICE_URL.search(url) or
            any(k in proto for k in ("WMS", "WFS", "WMTS"))):
        return []
    url = ogc_utils.service_base_url(url) \
        if re.search(r"request=(getmap|getlegendgraphic|getfeature)", url, re.I) \
        else url
    low = url.lower()
    if "WMTS" in proto or "wmts" in low:
        stype = "WMTS"
    elif "WFS" in proto or "/wfs" in low or "service=wfs" in low:
        stype = "WFS"
    else:
        stype = "WMS"
    return [(stype, url)]


def collect_geocat():
    """All service links of all geocat.ch records (paged with search_after)."""
    out, after = [], None
    while True:
        query = {"size": 1000, "_source": ["link"], "sort": [{"uuid": "asc"}],
                 "query": {"match_all": {}}}
        if after:
            query["search_after"] = after
        r = requests.post(GEOCAT_API, json=query, timeout=120,
                          headers={"Accept": "application/json"})
        r.raise_for_status()
        hits = r.json()["hits"]["hits"]
        if not hits:
            break
        after = hits[-1]["sort"]
        for hit in hits:
            for link in hit["_source"].get("link") or []:
                url = ((link.get("urlObject") or {}).get("default") or "").strip()
                if not url.startswith("http"):
                    continue
                url = unwrap_url(url)
                host = urlsplit(url).netloc.lower()
                if any(h in host for h in GEOCAT_SKIP_HOSTS):
                    continue
                for stype, cand in service_candidates(
                        url, link.get("protocol") or ""):
                    owner = owner_for_url(cand)
                    if owner:
                        out.append((owner, stype, cand, "geocat.ch"))
    return out


FHNW_SOURCES = ("https://raw.githubusercontent.com/FHNW-IGEO/Geoharvester/"
                "main/scraper/sources.csv")
FHNW_OWNERS = {"ST_ZH": "CITY_Zuerich", "ST_BE": "CITY_Bern",
               "ASIT": "KT_VD", "SOSM": "SOSM"}


def collect_fhnw():
    """Endpoints of the FHNW Geoharvester project."""
    r = requests.get(FHNW_SOURCES, timeout=120)
    r.raise_for_status()
    out = []
    for row in csv.DictReader(r.text.splitlines()):
        url = (row.get("URL") or "").strip()
        owner = (row.get("Description") or "").strip()
        owner = FHNW_OWNERS.get(owner, owner)
        if url.startswith("http") and owner:
            out.append((owner, None, url, "fhnw"))
    return out


def collect_geodienste():
    r = requests.get("https://geodienste.ch/info/services.json",
                     params={"language": "de"}, timeout=120)
    r.raise_for_status()
    out = []
    for svc in r.json()["services"]:
        for key, stype in (("getcapabilities_wms", "WMS"),
                           ("getcapabilities_wfs", "WFS")):
            for url in svc.get(key) or []:
                out.append(("Geodienste", stype, url, "geodienste.ch"))
    return out


def collect_arcgis():
    out = []
    for owner, root, folder, name_filter in ARCGIS_CATALOGUES:
        rest = "%s/rest/services%s" % (root, "/" + folder if folder else "")
        try:
            services = ogc_utils.session().get(
                rest, params={"f": "json"}, timeout=60).json()["services"]
        except Exception as e:
            log.warning("ArcGIS catalogue %s failed: %s", rest, e)
            continue
        for svc in services:
            name, stype = svc["name"], svc["type"]
            short = name.split("/")[-1]
            if name_filter and not name_filter(short):
                continue
            if stype == "MapServer":
                base = "%s/services/%s/MapServer" % (root, name)
                out.append((owner, "WMS", base + "/WMSServer", "arcgis"))
                out.append((owner, "WFS", base + "/WFSServer", "arcgis"))
            elif stype == "ImageServer":
                base = "%s/services/%s/ImageServer" % (root, name)
                out.append((owner, "WMS", base + "/WMSServer", "arcgis"))
    return out


def collect_manual():
    return [(o, None, u, "manual") for o, u in MANUAL_SOURCES]


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def validate_group(candidates):
    """Validate candidates sequentially (they share one host)."""
    results = []
    for cand in candidates:
        cap = ogc_utils.fetch_capabilities(cand["url"], cand["type"],
                                           timeout=45)
        cand = dict(cand)
        cand["valid"] = cap["ok"]
        cand["detected"] = cap["type"] or ""
        cand["error"] = cap["error"] or ""
        cand["title"] = cap["title"] or ""
        cand["fingerprint"] = cap.get("fingerprint")
        if cap["ok"]:
            cand["type"] = cap["type"]
            cand["url"] = ogc_utils.capabilities_url(cand["url"], cap["type"])
        results.append(cand)
    return results


def validate(candidates, workers=16, per_host=3):
    """Validate in parallel, with at most `per_host` workers per host."""
    by_host = defaultdict(list)
    for c in candidates:
        by_host[urlsplit(c["url"]).netloc].append(c)
    groups = []
    for items in by_host.values():
        size = max(100, math.ceil(len(items) / per_host))
        for i in range(0, len(items), size):
            groups.append(items[i:i + size])
    groups.sort(key=len, reverse=True)
    done = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for res in pool.map(validate_group, groups):
            done.extend(res)
            print("  validated %d/%d" % (len(done), len(candidates)),
                  flush=True)
    return done


# --------------------------------------------------------------------------

def owner_sort_key(owner):
    order = {"Bund": 0, "Geodienste": 1}
    if owner in order:
        return (order[owner], owner)
    if owner.startswith("KT_"):
        return (2, owner)
    if owner.startswith("FL_"):
        return (3, owner)
    return (4, owner)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-invalid", action="store_true",
                        help="keep curated sources.csv entries that fail")
    parser.add_argument("--skip", nargs="*", default=[],
                        choices=["ods", "geocat", "geodienste", "arcgis",
                                 "fhnw"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    collected = collect_existing() + collect_manual()
    collectors = [("ods", collect_opendata_swiss), ("geocat", collect_geocat),
                  ("geodienste", collect_geodienste),
                  ("arcgis", collect_arcgis), ("fhnw", collect_fhnw)]
    for name, func in collectors:
        if name in args.skip:
            continue
        try:
            items = func()
            print("%-10s %5d candidates" % (name, len(items)))
            collected += items
        except Exception as e:
            log.error("Collector %s failed: %s", name, e)

    # Normalise and deduplicate. The first occurrence wins, so curated
    # entries from sources.csv keep their owner.
    candidates, seen = [], set()
    for owner, stype, url, origin in collected:
        url = url.strip()
        if not url.startswith("http"):
            continue
        if origin != "sources.csv" and is_skipped(url):
            continue
        if urlsplit(url).netloc.lower().endswith("geodienste.ch") and \
                origin != "geodienste.ch":
            continue  # only use the official geodienste.ch list
        stype = stype or ogc_utils.guess_service_type(url)
        url = url.replace("http://", "https://", 1)
        key = ogc_utils.canonical_key(url, stype)
        if key in seen:
            continue
        seen.add(key)
        candidates.append({"owner": owner, "type": stype, "origin": origin,
                           "url": ogc_utils.capabilities_url(url, stype)})
    print("%d unique candidates, validating ..." % len(candidates))

    results = validate(candidates)

    # A curated entry whose detected type differs may now duplicate another
    # valid entry: deduplicate again on the detected type.
    # Endpoints serving identical content under another URL (e.g. a WMTS
    # via KVP and via its RESTful capabilities) are duplicates as well.
    final, seen, fingerprints = [], set(), {}
    for r in sorted(results, key=lambda r: (not r["valid"],
                                            r["origin"] != "sources.csv")):
        key = ogc_utils.canonical_key(r["url"], r["type"])
        fp = r.get("fingerprint")
        if r["valid"] and key in seen:
            r["valid"], r["error"] = False, "duplicate"
        elif r["valid"] and fp and fp in fingerprints:
            r["valid"] = False
            r["error"] = "same content as %s" % fingerprints[fp]
        if r["valid"]:
            seen.add(key)
            if fp:
                fingerprints[fp] = r["url"]
        final.append(r)

    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["OWNER", "SERVICETYPE", "VALID", "ORIGIN", "URL",
                    "TITLE", "ISSUE"])
        for r in sorted(final, key=lambda r: (owner_sort_key(r["owner"]),
                                              r["url"])):
            w.writerow([r["owner"], r["type"], r["valid"], r["origin"],
                        r["url"], r["title"], r["error"]])

    keep = [r for r in final if r["valid"] or
            (args.keep_invalid and r["origin"] == "sources.csv")]
    keep.sort(key=lambda r: (owner_sort_key(r["owner"]), r["url"]))

    stats = defaultdict(lambda: defaultdict(int))
    for r in keep:
        stats[r["owner"]][r["type"]] += 1
    print("\nValid endpoints per owner:")
    for owner in sorted(stats, key=owner_sort_key):
        print("  %-16s %s" % (owner, dict(stats[owner])))
    print("\n%d valid, %d rejected (see %s)" % (
        len(keep), len(final) - len(keep), REPORT_FILE))

    if args.dry_run:
        return
    with open(config.SOURCE_COLLECTION_CSV, "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["Description", "URL"])
        for r in keep:
            w.writerow([r["owner"], r["url"]])
    print("Wrote %s" % config.SOURCE_COLLECTION_CSV)


if __name__ == "__main__":
    sys.exit(main())
