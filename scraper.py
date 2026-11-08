# -*- coding: utf-8 -*-
"""
Title: Scraper a.k.a. Geoharvester
Author: David Oesch
Date: 2022-11-05 (refactored 2026-11)
Purpose: Harvest the layer metadata of all OGC services (WMS, WMTS, WFS)
    listed in sources.csv and write them to the data/ folder.

Notes
- Python >= 3.10, tested with 3.13
- Each GetCapabilities document is downloaded exactly once; the service type
  is detected from the XML (not guessed from the URL) and the document is
  handed to OWSLib.
- Sources are processed in parallel, grouped by host so that a single server
  never receives more than a few concurrent requests.
- Problems are written to tools/<OWNER>_errors.csv and summarised in
  ISSUES.md.

Usage
    python scraper.py                      # full run
    python scraper.py --owner KT_LU KT_NE  # only some owners (for testing)
"""

import argparse
import csv
import glob
import importlib
import importlib.util
import json
import logging
import math
import os
import shutil
import sys
import threading
import time
import warnings
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from statistics import mean
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo

import configuration as config
import ogc_utils

sys.path.insert(0, config.SOURCE_SCRAPER_DIR)

logger = logging.getLogger("Scraping log")
TZ = ZoneInfo("Europe/Zurich")

FIELDNAMES = ["OWNER", "TITLE", "NAME", "MAPGEO", "TREE", "GROUP",
              "ABSTRACT", "KEYWORDS", "LEGEND", "CONTACT", "SERVICELINK",
              "METADATA", "UPDATE", "SERVICETYPE", "MAX_ZOOM", "CENTER_LAT",
              "CENTER_LON", "BBOX"]

service_keys = (("WMSGetCap", "n.a."), ("WMTSGetCap", "n.a."),
                ("WFSGetCap", "n.a."))


def service_result_empty():
    """Return a layer record with placeholder values for all fields."""
    record = dict.fromkeys(FIELDNAMES, "n.a.")
    record["GROUP"] = ""
    return record


def load_source_collection():
    """Load sources.csv into a list of dicts (keys: Description, URL)."""
    with open(config.SOURCE_COLLECTION_CSV, mode="r", encoding="utf8") as f:
        sources = [{k: (v or "").strip() for k, v in row.items()}
                   for row in csv.DictReader(f)]
    return [s for s in sources if s.get("URL")]


class ErrorLog:
    """Thread-safe collection of per-operator issues."""

    def __init__(self):
        self._lock = threading.Lock()
        self.entries = defaultdict(list)

    def add(self, operator, url, issue):
        timestamp = datetime.now(TZ).isoformat()
        issue = str(issue).replace("\n", " ").replace("\r", " ")
        with self._lock:
            self.entries[operator].append((timestamp, operator, url, issue))

    def write(self, path):
        for old in glob.glob(os.path.join(path, "*_errors.csv")):
            os.remove(old)
        for operator, rows in self.entries.items():
            with open(os.path.join(path, "%s_errors.csv" % operator), "w",
                      encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(["Timestamp", "Operator", "URL", "Issue"])
                w.writerows(rows)


ERRORS = ErrorLog()


def load_scraper(operator):
    """Return the custom scraper module for an operator or the default."""
    name = operator if importlib.util.find_spec(operator) else "default"
    return importlib.import_module(name)


def getmap_ok(service, name, layer, timeout=20):
    """Check that a WMS layer can actually be rendered (GetMap)."""
    bbox = getattr(layer, "boundingBoxWGS84", None)
    if not bbox or len(bbox) != 4 or not all(map(math.isfinite, bbox)):
        bbox = config.SWISS_BBOX_WGS84
    try:
        service.getmap(layers=[name], srs="EPSG:4326", bbox=tuple(bbox),
                       size=(256, 256), format="image/png", transparent=True,
                       timeout=timeout)
        return True, None
    except Exception as e:
        return False, str(e).replace("\n", " ")[:200]


def harvest_source(source):
    """
    Harvest all layers of one service endpoint.

    Returns a list of layer records (dicts with FIELDNAMES keys).
    """
    operator, url = source["Description"], source["URL"]
    rows = []
    cap = ogc_utils.fetch_capabilities(url)
    if not cap["ok"]:
        ERRORS.add(operator, url, cap["error"])
        logger.warning("%s > %s: %s", operator, url, cap["error"])
        return rows
    try:
        service = ogc_utils.open_service(url, cap)
    except Exception as e:
        ERRORS.add(operator, url, "OWSLib could not parse capabilities: %s"
                   % e)
        logger.error("%s > %s: %s", operator, url, e)
        return rows

    stype = cap["type"]
    src = dict(source, SERVICETYPE=stype)
    scraper = load_scraper(operator)
    service_title = getattr(service.identification, "title", None)

    def layertree(name):
        parts = [operator, service_title, (name or "").replace('"', "")]
        return "/".join(p for p in parts if p)

    for name, layer in list(service.contents.items()):
        try:
            if stype == "WMS":
                parent = getattr(layer, "parent", None)
                if parent is not None and getattr(parent, "name", None):
                    # Child layer: listed under its parent group
                    group, tree = parent.name, layertree(parent.name)
                else:
                    # Top-level layer: must have a title and render
                    if layer.title is None:
                        logger.warning("%s: Title is empty. Skipping.", name)
                        continue
                    ok, err = getmap_ok(service, name, layer)
                    if not ok:
                        logger.warning("%s > %s: GetMap failed for %s: %s",
                                       operator, url, name, err)
                        continue
                    group, tree = name, layertree(name)
            else:
                group, tree = name, layertree(name)

            record = scraper.scrape(src, service, name, tree, group,
                                    service_result_empty(),
                                    config.MAPGEO_PREFIX)
            if record:
                rows.append(record)
        except Exception as e:
            ERRORS.add(operator, "%s (%s)" % (name, url), e)
            logger.error("%s, %s: %s", operator, name, e)
    logger.info("%s > %s: %s, %d layers", operator, url, stype, len(rows))
    return rows


def harvest_group(group):
    """Harvest sources sequentially (they share the same host)."""
    out = []
    for index, source in group:
        start = time.time()
        rows = harvest_source(source)
        out.append((index, rows))
        print("  %-16s %4d layers %5.1fs  %s" % (
            source["Description"], len(rows), time.time() - start,
            source["URL"][:90]), flush=True)
    return out


def harvest_all(sources, workers=12, per_host=3):
    """
    Harvest all sources in parallel. Sources are grouped by host and each
    host gets at most `per_host` concurrent workers, so large portals (e.g.
    one ArcGIS server with 1500 services) are not overloaded.
    """
    by_host = defaultdict(list)
    for index, source in enumerate(sources):
        by_host[urlsplit(source["URL"]).netloc].append((index, source))
    groups = []
    for items in by_host.values():
        size = max(100, math.ceil(len(items) / per_host))
        for i in range(0, len(items), size):
            groups.append(items[i:i + size])
    groups.sort(key=len, reverse=True)

    results = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for group_result in pool.map(harvest_group, groups):
            for index, rows in group_result:
                results[index] = rows
    # Keep the order of sources.csv
    return [row for index in sorted(results) for row in results[index]]


def write_csv(rows, output_file, fieldnames):
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_dataset_info(csv_filename, output_file, output_simple_file):
    """
    Aggregate the layer records (one per service and layer) into one record
    per dataset (OWNER + TITLE + NAME) with links to all services (WMS, WMTS,
    WFS) offering it. Writes the full and the simple dataset files.
    """
    with open(csv_filename, encoding="utf-8") as f:
        layers = list(csv.DictReader(f))

    datasets = {}
    for layer in layers:
        key = (layer["OWNER"], layer["TITLE"], layer["NAME"])
        ds = datasets.get(key)
        if ds is None:
            ds = service_result_empty()
            ds.update(service_keys)
            ds.update(OWNER=layer["OWNER"], TITLE=layer["TITLE"],
                      NAME=layer["NAME"], KEYWORDS="")
            datasets[key] = ds
        # Prefer a WMS link to map.geo.admin.ch, then WMTS
        if "WMS|" not in unquote(ds["MAPGEO"]) and \
                layer["MAPGEO"] not in ("", "n.a."):
            if "WMS|" in unquote(layer["MAPGEO"]) or \
                    ds["MAPGEO"] in ("", "n.a."):
                ds["MAPGEO"] = layer["MAPGEO"]
        for field in ("ABSTRACT", "METADATA", "CONTACT"):
            if layer[field] not in ("", "n.a."):
                ds[field] = layer[field]
        if layer["KEYWORDS"] not in ("", "n.a."):
            ds["KEYWORDS"] = layer["KEYWORDS"]
        stype = layer["SERVICETYPE"].upper()
        if stype in ("WMS", "WMTS", "WFS"):
            ds["%sGetCap" % stype] = layer["SERVICELINK"]

    full_keys = ["OWNER", "TITLE", "NAME", "MAPGEO", "ABSTRACT", "KEYWORDS",
                 "CONTACT", "WMSGetCap", "WMTSGetCap", "WFSGetCap"]
    for ds in datasets.values():
        keywords = [k.strip() for k in ds["KEYWORDS"].split(",") if k.strip()]
        ds["KEYWORDS"] = ",".join(dict.fromkeys(keywords))
    write_csv(datasets.values(), output_file, full_keys)
    write_csv(datasets.values(), output_simple_file,
              ["OWNER", "TITLE", "MAPGEO"])


def write_dataset_stats(csv_filename, output_file):
    """
    Per OWNER: number of layers and completeness of KEYWORDS, ABSTRACT,
    CONTACT and METADATA. Also keeps a dated copy of the statistics file.
    """
    with open(csv_filename, mode="r", encoding="utf8") as f:
        data = list(csv.DictReader(f))

    owner_counts = defaultdict(int)
    for entry in data:
        owner_counts[entry["OWNER"]] += 1

    fields = ["KEYWORDS", "ABSTRACT", "CONTACT", "METADATA"]
    counts = defaultdict(lambda: defaultdict(int))
    for field in fields:
        for entry in data:
            if entry[field] and entry[field] != "n.a.":
                counts[field][entry["OWNER"]] += 1

    datestamp = datetime.now(TZ).strftime("%Y-%m-%d")
    header = ["DATE", "OWNER", "DATASET_COUNT"]
    for field in fields:
        header += [field + "_COUNT", field + "_MISSING",
                   field + "_PERCENTAGE"]
    header.append("TOTAL_PERCENTAGE")

    with open(output_file, mode="w", encoding="utf8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        for owner, total in owner_counts.items():
            row = {"DATE": datestamp, "OWNER": owner, "DATASET_COUNT": total}
            shares = []
            for field in fields:
                count = counts[field].get(owner, 0)
                share = count / total if total else 0
                shares.append(share)
                row[field + "_COUNT"] = count
                row[field + "_MISSING"] = total - count
                row[field + "_PERCENTAGE"] = ("{:.1%}".format(share)
                                              if count else "0%")
            row["TOTAL_PERCENTAGE"] = "{:.1%}".format(mean(shares))
            writer.writerow(row)

    path, file_with_ext = os.path.split(output_file)
    shutil.copy(output_file,
                os.path.join(path, "%s %s" % (datestamp, file_with_ext)))


def write_operator_stats(out_file):
    """Summarise the per-operator error files in a markdown file."""
    error_files = sorted(glob.glob(
        os.path.join(config.DEAD_SERVICES_PATH, "*_errors.csv")))
    datestamp = datetime.now(TZ).strftime("%d.%m.%Y")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("# Issues found during the last run (%s)\n\n" % datestamp)
        if not error_files:
            f.write("No issues found.\n")
        for error_file in error_files:
            operator = os.path.basename(error_file).replace("_errors.csv", "")
            with open(error_file, "r", encoding="utf-8") as in_file:
                n = max(0, sum(1 for _ in in_file) - 1)
            f.write("- %s: [%s issue(s)](%s)\n" % (
                operator, n, error_file.replace(os.sep, "/")))


def publish_urls():
    """
    Notify the Google Indexing API about updated pages. Optional: only runs
    if a service account is configured (env CLIENT_SECRET or key file).
    """
    info = None
    if os.environ.get("CLIENT_SECRET"):
        info = json.loads(os.environ["CLIENT_SECRET"])
    elif os.path.exists(config.JSON_KEY_FILE):
        print("Local key file found; set CLIENT_SECRET to publish to Google")
        return
    if not info:
        print("No Google Indexing credentials configured, skipping.")
        return
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=config.SCOPES)
        service = build("indexing", "v3", credentials=credentials,
                        cache_discovery=False)

        def callback(request_id, response, exception):
            if exception is not None:
                logger.error("Failed to update Google Index API: %s",
                             exception)

        batch = service.new_batch_http_request(callback=callback)
        for url in config.INDEXING_URLS:
            batch.add(service.urlNotifications().publish(
                body={"url": url, "type": "URL_UPDATED"}))
        batch.execute()
        print("Published %d URLs to the Google Indexing API"
              % len(config.INDEXING_URLS))
    except Exception as e:
        logger.error("Google Indexing API failed: %s", e)
        print("Google Indexing API failed: %s" % e)


def setup_logging():
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(config.LOG_FILE, "w", "utf-8")
    fh.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(threadName)s - %(message)s"))
    logger.addHandler(fh)
    # OWSLib is chatty; keep its warnings out of our log
    logging.getLogger("owslib").setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", module="owslib")


def main():
    parser = argparse.ArgumentParser(description="Geoservice harvester")
    parser.add_argument("--owner", nargs="*",
                        help="only harvest these owners (testing)")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--no-publish", action="store_true",
                        help="skip the Google Indexing API")
    args = parser.parse_args()

    setup_logging()
    started = time.time()
    sources = load_source_collection()
    if args.owner:
        sources = [s for s in sources if s["Description"] in args.owner]
    print("Harvesting %d sources with %d workers" % (len(sources),
                                                      args.workers))
    logger.info("Harvesting %d sources", len(sources))

    rows = harvest_all(sources, workers=args.workers)
    write_csv(rows, config.GEOSERVICES_CH_CSV, FIELDNAMES)
    ERRORS.write(config.DEAD_SERVICES_PATH)
    print("\n%d layers harvested in %.0f min" % (
        len(rows), (time.time() - started) / 60))

    print("Creating dataset files")
    write_dataset_info(config.GEOSERVICES_CH_CSV, config.GEODATA_CH_CSV,
                       config.GEODATA_SIMPLE_CH_CSV)
    write_dataset_stats(config.GEOSERVICES_CH_CSV,
                        config.GEOSERVICES_STATS_CH_CSV)
    write_operator_stats(config.OPERATOR_STATS_FILE)

    if not args.no_publish and not args.owner:
        publish_urls()

    print("\nScraper run completed")
    logger.info("Scraper run completed")


if __name__ == "__main__":
    main()
