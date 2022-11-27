import os

SOURCE_COLLECTION_CSV = "sources.csv"
SOURCE_COLLECTION_VERSION = {"KT_AI":"1.3.0","KT_AR":"1.3.0","Geodienste":"1.3.0"}
SOURCE_SCRAPER_DIR = os.path.join("scraper")
GEOSERVICES_CH_CSV = os.path.join("data", "geoservices_CH.csv")
GEODATA_CH_CSV = os.path.join("data", "geodata_CH.csv")
GEODATA_SIMPLE_CH_CSV = os.path.join("data", "geodata_simple_CH.csv")
LOG_FILE = os.path.join("tools", "debug.log")
DEAD_SERVICES_PATH=os.path.join("tools")
MAPGEO_PREFIX="https://test.map.geo.admin.ch/?bgLayer=ch.swisstopo.pixelkarte-grau&"
