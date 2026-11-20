[![GitHub commit](https://img.shields.io/github/last-commit/davidoesch/geoservice_harvester_poc)](https://github.com/davidoesch/geoservice_harvester_poc/commits/main)
[![Run scraper](https://github.com/davidoesch/geoservice_harvester_poc/actions/workflows/run-scraper.yml/badge.svg)](https://github.com/davidoesch/geoservice_harvester_poc/actions/workflows/run-scraper.yml)

# GeoHarvester – every open geoservice in Switzerland, one search

**➜ App: https://davidoesch.github.io/geoservice_harvester_poc**

GeoHarvester automatically harvests the metadata of all open **WMS, WMTS and WFS**
services of the Swiss Confederation, all 26 cantons, cities and the Principality
of Liechtenstein – every week. The result is a searchable catalogue of
<!-- STATS:datasets -->32'200<!-- /STATS --> datasets from <!-- STATS:endpoints -->5'127<!-- /STATS --> service endpoints, including
many datasets that are not listed in any metadata catalogue.

In the web app you can

- **search** any topic (synonyms in German, French, Italian and English, e.g.
  *Bienen* also finds *abeilles*, *apicoltura* and *bees*),
- **see the coverage** on a map: which cantons and cities publish data on the
  topic and where nothing is available,
- **search in the map view** (on by default, checkbox to switch off): once you
  zoom in, results are limited to datasets whose bounding box intersects the
  visible map and follow as you pan and zoom – without a search term this
  answers *"which data exists here?"*,
- **find topics across providers**: datasets of several providers about the
  same thing (e.g. *Bienenstandorte* of ten cantons) are grouped into one
  topic card, with ready-made packages for QGIS, ArcGIS Pro,
  map.geo.admin.ch and OWS Context,
- **find datasets despite missing metadata**: keywords from the GEMET
  thesaurus are added automatically (marked as such), in four languages,
- **combine** datasets of different providers on one map (e.g. bee hives of
  Graubünden, the City of Zurich and Valais at the same time),
- **open** them all at once in [map.geo.admin.ch](https://map.geo.admin.ch),
  **QGIS** (`.qlr`) or **ArcGIS Pro** (`.lyrx`), or copy the service URLs,
- **share** a link that restores your search and your map.

The project started as a proof of concept at the
[4th GeoUnconference](https://github.com/GeoUnconference/discussions/discussions/38).
Background: [blog post](https://www.linkedin.com/pulse/geoharvesting-unexploiting-seo-treasures-geoservices-david-oesch/).
Questions, ideas and bug reports: [GitHub issues](https://github.com/davidoesch/geoservice_harvester_poc/issues).

## Providers

Service endpoints in [`sources.csv`](sources.csv) and harvested layers per
provider (run of 8 November 2026; the weekly run updates the data,
problems of the last run are listed in [`ISSUES.md`](ISSUES.md)).

<!-- PROVIDERS -->
| Provider | Owner code | WMS | WMTS | WFS | Layers harvested |
| -------- | ---------- | --: | ---: | --: | ---------------: |
| Federal Government (geo.admin.ch) | `Bund` | 4 | 1 |  | 1'583 |
| geodienste.ch (intercantonal) | `Geodienste` | 48 |  | 47 | 1'290 |
| Canton of Aargau | `KT_AG` | 1 |  |  | 973 |
| Canton of Appenzell Innerrhoden | `KT_AI` | 1 |  |  | 182 |
| Canton of Appenzell Ausserrhoden | `KT_AR` | 1 |  |  | 212 |
| Canton of Bern | `KT_BE` | 49 |  | 48 | 2'511 |
| Canton of Basel-Landschaft | `KT_BL` | 1 | 1 | 1 | 2'481 |
| Canton of Basel-Stadt | `KT_BS` | 1 | 2 | 1 | 2'804 |
| Canton of Fribourg | `KT_FR` | 482 |  | 391 | 915 |
| Canton of Geneva | `KT_GE` | 883 |  | 879 | 1'635 |
| Canton of Glarus | `KT_GL` | 1 |  | 1 | 443 |
| Canton of Graubünden | `KT_GR` | 53 |  | 12 | 1'994 |
| Canton of Jura | `KT_JU` | 2 | 1 | 2 | 2'913 |
| Canton of Lucerne | `KT_LU` | 220 | 1 | 218 | 1'838 |
| Canton of Neuchâtel | `KT_NE` | 2 | 1 |  | 865 |
| Canton of Nidwalden | `KT_NW` | 1 |  |  | 140 |
| Canton of Obwalden | `KT_OW` | 1 |  |  | 105 |
| Canton of St. Gallen | `KT_SG` | 87 | 13 | 25 | 690 |
| Canton of Schaffhausen | `KT_SH` | 2 |  | 1 | 432 |
| Canton of Solothurn | `KT_SO` | 2 | 1 | 1 | 796 |
| Canton of Schwyz | `KT_SZ` | 2 | 1 | 1 | 2'246 |
| Canton of Thurgau | `KT_TG` | 96 |  | 90 | 1'343 |
| Canton of Ticino | `KT_TI` | 1 | 1 |  | 1'214 |
| Canton of Uri | `KT_UR` | 1 |  | 1 | 1'073 |
| Canton of Vaud | `KT_VD` | 2 | 1 |  | 520 |
| Canton of Valais | `KT_VS` | 24 |  | 1 | 367 |
| Canton of Zug | `KT_ZG` | 56 | 1 | 50 | 1'390 |
| Canton of Zurich | `KT_ZH` | 127 |  | 24 | 2'114 |
| Principality of Liechtenstein | `FL_LI` | 3 |  |  | 358 |
| City of Bern | `CITY_Bern` | 212 | 78 | 83 | 1'979 |
| Municipality of Emmen | `CITY_Emmen` | 1 |  | 1 | 123 |
| City of Geneva | `CITY_Geneve` | 34 |  | 34 | 52 |
| Municipality of Köniz | `CITY_Koeniz` | 4 |  |  | 4 |
| City of Lausanne | `CITY_Lausanne` | 1 |  |  | 538 |
| City of Lucerne | `CITY_Luzern` | 73 |  | 73 | 154 |
| Pully (SIGIP) | `CITY_Pully` | 1 | 1 | 1 | 615 |
| City of Winterthur | `CITY_Winterthur` | 35 |  | 4 | 254 |
| City of Zurich | `CITY_Zuerich` | 282 | 2 | 213 | 4'376 |
| City of Zug | `CITY_Zug` | 10 |  | 10 | 171 |
| Swiss OpenStreetMap Association (SOSM) | `SOSM` |  | 1 |  | 4 |
<!-- /PROVIDERS -->

Owner codes: `KT_<canton>` = canton, `CITY_<name>` = city/municipality,
`FL_LI` = Liechtenstein, `Bund` = federal services (geo.admin.ch and BAFU),
`Geodienste` = intercantonal services of [geodienste.ch](https://www.geodienste.ch),
`SOSM` = Swiss OpenStreetMap Association (third party).
Display names and regions of all owners are defined in [`owners.json`](owners.json).

Known limitations

- Services that require a login or token (HTTP 401/499) are not included.
- Some servers do not answer the cloud machines that run the weekly GitHub
  Action, although they work fine from Switzerland (seen for Zug, Winterthur,
  Pully, Emmen and at times Ticino). When an endpoint fails, the scraper keeps
  its layers from the previous run, logs the issue with the date of the first
  failure (`tools/failing_since.json`, summary in [`ISSUES.md`](ISSUES.md)) and
  retries next week. Endpoints that keep failing from a Swiss network as well
  should be removed from `sources.csv` (`discover_sources.py` does that).
  To refresh blocked providers, run `python scraper.py` from a Swiss network,
  or use a self-hosted runner in Switzerland.
- A browser preview of WFS-only and WMTS-only datasets needs CORS headers on
  the provider's server. Without them, the layers can still be opened in QGIS
  or ArcGIS Pro.

## How it works

```
 opendata.swiss ─┐
 geocat.ch ──────┤
 geodienste.ch ──┤                  ┌──────────────┐   data/geoservices_CH.csv  (one row per service layer)
 ArcGIS portals ─┼─ discover_   ──► │ sources.csv  │──► scraper.py ──► data/geodata_CH.csv     (one row per dataset)
 FHNW Geo-       │  sources.py      └──────────────┘                   data/geoservices_stats_CH.csv
 harvester ──────┤  (validates every endpoint)                         tools/*_errors.csv, ISSUES.md
 manual research ┘
                                                                             │
                                          build_catalog.py ◄─────────────────┘
                                                 │
                                          data/catalog.json ──► index.html (GitHub Pages)
```

| Step | Script | When |
| ---- | ------ | ---- |
| Find and validate service endpoints | [`discover_sources.py`](discover_sources.py) | manually, now and then |
| Harvest all layers of all endpoints | [`scraper.py`](scraper.py) (+ [`scraper/default.py`](scraper/default.py)) | weekly (GitHub Action) |
| Add keywords, categories and topics automatically | [`enrich.py`](enrich.py) | weekly |
| Build the search index of the app | [`build_catalog.py`](build_catalog.py) | weekly |
| Write the topic packages | [`build_topics.py`](build_topics.py) | weekly |
| Compare with the last 30 days, e-mail alert on big drops | [`check-geoservices-stats.py`](check-geoservices-stats.py) | weekly |
| Convert CSV to Parquet | [`format-converter.py`](format-converter.py) | weekly |
| Outlines of cantons / cities for the coverage map | [`build_boundaries.py`](build_boundaries.py) | when owners change |
| GEMET thesaurus and eCH-0166 categories | [`build_vocabulary.py`](build_vocabulary.py) | rarely |

The weekly pipeline runs in one job ([`.github/workflows/run-scraper.yml`](.github/workflows/run-scraper.yml),
Sundays 00:03 UTC, Python 3.13) and commits all results in a single commit.
The other two workflows are kept for manual re-runs.

The scraper fetches each GetCapabilities document once, detects the service
type from the XML (not from the URL), and processes the sources in parallel
with at most three concurrent requests per server. A WMS layer is only
published if a `GetMap` request for it succeeds.

## Automatic enrichment

88% of the harvested layers have no keywords and 62% no description, and many
titles are technical (`zg_bachdelta_bachschuttkegel`). Every week
[`enrich.py`](enrich.py) adds, free of charge and without any paid AI service:

- **Keywords** from [GEMET](https://www.eionet.europa.eu/gemet), the
  multilingual EU environmental thesaurus (taken from geocat.ch). A concept is
  assigned when its label occurs in the title or layer group – German labels
  also inside compounds (*Bienen*standorte), French, Italian and English
  labels as whole words. The keyword is stored with its labels in German,
  French, Italian and English, so *abeilles* finds *Bienenstandorte*.
  Generic terms and provider or place names are ignored.
- **Category**: one of the eCH-0166 geocategories used by geodienste.ch, from
  curated term lists; no category rather than a wrong one.
- **Topics**: titles are normalised (provider names, years, codes removed),
  embedded with the multilingual model
  `paraphrase-multilingual-MiniLM-L12-v2` (fastembed / ONNX, runs on the
  GitHub runner's CPU) and grouped when they are mutual nearest neighbours
  with a high similarity. A topic needs at least two providers; each provider
  contributes its best-matching dataset.

Results are written to [`data/enrichment.csv`](data/enrichment.csv); provider
metadata is never changed, and the app marks the keywords as *added
automatically*. Exact matching was chosen for keywords because, on short layer
titles, embedding similarity proved unreliable for keywords, while it works
well for grouping near-identical titles into topics. A language model could
later add generated descriptions (paid API).

## Topics

[`build_topics.py`](build_topics.py) writes one package per topic to
[`data/topics/`](data/topics): an index ([`index.json`](data/topics/index.json))
with members and a map.geo.admin.ch link, and per topic a QGIS layer file
(`<id>.qlr`), an ArcGIS Pro layer file (`<id>.lyrx`) and an
[OGC OWS Context](https://www.ogc.org/standard/owc/) document (`<id>.ows.json`),
all served by GitHub Pages at
`https://davidoesch.github.io/geoservice_harvester_poc/data/topics/`.

A topic is a bundle of the providers' own services, not one merged service:
GitHub Pages only serves static files and cannot cascade WMS/WFS requests. A
cascading server (e.g. QGIS Server) could publish each topic as one WMS/WFS
using `index.json` as its configuration.

## Add or fix a service

1. Add the GetCapabilities URL to [`sources.csv`](sources.csv)
   (`"Description","URL"` – the description is the owner code, e.g. `KT_LU`,
   URLs must use `https`). For a new owner add an entry to
   [`owners.json`](owners.json) (and, for a new city, run `build_boundaries.py`).
2. Open a pull request.

Alternatively add the endpoint to `MANUAL_SOURCES` (or a whole portal to
`ARCGIS_CATALOGUES`) in [`discover_sources.py`](discover_sources.py) and run it.
It collects candidates from opendata.swiss, all records of geocat.ch,
geodienste.ch, ArcGIS REST catalogues and the
[FHNW Geoharvester](https://github.com/FHNW-IGEO/Geoharvester) source list,
re-validates every endpoint (dropping duplicates that serve identical content
under another URL) and rewrites `sources.csv`. The full validation
report is written to [`tools/sources_report.csv`](tools/sources_report.csv).

## Run it locally

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python scraper.py --owner KT_LU KT_NE   # harvest some owners only (fast)
python scraper.py                       # full run
python build_catalog.py                 # build data/catalog.json
python -m http.server 8000              # app at http://localhost:8000

pip install shapely && python build_boundaries.py   # only when owners.json changes
python discover_sources.py --dry-run                # check for new / dead endpoints
```

## Data

All files are open and updated weekly. Every CSV is also available as Parquet.

### geoservices_CH.csv – one row per service layer

[`data/geoservices_CH.csv`](data/geoservices_CH.csv) · [Parquet](data/geoservices_CH.parquet)

| Field | Description | Format |
| ----- | ----------- | ------ |
| OWNER | Owner code (`<OwnerType>_<OwnerName>`, e.g. `KT_GR`, `CITY_Bern`, `Bund`) | Text |
| TITLE | Title of the layer | Text |
| NAME | Name / identifier of the layer in the service | Text |
| MAPGEO | Permalink to [map.geo.admin.ch](https://map.geo.admin.ch) showing the layer (empty for WFS) | URL |
| TREE | Layer tree derived from the service: `owner/service title/group` | Text, separator `/` |
| GROUP | Name of the parent (group) layer | Text |
| ABSTRACT | Description of the layer | Text |
| KEYWORDS | Keywords of the layer | Text, comma separated |
| LEGEND | Link to the legend image | URL |
| CONTACT | E-mail or name of the service provider | Text |
| SERVICELINK | Base URL of the service (for WMTS: the GetCapabilities URL) | URL |
| METADATA | Link to the metadata of the layer or service | URL |
| UPDATE | Publication date (mostly not provided by services) | Text |
| SERVICETYPE | `WMS`, `WMTS` or `WFS` | Text |
| MAX_ZOOM | map.geo.admin.ch zoom level (0–13) that fits the layer extent | Integer |
| CENTER_LAT | Latitude of the layer's centre (WGS84) | Float |
| CENTER_LON | Longitude of the layer's centre (WGS84) | Float |
| BBOX | Extent of the layer: west south east north (WGS84) | Text |

### geodata_CH.csv – one row per dataset

[`data/geodata_CH.csv`](data/geodata_CH.csv) · [Parquet](data/geodata_CH.parquet)

The layers of `geoservices_CH.csv` aggregated per dataset (OWNER + TITLE + NAME),
with the links to all services that offer the dataset.

| Field | Description | Format |
| ----- | ----------- | ------ |
| OWNER | Owner code | Text |
| TITLE | Title of the dataset | Text |
| NAME | Name of the dataset | Text |
| MAPGEO | Permalink to map.geo.admin.ch (WMS preferred, then WMTS) | URL |
| ABSTRACT | Description | Text |
| KEYWORDS | Keywords | Text, comma separated |
| CONTACT | Contact | Text |
| WMSGetCap | Base URL of the WMS offering the dataset, or `n.a.` | URL |
| WMTSGetCap | GetCapabilities URL of the WMTS offering the dataset, or `n.a.` | URL |
| WFSGetCap | Base URL of the WFS offering the dataset, or `n.a.` | URL |

### Other files

| File | Content |
| ---- | ------- |
| [`data/geodata_simple_CH.csv`](data/geodata_simple_CH.csv) | OWNER, TITLE and MAPGEO only (kept for compatibility) |
| [`data/geoservices_stats_CH.csv`](data/geoservices_stats_CH.csv) | Per owner: number of layers and share of layers with keywords, abstract, contact and metadata link; a dated copy is kept for every run |
| [`data/geoservices_changestats_CH.csv`](data/geoservices_changestats_CH.csv) | Number of layers per owner compared with the mean of the last 30 days |
| [`data/catalog.json`](data/catalog.json) | Compact search index of the web app (datasets merged across WMS/WMTS/WFS, with coverage regions) |
| [`data/boundaries.json`](data/boundaries.json) | Simplified outlines (LV95) of cantons, Liechtenstein and cities for the coverage map |
| [`data/enrichment.csv`](data/enrichment.csv) | Automatic keywords (GEMET), category (eCH-0166) and topic per dataset; machine-generated, see *Automatic enrichment* |
| [`data/topics/`](data/topics) | Topic packages (index, QGIS, ArcGIS Pro, OWS Context) |
| [`data/vocab/`](data/vocab) | GEMET thesaurus and eCH-0166 categories used by `enrich.py` |
| [`tools/*_errors.csv`](tools) | Services that failed in the last run, per owner (summary in [`ISSUES.md`](ISSUES.md)) |
| [`tools/sources_report.csv`](tools/sources_report.csv) | Validation report of `discover_sources.py` (all candidate endpoints and why some were rejected) |

## License

[GPL-3.0](LICENSE). The harvested metadata belongs to the respective providers;
please respect their terms of use. Basemap © [swisstopo](https://www.swisstopo.admin.ch).
