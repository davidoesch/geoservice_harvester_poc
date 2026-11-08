import os

SOURCE_COLLECTION_CSV = "sources.csv"
SOURCE_SCRAPER_DIR = "scraper"

GEOSERVICES_CH_CSV = os.path.join("data", "geoservices_CH.csv")
GEOSERVICES_STATS_CH_CSV = os.path.join("data", "geoservices_stats_CH.csv")
GEOSERVICES_STATS_CH_PATTERN = os.path.join(
    "data", "* geoservices_stats_CH.csv")
GEOSERVICES_CHANGESTATS_CH_CSV = os.path.join(
    "data", "geoservices_changestats_CH.csv")
GEOSERVICES_CHANGESTATS_ALERT_RECIPIENTS = [
    'david.oesch@gmail.com', 'mail@ralphstraumann.ch']
GEODATA_CH_CSV = os.path.join("data", "geodata_CH.csv")
GEODATA_SIMPLE_CH_CSV = os.path.join("data", "geodata_simple_CH.csv")

# Web application (index.html) data
CATALOG_JSON = os.path.join("data", "catalog.json")
OWNERS_JSON = "owners.json"

LOG_FILE = os.path.join("tools", "debug.log")
OPERATOR_STATS_FILE = "ISSUES.md"
DEAD_SERVICES_PATH = "tools"

# Permalinks to the federal map viewer (web-mapviewer, URL format
# "#/map?layers=WMS|<url>|<layer>"). The scraper appends center, zoom and
# layers.
MAPGEO_PREFIX = ("https://map.geo.admin.ch/#/map?lang=de"
                 "&bgLayer=ch.swisstopo.pixelkarte-grau&")

# Fallback extent of Switzerland (WGS84: west, south, east, north)
SWISS_BBOX_WGS84 = (5.95, 45.81, 10.5, 47.81)

# Google Indexing API (optional, see scraper.publish_urls)
JSON_KEY_FILE = "geoharvester-indexing-credentials.json"
SCOPES = ["https://www.googleapis.com/auth/indexing"]
SITE_URL = "https://davidoesch.github.io/geoservice_harvester_poc/"
INDEXING_URLS = [
    SITE_URL,
    SITE_URL + "data/geoservices_stats_CH.csv",
    SITE_URL + "data/geodata_CH.csv",
]
