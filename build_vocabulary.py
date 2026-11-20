# -*- coding: utf-8 -*-
"""
Build the controlled vocabularies used by enrich.py (run rarely, results are
committed so the weekly pipeline needs no download):

- data/vocab/gemet.json       GEMET, the EU environmental thesaurus
                              (https://www.eionet.europa.eu/gemet), labels in
                              de / fr / it / en, about 5300 concepts
- data/vocab/categories.json  eCH-0166 geocategories as used by
                              geodienste.ch (de / fr / it from the
                              geodienste.ch API, en translated here)

GEMET is taken from geocat.ch, which publishes it as a SKOS thesaurus.
"""

import json
import os
import xml.etree.ElementTree as ET
from collections import defaultdict

import requests

# GEMET as SKOS/RDF from geocat.ch (the Swiss metadata catalogue ships it as
# a thesaurus; much faster and more reliable than the eionet API)
GEMET_SKOS = ("https://www.geocat.ch/geonetwork/srv/api/registries/"
              "vocabularies/external.theme.gemet")
LANGS = ("de", "fr", "it", "en")
OUT_DIR = os.path.join("data", "vocab")

# English labels of the eCH-0166 categories (geodienste.ch returns German)
CATEGORY_EN = {
    "A": "Base maps, land cover, imagery",
    "B": "Locations, reference systems",
    "C": "Elevation",
    "D": "Political and administrative boundaries",
    "E": "Spatial planning, land register",
    "F": "Geology, soils, natural hazards",
    "G": "Forest, flora, fauna",
    "I": "Waters",
    "K": "Atmosphere, air, climate",
    "L": "Environmental and nature protection",
    "O": "Buildings, facilities",
    "P": "Transport",
    "Q": "Utilities, waste disposal, communication",
    "S": "Agriculture",
}


def about_id(concept, ns):
    about = concept.get("{%s}about" % ns["rdf"]) or ""
    return about.rstrip("/").rsplit("/", 1)[-1]


def build_gemet():
    r = requests.get(GEMET_SKOS, timeout=300)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    ns = {"skos": "http://www.w3.org/2004/02/skos/core#",
          "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}
    lang_attr = "{http://www.w3.org/XML/1998/namespace}lang"
    concepts = []
    for c in root.iterfind("skos:Concept", ns):
        labels = {el.get(lang_attr): (el.text or "").strip()
                  for el in c.iterfind("skos:prefLabel", ns)}
        if all(labels.get(l) for l in LANGS) and about_id(c, ns).isdigit():
            concepts.append({"id": about_id(c, ns),
                             **{l: labels[l] for l in LANGS}})
    concepts.sort(key=lambda c: int(c["id"]) if c["id"].isdigit() else 0)
    with open(os.path.join(OUT_DIR, "gemet.json"), "w",
              encoding="utf-8") as f:
        json.dump(concepts, f, ensure_ascii=False, separators=(",", ":"))
    print("Wrote %d GEMET concepts" % len(concepts))


def build_categories():
    cats = defaultdict(dict)
    for lang in ("de", "fr", "it"):
        r = requests.get("https://geodienste.ch/info/services.json",
                         params={"language": lang}, timeout=120)
        r.raise_for_status()
        for svc in r.json()["services"]:
            for c in svc.get("categories") or []:
                code, _, label = c.partition("–")
                cats[code.strip()][lang] = label.strip()
    out = [{"id": code, **labels, "en": CATEGORY_EN.get(code, labels["de"])}
           for code, labels in sorted(cats.items())]
    with open(os.path.join(OUT_DIR, "categories.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("Wrote %d categories" % len(out))


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    build_categories()
    build_gemet()
