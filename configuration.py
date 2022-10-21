import os

SOURCE_COLLECTION_CSV = "sources.csv"
SOURCE_SCRAPER_DIR = os.path.join("scraper")
GEOSERVICES_CH_CSV = os.path.join("data", "geoservices_CH.csv")
LOG_FILE = os.path.join("tools", "debug.log")
DEAD_SERVICES_PATH=os.path.join("tools")
MAPGEO_PREFIX="https://map.geo.admin.ch/?bgLayer=ch.swisstopo.pixelkarte-grau&"

SERVICE_RESULT={"OWNER":"n.a.","TITLE":"n.a","NAME":"n.a","TREE":"n.a.","GROUP":"","ABSTRACT":"n.a",
    "KEYWORDS":"n.a.","LEGEND":"n.a.","CONTACT":"n.a.","SERVICELINK":"n.a.",
    "METADATA":"n.a.","UPDATE":"n.a.","LEGEND":"n.a.","SERVICETYPE":"n.a.","MAX ZOOM":"n.a.",
    "CENTER_LAT":"n.a.","CENTER_LON":"n.a.","MAPGEO":"n.a."}