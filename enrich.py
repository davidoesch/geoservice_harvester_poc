# -*- coding: utf-8 -*-
"""
Title: Automatic metadata enrichment and topics
Purpose: Free, offline "AI" enrichment of the harvested datasets, run weekly
    after scraper.py:

    - keywords: concepts of the multilingual GEMET thesaurus that occur in
      the title or layer group (also inside German compounds such as
      "Bienenstandorte"); stored with labels in de / fr / it / en, so a
      French search finds a German-titled dataset
    - category: eCH-0166 geocategory (as used by geodienste.ch), from
      curated term lists
    - topic: datasets of different providers about the same thing
      (e.g. "Bienenstandorte" of ten cantons), grouped automatically with
      multilingual sentence embeddings (fastembed / ONNX, model
      paraphrase-multilingual-MiniLM-L12-v2, CPU)

Keywords and categories use exact term matching on purpose: on short,
technical layer titles the embedding similarity proved unreliable for
keywords (e.g. "Allmendparzelle" -> "Flächenwidmung"), while it works well
for grouping near-identical titles into topics. No paid API, no text
generation. Provider metadata is never changed: results go to
data/enrichment.csv and are marked as automatic in the app.

Run:  python enrich.py        (needs data/vocab/*.json, see
                               build_vocabulary.py)
"""

import csv
import json
import os
import re
import time
import unicodedata
from collections import Counter, defaultdict

import numpy as np

import build_catalog as bc
import configuration as config

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VOCAB_DIR = os.path.join("data", "vocab")
OUT_FILE = os.path.join("data", "enrichment.csv")

# Tuned on spot checks (see README "Automatic enrichment")
KEYWORD_MAX = 5
KEYWORD_MIN_LEN = 4         # shortest GEMET label that may match
GERMAN_INFIX_MIN_LEN = 5    # German labels may match inside compounds
FOREIGN_COVERAGE = 0.7      # fr/it/en labels must cover most of a word
TOPIC_SIM = 0.86            # title similarity for "same topic"
TOPIC_SIM_STEP = 0.03       # stricter threshold for oversized topics
TOPIC_MAX_MEMBERS = 60
TOPIC_NEIGHBOURS = 15
TOPIC_MIN_OWNERS = 2

FIELDS = ["DATASET_KEY", "OWNER", "TITLE", "GEMET_IDS", "KEYWORDS_AUTO",
          "CATEGORY", "TOPIC_ID", "TOPIC_LABEL"]


# --------------------------------------------------------------- text prep

def _owner_words():
    """Words that name a provider and must not drive topics."""
    words = {"kanton", "kantons", "kt", "canton", "cantone", "cantonal",
             "cantonale", "stadt", "ville", "citta", "city", "gemeinde",
             "commune", "comune", "municipality", "bund", "ch", "fl",
             "geoportal", "geodaten", "wms", "wfs", "wmts", "ogd", "layer",
             "v", "ds", "col", "mp", "im"}
    with open(config.OWNERS_JSON, encoding="utf-8") as f:
        owners = json.load(f)
    for code, info in owners.items():
        words.add((info.get("region") or "").lower())
        for label in (info.get("label") or {}).values():
            words.update(normalise(label).split())
    return {w for w in words if w}


def normalise(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)   # camelCase
    text = re.sub(r"[_.:/\\-]+", " ", text).lower()
    return re.sub(r"[^a-z0-9 ]+", " ", text)


def topic_text(title, stop):
    """Title without provider names, years, scales and version codes."""
    words = [w for w in normalise(title).split()
             if w not in stop and not w.isdigit() and len(w) > 1
             and not re.fullmatch(r"v\d+|\d+[a-z]?|[a-z]\d+", w)]
    return " ".join(words)


def keyword_text(ds):
    """Title and layer group (the abstract is often generic boilerplate)."""
    return ds["t"] + " " + (ds["g"].split(" / ")[-1] if ds["g"] else "")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", normalise(text)).strip("-")[:60]


# ------------------------------------------------------- keyword matching

# Labels too generic to be useful as keywords
GENERIC = set("""
karte karten plan plane daten gebiet gebiete zone zonen region linie linien
punkt punkte flache flachen objekt objekte netz art typ stand inventar
kataster grenze wert werte anlage anlagen information informationen modell
projekt gruppe element elemente teil bild grundlage land wirkung system
carte cartes donnees ligne lignes point points projet systeme groupe base
map maps data area areas line lines project group image information model
piano dati linea punto zona carta progetto sistema gruppo immagine base
gemeinde gemeinden commune communes comune comuni thema theme themes tema
""".split())

# eCH-0166 categories: typical terms (normalised, matched like keywords)
CATEGORY_TERMS = {
    "A": "orthofoto orthophoto ortofoto luftbild aerienne swissimage basisplan "
         "landeskarte pixelkarte ubersichtsplan bodenbedeckung satellit "
         "hintergrund stadtplan couverture cartografia",
    "B": "adresse gebaudeadress hausnummer strassenname ortschaft "
         "postleitzahl fixpunkt vermessung koordinat flurname nomenklatur "
         "localite indirizz toponym lieudit",
    "C": "hohenkurv hohenmodell gelandemodell relief altitude altimetr "
         "hangneigung schummerung courbe isoipse lidar hillshade dtm dom",
    "D": "gemeindegrenz kantonsgrenz hoheitsgrenz landesgrenz bezirk "
         "wahlkreis stimmbezirk limite district confini frontiere",
    "E": "nutzungsplan zonenplan bauzone richtplan baulinie oereb rdppf "
         "catasto parzelle liegenschaft grundstuck affectation "
         "sondernutzung gestaltungsplan bebauungsplan planungszone "
         "pianificazion amenagement regolatore landwert",
    "F": "geolog boden naturgefahr gefahrenkart gefahrenhinweis rutsch "
         "sturz lawine hochwasser erosion erdbeben karst bohrung geotop "
         "erdwarm geotherm danger pericol frana valanga radon sondage",
    "G": "wald forst baum flora fauna wildtier vogel amphib neophyt biotop "
         "lebensraum foret arbre bosco albero jagd chasse caccia fisch peche "
         "pesca insekt biene hornisse vegetation pflanze reptil fledermaus",
    "I": "gewasser fluss bach grundwasser quelle hydro wasserbau riviere "
         "lac eaux acque fiume lago gewasserraum revitalis entwasser "
         "drainage seeufer ufer",
    "K": "klima luft wetter meteo temperatur warmebelast niederschlag "
         "immission schadstoff ozon climat clima aria hitze",
    "L": "naturschutz landschaftsschutz schutzgebiet umweltschutz larm "
         "bruit rumore altlast belastet okomorph reservat auen moor "
         "trockenwiese protezione",
    "O": "gebaude bauten denkmal kulturgut archaolog archeolog schulhaus "
         "schule spital sportanlage kirche batiment edifice edific "
         "schutzraum immobilie wohnung hotel friedhof",
    "P": "verkehr strasse bahn haltestelle velo fussweg wanderweg "
         "parkplatz flughafen schiff trafic route transport traffico "
         "strada ferrovi parking mobilit unfall tram",
    "Q": "abwasser wasserversorgung leitung kanalisation strom energie "
         "elektr fernwarm telekom kommunikation antenne mobilfunk abfall "
         "entsorgung deponie solar wasserkraft klaranlage approvisionnement "
         "dechet rifiut energia elettric",
    "S": "landwirtschaft agrar fruchtfolge rebbau weinbau alpwirtschaft "
         "bewirtschaft nutzungsflach biodiversitatsforder agricol agricult "
         "vigne viticol sommerung",
}


def norm_words(text):
    return normalise(text).split()


class TermMatcher:
    """
    Find vocabulary labels in a text. German labels may also match inside
    words (compounds such as "Bienenstandorte"); French, Italian and English
    labels must cover most of a word (plural / inflection endings only).
    """

    def __init__(self, entries, stop=()):
        # entries: (label_text, lang, value); stop: words never to match
        # (e.g. names of providers and places)
        self.single, self.multi = {}, {}
        stop = GENERIC | set(stop)
        for text, lang, value in entries:
            n = " ".join(norm_words(text))
            if len(n) < KEYWORD_MIN_LEN or n in stop or \
                    re.search(r"\d", n):
                continue
            target = self.multi if " " in n else self.single
            target.setdefault(n, []).append((lang, value))

    def find(self, text):
        words = norm_words(text)
        padded = " " + " ".join(words) + " "
        found = {}
        for phrase, hits in self.multi.items():
            if " " + phrase + " " in padded:
                found[phrase] = [v for _, v in hits]
        for w in words:
            n = len(w)
            for i in range(n):
                for j in range(i + KEYWORD_MIN_LEN, n + 1):
                    hits = self.single.get(w[i:j])
                    if not hits:
                        continue
                    sub = w[i:j]
                    ok = []
                    for lang, value in hits:
                        if lang == "de":
                            if i == 0 or len(sub) >= GERMAN_INFIX_MIN_LEN:
                                ok.append(value)
                        elif i == 0 and len(sub) >= FOREIGN_COVERAGE * n:
                            ok.append(value)
                    if ok:
                        found[sub] = ok
        # longest matches first; drop matches contained in a longer one
        keep = []
        for k in sorted(found, key=len, reverse=True):
            if not any(k in other for other in keep):
                keep.append(k)
        out = []
        for k in keep:
            for v in found[k]:
                if v not in out:
                    out.append(v)
        return out


def gemet_matcher(gemet, stop=()):
    return TermMatcher(((c[lang], lang, c["id"]) for c in gemet
                        for lang in ("de", "fr", "it", "en")), stop)


def category_matcher():
    return TermMatcher((term, "de", code) for code, terms in
                       CATEGORY_TERMS.items() for term in terms.split())


def best_category(matcher, text):
    hits = matcher.find(text)
    return Counter(hits).most_common(1)[0][0] if hits else ""


# --------------------------------------------------------------- embedding

def embedder():
    from fastembed import TextEmbedding
    # FASTEMBED_CACHE_PATH: model cache (cached between GitHub Action runs)
    model = TextEmbedding(model_name=MODEL,
                          cache_dir=os.environ.get("FASTEMBED_CACHE_PATH"))

    def embed(texts):
        vecs = np.array(list(model.embed(texts, batch_size=256)),
                        dtype=np.float32)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
        return vecs
    return embed


def top_k(a, b, k, chunk=2048):
    """Indices and similarities of the k nearest rows of b for each row of a."""
    idx = np.zeros((len(a), k), dtype=np.int32)
    sim = np.zeros((len(a), k), dtype=np.float32)
    for i in range(0, len(a), chunk):
        s = a[i:i + chunk] @ b.T
        part = np.argpartition(-s, min(k, s.shape[1] - 1), axis=1)[:, :k]
        ps = np.take_along_axis(s, part, axis=1)
        order = np.argsort(-ps, axis=1)
        idx[i:i + chunk] = np.take_along_axis(part, order, axis=1)
        sim[i:i + chunk] = np.take_along_axis(ps, order, axis=1)
    return idx, sim


# ------------------------------------------------------------------ topics

def find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def cluster(vecs, members, threshold):
    """Mutual-nearest-neighbour graph above threshold -> connected parts."""
    n = len(members)
    if n < 2:
        return [members]
    sub = vecs[members]
    k = min(TOPIC_NEIGHBOURS, n - 1)
    idx, sim = top_k(sub, sub, k + 1)
    neigh = [set(idx[i][(sim[i] >= threshold) & (idx[i] != i)])
             for i in range(n)]
    parent = list(range(n))
    for i in range(n):
        for j in neigh[i]:
            if i in neigh[j]:                      # mutual neighbours only
                parent[find(parent, i)] = find(parent, j)
    groups = defaultdict(list)
    for i in range(n):
        groups[find(parent, i)].append(members[i])
    return list(groups.values())


def topic_label(titles):
    """
    Most frequent title of a topic, preferring human-readable titles over
    technical layer names (e.g. "vd.station_fecondation_apicole").
    """
    def technical(t):
        return bool(re.search(r"[_.]|^[a-z0-9]+$", t))
    counts = Counter(titles)
    readable = [t for t, _ in counts.most_common() if not technical(t)]
    if readable:
        return readable[0]
    t = counts.most_common(1)[0][0]
    t = re.sub(r"^[a-z]{2}\.", "", t)            # canton prefix "vd."
    t = re.sub(r"[_.]+", " ", t).strip()
    return t[:1].upper() + t[1:]


def build_topics(datasets, owners, embed, stop):
    texts = [topic_text(ds["t"], stop) for ds in datasets]
    uniq = sorted({t for t in texts if len(t) >= 4})
    if not uniq:
        return {}
    pos = {t: i for i, t in enumerate(uniq)}
    vecs = embed(uniq)
    by_text = defaultdict(list)
    for d, t in enumerate(texts):
        if t in pos:
            by_text[pos[t]].append(d)

    pending = [(list(range(len(uniq))), TOPIC_SIM)]
    groups = []
    while pending:
        members, threshold = pending.pop()
        for g in cluster(vecs, members, threshold):
            size = sum(len(by_text[u]) for u in g)
            if size > TOPIC_MAX_MEMBERS and len(g) > 1 and threshold < 0.99:
                pending.append((g, threshold + TOPIC_SIM_STEP))
            else:
                groups.append(g)

    topics = {}
    for g in groups:
        centre = vecs[g].mean(axis=0)
        ds_ids = [d for u in g for d in by_text[u]]
        if len({datasets[d]["o"] for d in ds_ids}) < TOPIC_MIN_OWNERS:
            continue
        # one dataset per provider: the one closest to the topic centre
        best = {}
        for u in g:
            score = float(vecs[u] @ centre)
            for d in by_text[u]:
                o = datasets[d]["o"]
                if o not in best or score > best[o][0]:
                    best[o] = (score, d)
        label = topic_label([datasets[d]["t"] for _, d in best.values()])
        tid = slug(label) or "topic"
        while tid in topics:
            tid += "-2"
        topics[tid] = {"label": label,
                       "members": sorted(d for _, d in best.values())}
    return topics


# ------------------------------------------------------------------- main

def main():
    started = time.time()
    with open(os.path.join(VOCAB_DIR, "gemet.json"), encoding="utf-8") as f:
        gemet = json.load(f)
    with open(config.OWNERS_JSON, encoding="utf-8") as f:
        owner_info = json.load(f)

    owners, services, datasets = bc.merge_datasets(bc.load_layers(),
                                                   owner_info)
    stop = _owner_words()
    print("%d datasets, %d GEMET concepts" % (len(datasets), len(gemet)))
    by_id = {c["id"]: c for c in gemet}
    kw_matcher = gemet_matcher(gemet, stop)
    cat_matcher = category_matcher()
    keywords = [kw_matcher.find(keyword_text(ds))[:KEYWORD_MAX]
                for ds in datasets]
    cats = [best_category(cat_matcher, keyword_text(ds) + " " +
                          ", ".join(ds["k"])) for ds in datasets]
    print("keywords and categories done after %.0fs"
          % (time.time() - started))

    topics = build_topics(datasets, owners, embedder(), stop)
    topic_of = {d: tid for tid, t in topics.items() for d in t["members"]}

    with open(OUT_FILE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for d, ds in enumerate(datasets):
            hits, labels = [], set()
            for cid in keywords[d]:      # one concept per German label
                if by_id[cid]["de"] not in labels:
                    labels.add(by_id[cid]["de"])
                    hits.append(by_id[cid])
            cat = cats[d]
            tid = topic_of.get(d, "")
            w.writerow({
                "DATASET_KEY": bc.dataset_key(ds, owners, services),
                "OWNER": owners[ds["o"]]["code"],
                "TITLE": ds["t"],
                "GEMET_IDS": " ".join(c["id"] for c in hits),
                "KEYWORDS_AUTO": ", ".join(c["de"] for c in hits),
                "CATEGORY": cat,
                "TOPIC_ID": tid,
                "TOPIC_LABEL": topics[tid]["label"] if tid else "",
            })
    n_kw = sum(1 for k in keywords if k)
    print("Wrote %s: %d datasets with keywords, %d topics covering %d "
          "datasets, %.0fs" % (OUT_FILE, n_kw, len(topics), len(topic_of),
                               time.time() - started))


if __name__ == "__main__":
    main()
