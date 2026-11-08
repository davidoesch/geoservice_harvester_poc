# -*- coding: utf-8 -*-
"""
Shared helpers for talking to OGC web services (WMS, WMTS, WFS).

Used by scraper.py (weekly harvest) and discover_sources.py (finding and
validating new service endpoints for sources.csv).

The key idea: fetch a GetCapabilities document exactly once, detect the
service type from the XML root element (not from the URL, which is often
misleading, e.g. ".../av_wms?service=WFS"), and hand the XML to OWSLib so it
does not have to download it again.
"""

import hashlib
import re
import threading
import xml.etree.ElementTree as ET
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = ("GeoHarvester/2.0 "
              "(+https://github.com/davidoesch/geoservice_harvester_poc)")

SERVICE_TYPES = ("WMS", "WMTS", "WFS")

# Query parameters that belong to an individual OGC request and therefore
# must not be part of a service's base URL. Everything else (e.g. "map=",
# "ogcserver=", "lang=") is kept because servers need it.
OGC_REQUEST_PARAMS = {
    "service", "request", "version", "acceptversions", "sections",
    "layers", "layer", "typename", "typenames", "bbox", "width", "height",
    "format", "crs", "srs", "srsname", "styles", "outputformat",
    "transparent", "tiled", "dpi", "opacities", "updatesequence",
}

_thread_local = threading.local()


def session():
    """Return a per-thread requests session with retries (thread safe)."""
    s = getattr(_thread_local, "session", None)
    if s is None:
        s = requests.Session()
        retry = Retry(total=2, connect=2, read=1, backoff_factor=2,
                      status_forcelist=(502, 503, 504),
                      allowed_methods=("GET", "HEAD"))
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=4)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        s.headers["User-Agent"] = USER_AGENT
        _thread_local.session = s
    return s


def _clean_key(key):
    # Repairs keys like "amp;Request" that stem from double-escaped "&amp;"
    return re.sub(r"^(amp;)+", "", key, flags=re.I)


def split_url(url):
    """Split a URL into (base_without_query, kept_params, ogc_params)."""
    parts = urlsplit(url.strip())
    kept, ogc = [], {}
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        k = _clean_key(k)
        if k.lower() in OGC_REQUEST_PARAMS:
            ogc[k.lower()] = v
        else:
            kept.append((k, v))
    base = urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                       parts.path, "", ""))
    return base, kept, ogc


def service_base_url(url):
    """
    Base URL of a service as used for GetMap/GetFeature requests: the
    endpoint plus vendor parameters, without OGC request parameters.
    """
    base, kept, _ = split_url(url)
    if base.lower().endswith(".xml"):
        return base
    return base + ("?" + urlencode(kept) if kept else "")


def guess_service_type(url):
    """Best guess of the service type from the URL alone (may be wrong)."""
    base, _, ogc = split_url(url)
    svc = ogc.get("service", "").upper()
    if svc in SERVICE_TYPES:
        return svc
    low = url.lower()
    if base.lower().endswith(".xml") or "wmts" in low:
        return "WMTS"
    if "wfs" in low:
        return "WFS"
    return "WMS"


def capabilities_url(url, service_type=None):
    """Build a proper GetCapabilities URL for a service endpoint."""
    service_type = (service_type or guess_service_type(url)).upper()
    base, kept, ogc = split_url(url)
    if base.lower().endswith(".xml"):
        # RESTful WMTS capabilities document
        return base + ("?" + urlencode(kept) if kept else "")
    params = kept + [("SERVICE", service_type),
                     ("REQUEST", "GetCapabilities")]
    return base + "?" + urlencode(params)


def canonical_key(url, service_type=None):
    """Key used to detect duplicate endpoints."""
    service_type = (service_type or guess_service_type(url)).upper()
    base, kept, _ = split_url(url)
    base = base.replace("http://", "https://").rstrip("/?")
    kept = sorted((k.lower(), v) for k, v in kept)
    return "%s|%s|%s" % (service_type, base.lower(), urlencode(kept))


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def detect_service_type(root):
    """Return 'WMS', 'WMTS', 'WFS' or None for a capabilities XML root."""
    tag = _local(root.tag)
    ns = root.tag[1:].split("}")[0].lower() if root.tag.startswith("{") else ""
    if tag in ("WMS_Capabilities", "WMT_MS_Capabilities"):
        return "WMS"
    if tag == "WFS_Capabilities":
        return "WFS"
    if tag == "Capabilities" and "wmts" in ns:
        return "WMTS"
    return None


def normalise_version(service_type, version):
    """Map a capabilities version to one OWSLib can handle."""
    version = (version or "").strip()
    if service_type == "WMS":
        return version if version in ("1.1.1", "1.3.0") else (
            "1.1.1" if version.startswith("1.1") else "1.3.0")
    if service_type == "WMTS":
        return "1.0.0"
    if service_type == "WFS":
        if version.startswith("2."):
            return "2.0.0"
        if version.startswith("1.1"):
            return "1.1.0"
        if version.startswith("1.0"):
            return "1.0.0"
        return "2.0.0"
    return version or None


def exception_text(root):
    """Extract a readable message from an OGC exception report."""
    texts = [t.strip() for t in root.itertext() if t and t.strip()]
    return " ".join(texts)[:300] or _local(root.tag)


def fetch_capabilities(url, service_type=None, timeout=60):
    """
    Download and inspect a GetCapabilities document.

    Returns a dict with keys:
      ok (bool), type ('WMS'|'WMTS'|'WFS'|None), version (str|None),
      xml (bytes|None), url (requested URL), status (HTTP status|None),
      error (str|None), title (service title|None)
    """
    cap_url = capabilities_url(url, service_type)
    result = {"ok": False, "type": None, "version": None, "xml": None,
              "url": cap_url, "status": None, "error": None, "title": None,
              "fingerprint": None}
    try:
        resp = session().get(cap_url, timeout=timeout)
    except requests.exceptions.RequestException as e:
        result["error"] = "Connection failed: %s" % type(e).__name__
        if "timed out" in str(e).lower() or isinstance(
                e, requests.exceptions.Timeout):
            result["error"] = "Connection timed out"
        return result

    result["status"] = resp.status_code
    if resp.status_code != 200:
        result["error"] = ("GET request yielded HTTP response status code %s"
                           % resp.status_code)
        return result

    content = resp.content
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        snippet = re.sub(r"<[^>]+>", " ", resp.text[:2000])
        snippet = re.sub(r"\s+", " ", snippet).strip()[:160]
        result["error"] = ("Response is not valid XML (HTML error page?): %s"
                           % snippet)
        return result

    stype = detect_service_type(root)
    if stype is None:
        if "Exception" in _local(root.tag):
            result["error"] = "Service exception: %s" % exception_text(root)
        else:
            result["error"] = ("Unexpected capabilities root element <%s>"
                               % _local(root.tag))
        return result

    result.update(ok=True, type=stype, xml=content,
                  version=normalise_version(stype, root.attrib.get("version")))
    # Title for reports (namespace agnostic)
    for el in root.iter():
        if _local(el.tag) in ("Title",) and el.text and el.text.strip():
            result["title"] = el.text.strip()
            break
    result["fingerprint"] = content_fingerprint(root, stype, result["title"])
    return result


def content_fingerprint(root, service_type, title):
    """
    Fingerprint of a service's content: type, title, layer names and titles
    and the URLs the document advertises (OnlineResource, operation and
    ResourceURL links). Two URLs with the same fingerprint serve the same
    layers, e.g. a WMTS reachable via KVP and via its RESTful capabilities
    document. Including the advertised URLs keeps apart services whose layer
    lists are identical but whose data differs (e.g. yearly snapshots).
    """
    layers, links = [], set()
    xlink = "{http://www.w3.org/1999/xlink}href"
    for el in root.iter():
        href = el.attrib.get(xlink) or el.attrib.get("template")
        if href:
            base, kept, _ = split_url(href.strip())
            links.add((base.replace("http://", "https://").rstrip("/?")
                       + "?" + urlencode(sorted(kept))).lower())
        if _local(el.tag) not in ("Layer", "FeatureType"):
            continue
        name = layer_title = ""
        for child in el:
            tag = _local(child.tag)
            if tag in ("Name", "Identifier") and child.text:
                name = child.text.strip()
            elif tag == "Title" and child.text:
                layer_title = child.text.strip()
        if name:
            layers.append(name + "\x1f" + layer_title)
    if not layers:
        return None
    text = "\x1e".join([service_type, title or ""] + sorted(layers) +
                        sorted(links))
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def open_service(url, cap):
    """
    Create an OWSLib service object from a successful fetch_capabilities()
    result without downloading the document again.
    """
    from owslib.wfs import WebFeatureService
    from owslib.wms import WebMapService
    from owslib.wmts import WebMapTileService

    base = service_base_url(url)
    if cap["type"] == "WMS":
        return WebMapService(base, version=cap["version"], xml=cap["xml"],
                             timeout=60)
    if cap["type"] == "WMTS":
        return WebMapTileService(base, version="1.0.0", xml=cap["xml"],
                                 timeout=60)
    if cap["type"] == "WFS":
        return WebFeatureService(base, version=cap["version"],
                                 xml=cap["xml"], timeout=60)
    raise ValueError("Unknown service type %r" % cap["type"])
