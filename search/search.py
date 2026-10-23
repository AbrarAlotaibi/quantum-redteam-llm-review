#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reproducible literature search for the survey
"Quantum and quantum-inspired methods for LLMs, read through LLM red teaming".

This script only SEARCHES and RECORDS. It does not decide inclusion. It adds a
keyword-based `prescreen_flag` hint per record; `include` and
`exclusion_reason` are left empty for the authors.

Sources : OpenAlex works API, arXiv API, Semantic Scholar Graph API (bulk search)
Searches: S1 = Q AND L AND S (no year limit)
          S2 = Q AND L, 2018-2026
          S3 = Q AND S, 2018-2026, computer science
          S4 = Q AND G, 2018-2026, computer science or machine learning (cap 3000/source)

Usage (run from anywhere; paths are relative to this file):
    set PYTHONIOENCODING=utf-8
    python -I search.py fetch   [--sources openalex,arxiv,s2] [--searches S1,S2,S3,S4]
                                [--max-pages N] [--refresh]
    python -I search.py diagnose      # fetch metadata of the known check items (raw/diag_*)
    python -I search.py build         # parse raw/, dedup, flag, write outputs
    python -I search.py all           # fetch + diagnose + build

Raw API responses are cached in raw/. A fetch resumes from the cached pages and
does not re-request a completed source x search unless --refresh is given, so
`build` is fully reproducible offline from raw/.

Standard library only. No API keys. No e-mail address or other personal data
is sent (no mailto parameter, generic User-Agent).
"""

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
UA = "quantum-redteam-survey-literature-search/1.0 (Python-urllib)"

# --------------------------------------------------------------------------
# Query design
# --------------------------------------------------------------------------
GROUPS = OrderedDict([
    ("Q", ["quantum", "quantum-inspired", "quantum-enhanced", "hybrid quantum-classical",
           "variational quantum circuit", "parameterized quantum circuit", "Born machine",
           "tensor network", "quantum annealing", "QAOA", "QUBO", "HUBO", "Ising machine"]),
    ("L", ["large language model", "LLM", "language model", "natural language processing",
           "text generation", "language generation"]),
    ("G", ["generative model", "Born machine", "quantum GAN", "quantum diffusion",
           "quantum Boltzmann machine", "combinatorial optimization"]),
    ("S", ["red teaming", "jailbreak", "adversarial prompt", "adversarial attack",
           "attack strategy", "safety evaluation"]),
])
GROUP_NAMES = {"Q": "quantum", "L": "language anchor", "G": "generative/optimization components",
               "S": "security"}

SEARCHES = OrderedDict([
    ("S1", {"groups": ["Q", "L", "S"], "years": None, "field": None, "cap": None,
            "desc": "Q AND L AND S, no year limit"}),
    ("S2", {"groups": ["Q", "L"], "years": (2018, 2026), "field": None, "cap": None,
            "desc": "Q AND L, 2018-2026"}),
    ("S3", {"groups": ["Q", "S"], "years": (2018, 2026), "field": "cs", "cap": None,
            "desc": "Q AND S, 2018-2026, computer science"}),
    ("S4", {"groups": ["Q", "G"], "years": (2018, 2026), "field": "cs_ml", "cap": 3000,
            "desc": "Q AND G, 2018-2026, computer science or machine learning; first 3000 per source"}),
])
SAFETY_CAP = 10000          # never hit unless a search is far larger than expected (logged if hit)
SOURCES = ["openalex", "arxiv", "s2"]
SOURCE_LABEL = {"openalex": "OpenAlex", "arxiv": "arXiv", "s2": "Semantic Scholar"}

OA_BASE = "https://api.openalex.org/works"
OA_CS_FIELD = "17"          # OpenAlex topic-taxonomy field 17 = Computer Science
OA_SELECT = ("id,doi,display_name,publication_year,publication_date,type,ids,"
             "primary_location,locations,abstract_inverted_index,primary_topic")
OA_PER_PAGE = 200
AX_BASE = "https://export.arxiv.org/api/query"
AX_PAGE = 500
S2_BASE = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
S2_FIELDS = "title,year,venue,externalIds,abstract,publicationTypes"

KNOWN_ITEMS = [
    ("arxiv", "2510.24509", "QCR-LLM"),
    ("arxiv", "2503.12790", "QTHA"),
    ("arxiv", "2401.14109", "CompactifAI"),
    ("arxiv", "2407.00071", "combinatorial reasoning"),
    ("arxiv", "2607.12334", "QUBO RAG"),
    ("arxiv", "2509.16244", "QAA"),
    ("doi", "10.36227/techrxiv.177004376.69666864/v1", "TechRxiv survey"),
]


def qt(term):
    """Quote multi-word or hyphenated terms as phrases."""
    return '"%s"' % term if re.search(r"[\s\-]", term) else term


def openalex_boolean(sid):
    return " AND ".join("(" + " OR ".join(qt(t) for t in GROUPS[g]) + ")"
                        for g in SEARCHES[sid]["groups"])


def openalex_filter(sid):
    spec = SEARCHES[sid]
    f = "title_and_abstract.search:" + openalex_boolean(sid)
    if spec["years"]:
        f += ",publication_year:%d-%d" % spec["years"]
    if spec["field"] in ("cs", "cs_ml"):
        f += ",primary_topic.field.id:" + OA_CS_FIELD
    return f


def arxiv_query(sid):
    spec = SEARCHES[sid]
    parts = []
    for g in spec["groups"]:
        parts.append("(" + " OR ".join("ti:%s OR abs:%s" % (qt(t), qt(t)) for t in GROUPS[g]) + ")")
    q = " AND ".join(parts)
    if spec["years"]:
        q += " AND submittedDate:[%d01010000 TO %d12312359]" % spec["years"]
    if spec["field"] == "cs":
        q += " AND cat:cs.*"
    elif spec["field"] == "cs_ml":
        q += " AND (cat:cs.* OR cat:stat.ML)"
    return q


def s2_query(sid):
    return " + ".join("(" + " | ".join(qt(t) for t in GROUPS[g]) + ")"
                      for g in SEARCHES[sid]["groups"])


def s2_params(sid):
    spec = SEARCHES[sid]
    p = OrderedDict([("query", s2_query(sid)), ("fields", S2_FIELDS)])
    if spec["years"]:
        p["year"] = "%d-%d" % spec["years"]
    if spec["field"] in ("cs", "cs_ml"):
        p["fieldsOfStudy"] = "Computer Science"
    if spec["cap"]:
        # bulk search has no relevance ranking; most-cited first is used for the cap
        p["sort"] = "citationCount:desc"
    return p


def oa_params(sid, page=1):
    # Basic paging (page=N). Cursor paging past page 1 now needs an API key (HTTP 401), and
    # basic paging without a key is allowed for the first 10,000 results.
    return OrderedDict([("filter", openalex_filter(sid)), ("sort", "relevance_score:desc"),
                        ("per-page", str(OA_PER_PAGE)), ("page", str(page)), ("select", OA_SELECT)])


def ax_params(sid, start=0, n=AX_PAGE):
    return OrderedDict([("search_query", arxiv_query(sid)), ("start", str(start)),
                        ("max_results", str(n)), ("sortBy", "relevance"), ("sortOrder", "descending")])


def all_queries():
    out = OrderedDict()
    for sid, spec in SEARCHES.items():
        out[sid] = OrderedDict([
            ("description", spec["desc"]),
            ("groups", spec["groups"]),
            ("openalex", OrderedDict([
                ("endpoint", OA_BASE),
                ("filter", openalex_filter(sid)),
                ("title_and_abstract.search", openalex_boolean(sid)),
                ("other_params", OrderedDict([("sort", "relevance_score:desc"),
                                              ("per-page", str(OA_PER_PAGE)),
                                              ("page", "1, 2, ... (basic paging)"),
                                              ("select", OA_SELECT)])),
                ("first_page_url", OA_BASE + "?" + urllib.parse.urlencode(oa_params(sid))),
            ])),
            ("arxiv", OrderedDict([
                ("endpoint", AX_BASE),
                ("search_query", arxiv_query(sid)),
                ("other_params", OrderedDict([("start", "0, %d, ..." % AX_PAGE),
                                              ("max_results", str(AX_PAGE)),
                                              ("sortBy", "relevance"), ("sortOrder", "descending")])),
                ("first_page_url", AX_BASE + "?" + urllib.parse.urlencode(ax_params(sid))),
            ])),
            ("semantic_scholar", OrderedDict([
                ("endpoint", S2_BASE),
                ("query", s2_query(sid)),
                ("params", s2_params(sid)),
                ("first_page_url", S2_BASE + "?" + urllib.parse.urlencode(s2_params(sid), quote_via=urllib.parse.quote)),
            ])),
            ("cap_per_source", spec["cap"]),
        ])
    return out


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
_last_call = {}
MIN_INTERVAL = {"openalex": 0.25, "arxiv": 3.5, "s2": 1.5}


def utcnow():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_get(url, host, timeout=180):
    wait = _last_call.get(host, 0.0) + MIN_INTERVAL[host] - time.time()
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, headers, body = r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        status, headers = e.code, dict(e.headers or {})
    except Exception as e:  # timeouts, resets, DNS
        status, headers, body = -1, {}, repr(e).encode("utf-8")
    _last_call[host] = time.time()
    return status, headers, body


def say(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------
# Manifests and raw cache
# --------------------------------------------------------------------------
def man_path(tag):
    return os.path.join(RAW, tag + "_manifest.json")


def load_manifest(tag):
    p = man_path(tag)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


def save_manifest(tag, man):
    with open(man_path(tag), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2, ensure_ascii=False)


def new_manifest(source, sid, query_repr):
    return OrderedDict([("source", source), ("search", sid), ("query", query_repr),
                        ("reported_count", None), ("retrieved", 0), ("cap", SEARCHES[sid]["cap"] or SAFETY_CAP),
                        ("capped", False), ("complete", False), ("pages", []), ("problems", [])])


def clear_tag(tag):
    for fn in os.listdir(RAW):
        if fn.startswith(tag + "_"):
            os.remove(os.path.join(RAW, fn))


def write_raw(fn, body):
    with open(os.path.join(RAW, fn), "wb") as f:
        f.write(body)


# --------------------------------------------------------------------------
# Fetchers
# --------------------------------------------------------------------------
def fetch_openalex(sid, refresh=False, max_pages=None):
    tag = "openalex_%s" % sid
    if refresh:
        clear_tag(tag)
    man = load_manifest(tag) or new_manifest("openalex", sid, openalex_filter(sid))
    if man["complete"]:
        say("[openalex %s] cached, complete (%s/%s)" % (sid, man["retrieved"], man["reported_count"]))
        return man
    cap = man["cap"]
    more = True
    if man["pages"]:
        last = man["pages"][-1]
        more = last["n"] >= OA_PER_PAGE and (man["reported_count"] or 0) > len(man["pages"]) * OA_PER_PAGE
    sort_ok = True
    while more and man["retrieved"] < cap:
        if max_pages is not None and len(man["pages"]) >= max_pages:
            break
        page_no = len(man["pages"]) + 1
        if page_no * OA_PER_PAGE > 10000:
            man["problems"].append("basic paging limit (10,000 results) reached")
            break
        params = oa_params(sid, page_no)
        if not sort_ok:
            params.pop("sort")
        url = OA_BASE + "?" + urllib.parse.urlencode(params)
        status, headers, body = None, {}, b""
        for attempt in range(4):
            status, headers, body = http_get(url, "openalex")
            if status == 200:
                break
            msg = body[:300].decode("utf-8", "replace")
            man["problems"].append("%s HTTP %s on page %d attempt %d: %s" % (utcnow(), status, len(man["pages"]) + 1, attempt + 1, msg))
            say("[openalex %s] HTTP %s: %s" % (sid, status, msg[:160]))
            if status == 400 and sort_ok and "sort" in msg.lower():
                sort_ok = False
                params.pop("sort")
                url = OA_BASE + "?" + urllib.parse.urlencode(params)
                man["problems"].append("relevance sort rejected; continued without sort")
                continue
            if status == 429 or status >= 500 or status == -1:
                time.sleep(20 * (attempt + 1))
                continue
            break
        if status != 200:
            break
        j = json.loads(body.decode("utf-8"))
        fn = "%s_p%03d.json" % (tag, len(man["pages"]) + 1)
        write_raw(fn, body)
        res = j.get("results", []) or []
        meta = j.get("meta", {})
        if man["reported_count"] is None:
            man["reported_count"] = meta.get("count")
        man["pages"].append(OrderedDict([
            ("file", fn), ("url", url), ("status", status), ("fetched_utc", utcnow()), ("n", len(res)),
            ("cost_usd", headers.get("X-RateLimit-Cost-USD")),
            ("remaining_usd", headers.get("X-RateLimit-Remaining-USD"))]))
        man["retrieved"] = min(cap, man["retrieved"] + len(res))
        more = len(res) >= OA_PER_PAGE and (man["reported_count"] or 0) > page_no * OA_PER_PAGE
        save_manifest(tag, man)
        say("[openalex %s] page %d: %d records (reported %s, remaining budget USD %s)" % (
            sid, len(man["pages"]), len(res), man["reported_count"], headers.get("X-RateLimit-Remaining-USD")))
    man["capped"] = bool(man["reported_count"] and man["reported_count"] > cap and man["retrieved"] >= cap)
    man["complete"] = (not more) or man["retrieved"] >= cap
    man["paging"] = "basic page=N"
    man["sort"] ="relevance_score:desc" if sort_ok else "none"
    save_manifest(tag, man)
    return man


def arxiv_total(body_text):
    m = re.search(r"<opensearch:totalResults[^>]*>(\d+)</opensearch:totalResults>", body_text)
    return int(m.group(1)) if m else None


def fetch_arxiv(sid, refresh=False, max_pages=None):
    tag = "arxiv_%s" % sid
    if refresh:
        clear_tag(tag)
    man = load_manifest(tag) or new_manifest("arxiv", sid, arxiv_query(sid))
    if man["complete"]:
        say("[arxiv %s] cached, complete (%s/%s)" % (sid, man["retrieved"], man["reported_count"]))
        return man
    cap = man["cap"]
    start = sum(p["n"] for p in man["pages"])
    total = man["reported_count"]
    stalled = False
    while True:
        if total is not None and start >= min(total, cap):
            break
        if max_pages is not None and len(man["pages"]) >= max_pages:
            break
        n_req = AX_PAGE if total is None else min(AX_PAGE, min(total, cap) - start)
        url = AX_BASE + "?" + urllib.parse.urlencode(ax_params(sid, start, n_req))
        ok = False
        for attempt in range(7):
            status, headers, body = http_get(url, "arxiv")
            text = body.decode("utf-8", "replace")
            n_entries = text.count("<entry>") + text.count("<entry ")
            t = arxiv_total(text) if status == 200 else None
            if status == 200 and t is not None and (n_entries > 0 or t <= start):
                ok = True
                break
            why = "HTTP %s" % status if status != 200 else "empty/short body (entries=%d, total=%s)" % (n_entries, t)
            man["problems"].append("%s %s at start=%d attempt %d" % (utcnow(), why, start, attempt + 1))
            say("[arxiv %s] %s at start=%d; backing off" % (sid, why, start))
            time.sleep(min(60, 30 + 10 * attempt))
        if not ok:
            stalled = True
            break
        fn = "%s_p%03d.xml" % (tag, len(man["pages"]) + 1)
        write_raw(fn, body)
        if total is None:
            total = t
            man["reported_count"] = t
        man["pages"].append(OrderedDict([("file", fn), ("url", url), ("status", status),
                                         ("fetched_utc", utcnow()), ("start", start), ("n", n_entries),
                                         ("totalResults_on_page", t)]))
        start += n_entries
        man["retrieved"] = min(cap, start)
        save_manifest(tag, man)
        say("[arxiv %s] page %d: %d entries (start now %d, reported %s)" % (sid, len(man["pages"]), n_entries, start, total))
        if n_entries == 0:
            break
    man["capped"] = bool(total and total > cap and man["retrieved"] >= cap)
    man["complete"] = (not stalled) and total is not None and man["retrieved"] >= min(total, cap)
    if not man["complete"] and not stalled and total is not None and max_pages is None:
        man["problems"].append("arXiv returned fewer entries than totalResults; stopped at %d" % man["retrieved"])
        man["complete"] = True
    save_manifest(tag, man)
    return man


S2_BACKOFF = [30, 60, 90, 120, 180, 240, 300, 300, 300, 300, 300, 300]


def fetch_s2(sid, refresh=False, max_pages=None):
    tag = "s2_%s" % sid
    if refresh:
        clear_tag(tag)
    man = load_manifest(tag) or new_manifest("s2", sid, s2_query(sid))
    man["params"] = s2_params(sid)
    if man["complete"]:
        say("[s2 %s] cached, complete (%s/%s)" % (sid, man["retrieved"], man["reported_count"]))
        return man
    cap = man["cap"]
    token = None
    started = bool(man["pages"])
    if started:
        with open(os.path.join(RAW, man["pages"][-1]["file"]), encoding="utf-8") as f:
            token = json.load(f).get("token")
    stalled = False
    while (not started or token) and man["retrieved"] < cap:
        if max_pages is not None and len(man["pages"]) >= max_pages:
            break
        params = s2_params(sid)
        if token:
            params["token"] = token
        url = S2_BASE + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        ok = False
        for attempt in range(len(S2_BACKOFF)):
            status, headers, body = http_get(url, "s2")
            if status == 200:
                ok = True
                break
            msg = body[:200].decode("utf-8", "replace")
            man["problems"].append("%s HTTP %s attempt %d: %s" % (utcnow(), status, attempt + 1, msg))
            say("[s2 %s] HTTP %s; backing off %ds" % (sid, status, S2_BACKOFF[attempt]))
            if status in (400, 404):
                break
            time.sleep(S2_BACKOFF[attempt])
        if not ok:
            stalled = True
            break
        started = True
        j = json.loads(body.decode("utf-8"))
        fn = "%s_p%03d.json" % (tag, len(man["pages"]) + 1)
        write_raw(fn, body)
        data = j.get("data") or []
        if man["reported_count"] is None:
            man["reported_count"] = j.get("total")
        man["pages"].append(OrderedDict([("file", fn), ("url", url), ("status", status),
                                         ("fetched_utc", utcnow()), ("n", len(data)), ("total_on_page", j.get("total"))]))
        man["retrieved"] = min(cap, man["retrieved"] + len(data))
        token = j.get("token")
        save_manifest(tag, man)
        say("[s2 %s] page %d: %d records (reported %s)" % (sid, len(man["pages"]), len(data), man["reported_count"]))
        if not data:
            token = None
    man["capped"] = bool(man["reported_count"] and man["reported_count"] > cap and man["retrieved"] >= cap)
    man["complete"] = (not stalled) and started and (token is None or man["retrieved"] >= cap)
    save_manifest(tag, man)
    return man


FETCHERS = {"openalex": fetch_openalex, "arxiv": fetch_arxiv, "s2": fetch_s2}


# --------------------------------------------------------------------------
# Known-item diagnostics (only metadata of the named check items)
# --------------------------------------------------------------------------
def diagnose():
    ax_ids = [k for t, k, _ in KNOWN_ITEMS if t == "arxiv"]
    fn = os.path.join(RAW, "diag_arxiv_known_items.xml")
    if not os.path.exists(fn):
        url = AX_BASE + "?" + urllib.parse.urlencode({"id_list": ",".join(ax_ids), "max_results": str(len(ax_ids))})
        for attempt in range(6):
            status, _, body = http_get(url, "arxiv")
            if status == 200 and b"<entry" in body:
                write_raw(os.path.basename(fn), body)
                say("[diag] arXiv known items fetched")
                break
            say("[diag] arXiv HTTP %s; backing off" % status)
            time.sleep(30 + 10 * attempt)
    for t, k, label in KNOWN_ITEMS:
        if t != "doi":
            continue
        fn = os.path.join(RAW, "diag_s2_doi_%s.json" % re.sub(r"[^A-Za-z0-9]+", "_", k))
        if os.path.exists(fn):
            continue
        url = ("https://api.semanticscholar.org/graph/v1/paper/DOI:" + urllib.parse.quote(k, safe="/")
               + "?fields=" + S2_FIELDS)
        for attempt in range(8):
            status, _, body = http_get(url, "s2")
            if status in (200, 404):
                write_raw(os.path.basename(fn), body)
                say("[diag] S2 DOI lookup %s -> HTTP %s" % (k, status))
                break
            say("[diag] S2 HTTP %s; backing off %ds" % (status, S2_BACKOFF[attempt]))
            time.sleep(S2_BACKOFF[attempt])


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------
def clean_ws(s):
    return re.sub(r"\s+", " ", s or "").strip()


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "")


def norm_doi(d):
    d = (d or "").strip()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", d, flags=re.I)
    return d.lower()


def doi_key(d):
    return re.sub(r"/v\d+$", "", norm_doi(d))


ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(.+)$", re.I)
ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([a-z\-]+(?:\.[a-z]{2})?/\d{7}|\d{4}\.\d{4,5})", re.I)


def norm_arxiv(a):
    a = (a or "").strip().lower()
    a = re.sub(r"^(arxiv:|https?://(export\.)?arxiv\.org/(abs|pdf)/)", "", a)
    a = re.sub(r"\.pdf$", "", a)
    a = re.sub(r"v\d+$", "", a)
    return a


def norm_title(t):
    t = unicodedata.normalize("NFKD", strip_tags(t or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def oa_abstract(inv):
    if not inv:
        return ""
    pos = []
    for w, idxs in inv.items():
        for i in idxs:
            pos.append((i, w))
    pos.sort()
    return " ".join(w for _, w in pos)


DOI_PREFIX_BUCKET = OrderedDict([
    ("10.1109", "IEEE"), ("10.1145", "ACM"), ("10.1016", "Elsevier (ScienceDirect)"),
    ("10.18653", "ACL Anthology"), ("10.36227", "TechRxiv"), ("10.48550", "arXiv DOI"),
    ("10.1007", "Springer Nature"), ("10.1038", "Springer Nature"), ("10.1186", "Springer Nature"),
    ("10.3390", "MDPI"), ("10.1103", "APS"), ("10.1088", "IOP"), ("10.1063", "AIP"),
    ("10.1002", "Wiley"), ("10.1111", "Wiley"), ("10.1117", "SPIE"), ("10.2139", "SSRN"),
    ("10.21203", "Research Square"), ("10.20944", "Preprints.org"), ("10.22331", "Quantum (journal)"),
    ("10.1080", "Taylor & Francis"), ("10.1093", "Oxford UP"), ("10.3389", "Frontiers"),
    ("10.1049", "IET"), ("10.1371", "PLOS"), ("10.1126", "Science/AAAS"), ("10.1073", "PNAS"),
    ("10.5281", "Zenodo"), ("10.31219", "OSF Preprints"), ("10.26434", "ChemRxiv"),
    ("10.1609", "AAAI"), ("10.24963", "IJCAI"), ("10.1142", "World Scientific"),
    ("10.1515", "De Gruyter"), ("10.1051", "EDP Sciences"), ("10.1364", "Optica"),
    ("10.1021", "ACS"), ("10.1039", "RSC"), ("10.1177", "SAGE"), ("10.1155", "Hindawi/Wiley"),
    ("10.32604", "Tech Science Press"), ("10.14569", "IJACSA (SAI)"), ("10.1162", "MIT Press"),
])


def publisher_bucket(dois, landing_urls, source_host):
    for d in dois:
        p = norm_doi(d).split("/")[0]
        if p in DOI_PREFIX_BUCKET and p != "10.48550":
            return DOI_PREFIX_BUCKET[p]
    for u in landing_urls:
        if "aclanthology.org" in (u or ""):
            return "ACL Anthology"
    for u in landing_urls:
        if "techrxiv.org" in (u or ""):
            return "TechRxiv"
    if any(norm_doi(d).startswith("10.48550/") for d in dois) or any("arxiv.org" in (u or "") for u in landing_urls):
        return "arXiv (no publisher DOI)"
    if dois:
        return "other DOI prefix"
    if source_host:
        return "no DOI: " + source_host
    return "no DOI, unknown host"


def parse_openalex(man):
    recs = []
    rank = 0
    for p in man["pages"]:
        with open(os.path.join(RAW, p["file"]), encoding="utf-8") as f:
            j = json.load(f)
        for w in j.get("results", []) or []:
            rank += 1
            if rank > man["cap"]:
                break
            dois, axs, urls = [], [], []
            if w.get("doi"):
                dois.append(norm_doi(w["doi"]))
            for loc in ([w.get("primary_location")] + (w.get("locations") or [])):
                if not loc:
                    continue
                for u in (loc.get("landing_page_url"), loc.get("pdf_url")):
                    if u:
                        urls.append(u)
                        m = ARXIV_URL_RE.search(u)
                        if m:
                            axs.append(norm_arxiv(m.group(1)))
                if loc.get("doi"):
                    dd = norm_doi(loc["doi"])
                    if dd not in dois:
                        dois.append(dd)
            for d in list(dois):
                m = ARXIV_DOI_RE.match(d)
                if m:
                    axs.append(norm_arxiv(m.group(1)))
            pl = w.get("primary_location") or {}
            src = pl.get("source") or {}
            venue = src.get("display_name") or pl.get("raw_source_name") or ""
            recs.append({
                "source": "openalex", "search": man["search"], "rank": rank,
                "native_id": w.get("id"), "title": clean_ws(strip_tags(w.get("display_name") or "")),
                "year": w.get("publication_year"), "venue": clean_ws(venue),
                "dois": dois, "arxiv_ids": sorted(set(a for a in axs if a)),
                "url": w.get("id"), "abstract": clean_ws(oa_abstract(w.get("abstract_inverted_index"))),
                "type": w.get("type"),
                "publisher_bucket": publisher_bucket(dois, urls, src.get("host_organization_name")),
                "primary_field": ((w.get("primary_topic") or {}).get("field") or {}).get("display_name"),
            })
    return recs


ATOM = "{http://www.w3.org/2005/Atom}"
ARX = "{http://arxiv.org/schemas/atom}"


def parse_arxiv_entries(path):
    out = []
    root = ET.parse(path).getroot()
    for e in root.findall(ATOM + "entry"):
        rid = (e.findtext(ATOM + "id") or "").strip()
        m = re.search(r"arxiv\.org/abs/(.+)$", rid)
        if not m:
            continue
        aid = norm_arxiv(m.group(1))
        pub = (e.findtext(ATOM + "published") or "")[:4]
        doi = (e.findtext(ARX + "doi") or "").strip()
        jref = clean_ws(e.findtext(ARX + "journal_ref") or "")
        pc = e.find(ARX + "primary_category")
        cats = [c.get("term") for c in e.findall(ATOM + "category")]
        out.append({
            "arxiv_id": aid, "title": clean_ws(e.findtext(ATOM + "title")),
            "abstract": clean_ws(e.findtext(ATOM + "summary")),
            "year": int(pub) if pub.isdigit() else None,
            "doi": norm_doi(doi) if doi else "", "journal_ref": jref,
            "primary_category": pc.get("term") if pc is not None else "", "categories": cats,
        })
    return out


def parse_arxiv(man):
    recs = []
    rank = 0
    for p in man["pages"]:
        for e in parse_arxiv_entries(os.path.join(RAW, p["file"])):
            rank += 1
            if rank > man["cap"]:
                break
            dois = [e["doi"]] if e["doi"] else []
            venue = ("arXiv (%s); %s" % (e["primary_category"], e["journal_ref"])) if e["journal_ref"] else "arXiv (%s)" % e["primary_category"]
            recs.append({
                "source": "arxiv", "search": man["search"], "rank": rank, "native_id": e["arxiv_id"],
                "title": e["title"], "year": e["year"], "venue": venue, "dois": dois,
                "arxiv_ids": [e["arxiv_id"]], "url": "https://arxiv.org/abs/" + e["arxiv_id"],
                "abstract": e["abstract"], "type": "preprint",
                "publisher_bucket": publisher_bucket(dois, ["arxiv.org"], None),
            })
    return recs


def parse_s2(man):
    recs = []
    rank = 0
    for p in man["pages"]:
        with open(os.path.join(RAW, p["file"]), encoding="utf-8") as f:
            j = json.load(f)
        for d in j.get("data") or []:
            rank += 1
            if rank > man["cap"]:
                break
            ext = d.get("externalIds") or {}
            dois = [norm_doi(ext["DOI"])] if ext.get("DOI") else []
            axs = [norm_arxiv(ext["ArXiv"])] if ext.get("ArXiv") else []
            for dd in dois:
                m = ARXIV_DOI_RE.match(dd)
                if m:
                    axs.append(norm_arxiv(m.group(1)))
            recs.append({
                "source": "s2", "search": man["search"], "rank": rank, "native_id": d.get("paperId"),
                "title": clean_ws(d.get("title")), "year": d.get("year"), "venue": clean_ws(d.get("venue")),
                "dois": dois, "arxiv_ids": sorted(set(axs)),
                "url": "https://www.semanticscholar.org/paper/%s" % d.get("paperId"),
                "abstract": clean_ws(d.get("abstract")), "type": ",".join(d.get("publicationTypes") or []),
                "publisher_bucket": publisher_bucket(dois, [], None),
            })
    return recs


PARSERS = {"openalex": parse_openalex, "arxiv": parse_arxiv, "s2": parse_s2}


# --------------------------------------------------------------------------
# Deduplication: DOI, then arXiv id, then normalized title (union-find)
# --------------------------------------------------------------------------
TITLE_MIN_LEN = 30      # normalized-title merging only for titles >= 30 characters
TITLE_MAX_YEAR_GAP = 2  # ... and only if both years are known and differ by <= 2 (or a year is missing)


def dedup(recs):
    parent = list(range(len(recs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    stats = Counter()

    def union(a, b, kind):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
            stats[kind] += 1

    for kind in ("doi", "arxiv", "title"):
        seen = {}
        for i, r in enumerate(recs):
            if kind == "doi":
                keys = [doi_key(d) for d in r["dois"] if not ARXIV_DOI_RE.match(d)]
            elif kind == "arxiv":
                keys = r["arxiv_ids"]
            else:
                nt = norm_title(r["title"])
                keys = [nt] if len(nt) >= TITLE_MIN_LEN else []
            for k in keys:
                if k in seen:
                    j = seen[k]
                    if kind == "title":
                        ya, yb = recs[i]["year"], recs[j]["year"]
                        if ya and yb and abs(ya - yb) > TITLE_MAX_YEAR_GAP:
                            stats["title_skipped_year_gap"] += 1
                            continue
                    union(j, i, kind)
                else:
                    seen[k] = i
    groups = defaultdict(list)
    for i in range(len(recs)):
        groups[find(i)].append(recs[i])
    return list(groups.values()), stats


SRC_ORDER = {"openalex": 0, "arxiv": 2, "s2": 1}
SRC_TAG = {"openalex": "openalex", "arxiv": "arxiv", "s2": "semanticscholar"}


def is_arxiv_venue(v):
    return (not v) or v.lower().startswith("arxiv")


def merge_group(g):
    g = sorted(g, key=lambda r: (SRC_ORDER[r["source"]], r["search"], r["rank"]))
    dois, axs = [], []
    for r in g:
        for d in r["dois"]:
            if ARXIV_DOI_RE.match(d):
                continue
            if d not in dois:
                dois.append(d)
        for a in r["arxiv_ids"]:
            if a not in axs:
                axs.append(a)
    title = next((r["title"] for r in g if r["title"]), "")
    years = [r["year"] for r in g if r["year"]]
    venue = next((r["venue"] for r in g if r["venue"] and not is_arxiv_venue(r["venue"])), "")
    if not venue:
        venue = next((r["venue"] for r in g if r["source"] == "arxiv" and r["venue"]), "") or \
            next((r["venue"] for r in g if r["venue"]), "")
    abstract = max((r["abstract"] for r in g), key=len, default="")
    if dois:
        url = "https://doi.org/" + dois[0]
    elif axs:
        url = "https://arxiv.org/abs/" + axs[0]
    else:
        url = g[0]["url"]
    found = OrderedDict()
    for src in ("openalex", "arxiv", "s2"):
        ss = sorted(set(r["search"] for r in g if r["source"] == src))
        if ss:
            found[src] = ss
    sources = "; ".join("%s:%s" % (SRC_TAG[s], ",".join(v)) for s, v in found.items())
    searches = sorted(set(r["search"] for r in g))
    if dois:
        pkey = "doi:" + sorted(doi_key(d) for d in dois)[0]
    elif axs:
        pkey = "arxiv:" + sorted(axs)[0]
    else:
        pkey = "title:" + norm_title(title)
    uid = "QRS-" + hashlib.sha1(pkey.encode("utf-8")).hexdigest()[:10]
    return {
        "uid": uid, "title": title, "year": min(years) if years else "", "venue": venue,
        "doi": "; ".join(dois), "arxiv_id": "; ".join(axs), "url": url, "sources": sources,
        "abstract_full": abstract, "searches": searches, "found": found, "n_records": len(g),
        "doi_keys": set(doi_key(d) for d in dois), "arxiv_set": set(axs),
    }


# --------------------------------------------------------------------------
# Pre-screen flag (heuristic hint only; applied in this priority order)
# --------------------------------------------------------------------------
FLAG_ORDER = ["post_quantum_crypto", "llm_for_quantum", "quantum_ml_robustness", "likely_relevant", "other"]

RX = OrderedDict()
# language anchor (L group plus obvious variants)
RX["L"] = re.compile(r"\b(large language models?|llms?|language models?|language modell?ing|"
                     r"natural language processing|nlp|text generation|language generation|"
                     r"chatgpt|gpt-?[2345o]\w*|generative pre-?trained transformers?)\b", re.I)
# quantum *method* (not just the word 'quantum', which also appears in 'quantum dot', 'quantum yield', ...)
RX["QM"] = re.compile(
    r"(quantum[- ]inspired|quantum[- ]enhanced|hybrid quantum|quantum[- ]classical|variational quantum|"
    r"parameteri[sz]ed quantum|parametri[sz]ed quantum|born machines?|tensor[- ]networks?|matrix product (states?|operators?)|"
    r"tensor[- ]train|quantum anneal\w*|\bqaoa\b|\bqubo\b|\bhubo\b|ising machines?|\bqubits?\b|\bnisq\b|"
    r"\bqnlp\b|discocat|discocirc|lambeq|\bqml\b|\bqnns?\b|\bvqcs?\b|\bvqe\b|"
    r"quantum (comput\w*|circuits?|algorithms?|machine learning|neural|natural language|nlp|kernels?|hardware|"
    r"processors?|devices?|advantage|walks?|approximate optimi[sz]ation|boltzmann|gans?|generative|diffusion|"
    r"transformers?|attention|embeddings?|optimi[sz]\w*|sampl\w*|reservoir|probabilit\w*|cognition|"
    r"-like|software|program\w*|search|learning|models? of|language models?|large language|llms?|"
    r"classifiers?|feature|encod\w*|superposition|entangle\w*|interference|state space|annealers?|simulat\w*))",
    re.I)
RX["PQC"] = re.compile(
    r"(post[- ]?quantum|quantum[- ](safe|resistant|resilient|secure|proof)\b|lattice[- ]based (crypt\w*|signature\w*|encryption|scheme\w*)|"
    r"\bkyber\b|dilithium|\bml-kem\b|\bml-dsa\b|sphincs|crystals-|ntru\b|quantum key distribution|"
    r"quantum cryptograph\w*|quantum-secure communication|quantum secure direct communication)", re.I)
RX["LFQ"] = re.compile(
    r"(\bqiskit\b|openqasm|\bqasm\b|\bcirq\b|pennylane|"
    r"quantum (code|codes|programs?|programming|software|compil\w*|circuit (design|generation|synthesis|compilation|optimi[sz]ation|discovery))|"
    r"(generat\w*|design\w*|synthesi\w*|writ\w*|compos\w*|construct\w*|discover\w*|translat\w*)\s+(\w+\s+){0,3}quantum (circuits?|programs?|algorithms?|code)\b|"
    r"\b(llms?|language models?|agents?)\s+(for|in|to)\s+(\w+\s+){0,2}quantum (computing|software|programming|circuits?|chemistry|physics|"
    r"simulations?|experiments?|research|science|information|error correction|hardware|architectures?|algorithms?|code|mechanics|many-body)|"
    r"quantum (circuits?|programs?|code|algorithms?)\s+(\w+\s+){0,2}(using|with|via|by)\s+(\w+\s+){0,2}(llms?|large language models?|language models?|gpt\w*))",
    re.I)
# attack terms; bare "adversarial" is NOT enough (it would catch every quantum GAN)
RX["ADV"] = re.compile(
    r"(adversarial (attacks?|examples?|perturbations?|robustness|samples?|inputs?|manipulations?|noise|"
    r"vulnerab\w*|defen[cs]es?|threats?|machine learning|regime|setting|scenario\w*)|"
    r"\battacks?\b|\battacker\w*|poison\w*|backdoor\w*|evasion)", re.I)
# quantum methods applied TO language (QNLP, quantum-enhanced LLM components): exempt from llm_for_quantum
RX["Q4L"] = re.compile(
    r"(\bqnlp\b|quantum natural language|discocat|discocirc|lambeq|"
    r"quantum[- ](inspired|enhanced|assisted|native|classical)\s+(\w+[- ]){0,2}(llms?|large language models?|language models?|"
    r"transformers?|nlp|text|fine-?tuning|adapters?|lora)\b|"
    r"hybrid quantum[- ]classical\s+(\w+[- ]){0,2}(llms?|large language models?|language models?|transformers?|nlp|text|"
    r"sentences?|words?|semantic\w*|linguistic\w*)\b|"
    r"quantum (transformers?|self-attention|attention mechanisms?|word embeddings?|language models?|large language models?|"
    r"fine-?tuning|adapters?|lora|text classif\w*|sentiment|sentence\w*)\b|"
    r"(llms?|large language models?|language models?)\s+(\w+\s+){0,2}(using|with|via) (\w+[- ]){0,2}(quantum|tensor[- ]networks?)\b)",
    re.I)
RX["QML_TARGET"] = re.compile(
    r"(quantum (machine learning|classifiers?|neural networks?|learning models?|models?|kernels?|support vector|"
    r"convolutional|image classif\w*|learning)|\bqml\b|\bqnns?\b|\bqcnns?\b|\bvqcs?\b|variational quantum (classifiers?|circuits?|algorithms?)|"
    r"parameteri[sz]ed quantum circuits?)", re.I)
RX["SEC_LLM"] = re.compile(r"(jailbreak\w*|red[- ]team\w*|adversarial prompts?|prompt injection)", re.I)
# calls for papers / front matter whose topic lists mention everything
RX["CFP"] = re.compile(r"^\s*((\d+(st|nd|rd|th)|[ivxl]+)\s+)?(international |annual )?(conference|workshop|symposium|congress)\b|"
                       r"call for (papers|chapters|submissions)|^\s*(preface|front matter|table of contents|editorial)\s*$", re.I)


def _lang_or_sec(s):
    return bool(RX["L"].search(s) or RX["SEC_LLM"].search(s))


def _cooccur(title, sents, test_a, test_b):
    """True if a and b occur in one sentence, or one of them is in the title (and the other anywhere)."""
    return (any(test_a(s) and test_b(s) for s in sents)
            or (test_a(title) and any(test_b(s) for s in sents))
            or (test_b(title) and any(test_a(s) for s in sents)))


def prescreen(title, abstract):
    title = title or ""
    text = "%s. %s" % (title, abstract or "")
    sents = re.split(r"(?<=[.!?;])\s+", text)
    has_l = bool(RX["L"].search(text))
    # 1. crypto: PQC/QKD term in the title, or at least two PQC/QKD mentions
    if RX["PQC"].search(title) or len(RX["PQC"].findall(text)) >= 2:
        return "post_quantum_crypto"
    # 2. LLM used for quantum programs/circuits (not when the text is about quantum methods for language)
    if (has_l and not RX["Q4L"].search(text)
            and _cooccur(title, sents, lambda s: bool(RX["L"].search(s)), lambda s: bool(RX["LFQ"].search(s)))):
        return "llm_for_quantum"
    # 3. attacks on quantum classifiers (no language anchor)
    if (not has_l) and RX["ADV"].search(text) and RX["QML_TARGET"].search(text):
        return "quantum_ml_robustness"
    # 4. quantum-method term and language/LLM-security term in one sentence, or one of them in the title
    #    (not for calls for papers / front matter)
    if (not RX["CFP"].search(title)
            and _cooccur(title, sents, lambda s: bool(RX["QM"].search(s)), _lang_or_sec)):
        return "likely_relevant"
    return "other"


PRESCREEN_RULES_MD = """Rules are applied in this order to `title + abstract` (the full abstract, before truncation); the first rule that fires sets the flag. Matching is case-insensitive regular expressions defined in `search.py` (`RX`).

"Co-occur" below means that the two terms appear in the same sentence, or that one of them is in the title and the other appears anywhere.

1. **post_quantum_crypto** fires when `RX["PQC"]` matches in the title, or matches at least twice in title + abstract. A single passing mention does not fire it. `RX["PQC"]` covers post-quantum, quantum-safe, quantum-resistant, quantum-resilient, quantum-secure, quantum-proof, lattice-based cryptography, signature or encryption schemes, Kyber, Dilithium, ML-KEM, ML-DSA, SPHINCS, CRYSTALS and NTRU. It also catches **quantum cryptography and QKD** (quantum key distribution, quantum secure direct communication), which are equally off-topic for this survey. The bare abbreviations "PQC" and "QKD" are deliberately not used, because they collide with "parameterized quantum circuit (PQC)" and "quantum kernel discriminator (QKD)".
2. **llm_for_quantum** fires when three conditions hold:
   - A language-anchor term (`RX["L"]`) co-occurs with an LLM-for-quantum term (`RX["LFQ"]`). `RX["L"]` covers LLM(s), (large) language model(s), NLP, natural language processing, text generation, language generation, ChatGPT and GPT-n.
   - `RX["LFQ"]` matches any of these:
     - the tool and language names Qiskit, OpenQASM, QASM, Cirq and PennyLane;
     - "quantum code", "quantum program(ming)", "quantum software", "quantum compiler";
     - "quantum circuit" followed by design, generation, synthesis, compilation, optimization or discovery;
     - generate, design, synthesize, write, compose, construct, discover or translate, then up to three words, then quantum circuits, programs, algorithms or code;
     - "LLM(s)", "language model(s)" or "agent(s)", then for, in or to, then a quantum field such as computing, software, programming, circuits, chemistry, physics, simulation or error correction;
     - quantum circuits, programs, code or algorithms, then using, with, via or by, then an LLM, language model or GPT.
   - The text does **not** match `RX["Q4L"]`, the quantum-methods-for-language markers. These are QNLP, quantum natural language, DisCoCat, DisCoCirc and lambeq; quantum-inspired, quantum-enhanced, quantum-assisted or hybrid quantum-classical followed by LLM, language model, transformer, NLP, text, sentence, fine-tuning or adapter; quantum transformer, attention, word embedding, language model, fine-tuning, adapter, LoRA, text classification or sentiment; and an LLM or language model "using", "with" or "via" a quantum method or tensor networks. Without this exemption, QNLP papers that "construct quantum circuits from sentences in Qiskit" would be mislabelled.
3. **quantum_ml_robustness**: **no** language-anchor term, **and** an attack term (`RX["ADV"]`: adversarial attacks, examples, perturbations, robustness, samples, inputs, noise, threats or defence, plus attack(s), attacker, poisoning, backdoor and evasion; a bare "adversarial" is not enough, so quantum GANs are not caught) **and** a quantum-model target (`RX["QML_TARGET"]`: quantum machine learning / classifier / neural network / model / kernel / SVM / convolutional / image classification / learning, QML, QNN, QCNN, VQC, variational quantum classifier|circuit|algorithm, parameterized quantum circuit).
4. **likely_relevant**: a quantum-*method* term (`RX["QM"]`: quantum-inspired, quantum-enhanced, hybrid quantum(-classical), variational/parameterized quantum, Born machine, tensor network, matrix product state/operator, tensor train, quantum annealing, QAOA, QUBO, HUBO, Ising machine, qubit, NISQ, QNLP, DisCoCat/DisCoCirc, lambeq, QML, QNN, VQC, VQE, or "quantum" followed by a computing word such as computing, circuit, algorithm, machine learning, neural, natural language, kernel, hardware, advantage, walk, Boltzmann, GAN, generative, diffusion, transformer, attention, embedding, optimization, sampling, reservoir, probability, cognition, -like, software, search, learning, language model, LLM, classifier, encoding, superposition, entanglement, interference, annealer, simulation) **co-occurring** with either a language-anchor term or an LLM-security term (`RX["SEC_LLM"]`: jailbreak, red team(ing), adversarial prompt, prompt injection). A bare "quantum" (e.g. "quantum dot", "quantum yield", "quantum chemistry") does not satisfy the quantum-method test. Records whose title looks like a call for papers or front matter (`RX["CFP"]`: "Nth International Conference/Workshop/Symposium ...", "call for papers", "Preface", "Front matter", "Editorial") are never flagged likely_relevant, because their topic lists mention every term.
5. **other**: everything else. Note that S4-only records (quantum generative / optimization models that do not mention language) will mostly be flagged `other` by construction; the flag says nothing about their value as candidate components and they still need screening on their own terms.

The flag is a sorting hint for the screeners, never an inclusion or exclusion decision."""


# --------------------------------------------------------------------------
# Group-term matcher used only for the known-item diagnostics
# --------------------------------------------------------------------------
def term_regex(term):
    parts = re.split(r"[\s\-]+", term)
    return re.compile(r"\b" + r"[\s\-]+".join(re.escape(p) for p in parts) + r"\w*", re.I)


GROUP_RX = {g: [(t, term_regex(t)) for t in terms] for g, terms in GROUPS.items()}


def group_hits(text):
    return {g: [t for t, rx in lst if rx.search(text)] for g, lst in GROUP_RX.items()}


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def load_all():
    mans, recs = {}, []
    for src in SOURCES:
        for sid in SEARCHES:
            man = load_manifest("%s_%s" % (src, sid))
            mans[(src, sid)] = man
            if man and man["pages"]:
                recs.extend(PARSERS[src](man))
    return mans, recs


def truncate(s, n=600):
    s = s or ""
    return s if len(s) <= n else s[: n - 3].rstrip() + "..."


def build():
    mans, recs = load_all()
    groups, dstats = dedup(recs)
    rows = [merge_group(g) for g in groups]
    for r in rows:
        r["prescreen_flag"] = prescreen(r["title"], r["abstract_full"])
    rows.sort(key=lambda r: (min(r["searches"]), -(r["year"] or 0), norm_title(r["title"])))
    # uid collision guard
    seen = Counter()
    for r in rows:
        seen[r["uid"]] += 1
        if seen[r["uid"]] > 1:
            r["uid"] += "-%d" % seen[r["uid"]]

    cols = ["uid", "title", "year", "venue", "doi", "arxiv_id", "url", "sources", "abstract",
            "prescreen_flag", "include", "exclusion_reason"]
    with open(os.path.join(BASE, "candidates.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(cols)
        for r in rows:
            w.writerow([r["uid"], r["title"], r["year"], r["venue"], r["doi"], r["arxiv_id"], r["url"],
                        r["sources"], truncate(r["abstract_full"]), r["prescreen_flag"], "", ""])

    with open(os.path.join(BASE, "queries.json"), "w", encoding="utf-8") as f:
        json.dump(OrderedDict([("generated_utc", utcnow()), ("term_groups", GROUPS),
                               ("searches", all_queries())]), f, indent=2, ensure_ascii=False)

    known = known_item_check(rows)
    write_log(mans, recs, rows, dstats, known)
    write_manual_queries()
    flags = Counter(r["prescreen_flag"] for r in rows)
    say("records parsed: %d; unique: %d" % (len(recs), len(rows)))
    say("flags: %s" % dict(flags))
    for k in known:
        say("known item %s (%s): %s" % (k["id"], k["label"], "FOUND " + k["uid"] if k["found"] else "not found"))
    return rows


def known_item_check(rows):
    by_ax, by_doi = {}, {}
    for r in rows:
        for a in r["arxiv_set"]:
            by_ax[a] = r
        for d in r["doi_keys"]:
            by_doi[d] = r
    diag_ax = {}
    p = os.path.join(RAW, "diag_arxiv_known_items.xml")
    if os.path.exists(p):
        for e in parse_arxiv_entries(p):
            diag_ax[e["arxiv_id"]] = e
    out = []
    for t, k, label in KNOWN_ITEMS:
        r = by_ax.get(norm_arxiv(k)) if t == "arxiv" else by_doi.get(doi_key(k))
        item = {"type": t, "id": k, "label": label, "found": bool(r), "uid": r["uid"] if r else "",
                "sources": r["sources"] if r else "", "flag": r["prescreen_flag"] if r else "",
                "title": r["title"] if r else "", "diag": ""}
        if t == "arxiv" and norm_arxiv(k) in diag_ax:
            e = diag_ax[norm_arxiv(k)]
            hits = group_hits(e["title"] + ". " + e["abstract"])
            item["title"] = item["title"] or e["title"]
            item["diag"] = "arXiv record: %s, %s, categories %s; term hits in title/abstract: %s" % (
                e["year"], e["primary_category"], ",".join(e["categories"]),
                "; ".join("%s=%s" % (g, "|".join(v) if v else "none") for g, v in hits.items()))
        if t == "doi":
            fn = os.path.join(RAW, "diag_s2_doi_%s.json" % re.sub(r"[^A-Za-z0-9]+", "_", k))
            if os.path.exists(fn):
                try:
                    with open(fn, encoding="utf-8") as f:
                        j = json.load(f)
                    if j.get("title"):
                        hits = group_hits((j.get("title") or "") + ". " + (j.get("abstract") or ""))
                        item["title"] = item["title"] or j["title"]
                        item["diag"] = "Semantic Scholar DOI lookup: %s (%s), venue '%s', abstract %s; term hits: %s" % (
                            j.get("title"), j.get("year"), j.get("venue"), "present" if j.get("abstract") else "missing",
                            "; ".join("%s=%s" % (g, "|".join(v) if v else "none") for g, v in hits.items()))
                    else:
                        item["diag"] = "Semantic Scholar DOI lookup: %s" % json.dumps(j)[:200]
                except Exception as ex:
                    item["diag"] = "diag file unreadable: %r" % ex
        out.append(item)
    return out


def md_escape(s):
    return (s or "").replace("|", "\\|")


def write_log(mans, recs, rows, dstats, known):
    times = [p["fetched_utc"] for m in mans.values() if m for p in m["pages"]]
    L = []
    L.append("# Literature search log")
    L.append("")
    L.append("Survey: quantum and quantum-inspired methods for LLMs, read through LLM red teaming.")
    L.append("")
    L.append("This log records what the searches returned. Nothing here is an inclusion decision. "
             "`include` and `exclusion_reason` in `candidates.csv` are left empty for the authors.")
    L.append("")
    L.append("## Run")
    L.append("")
    L.append("- Run date: 2026-10-23 (the API calls ran from %s to %s UTC; per-page timestamps are in `raw/*_manifest.json`)." % (
        min(times) if times else "n/a", max(times) if times else "n/a"))
    L.append("- Log built: %s UTC." % utcnow())
    L.append("- Command: `set PYTHONIOENCODING=utf-8` then `python -I search.py all` (equivalently `fetch`, `diagnose`, `build`). "
             "The script uses only the Python 3.13 standard library. Raw responses are cached in `raw/`, and `build` regenerates every output offline from them.")
    L.append("- No API keys were used. No e-mail address, `mailto` parameter or other personal data was sent. The User-Agent is generic (`%s`)." % UA)
    L.append("")
    L.append("## Term groups")
    L.append("")
    for g, terms in GROUPS.items():
        L.append("- **%s** (%s): %s" % (g, GROUP_NAMES[g], ", ".join(qt(t) for t in terms)))
    L.append("")
    L.append("Searches: " + "; ".join("**%s** = %s" % (s, v["desc"]) for s, v in SEARCHES.items()) + ".")
    L.append("Exact strings sent to each source are in `queries.json` and in the `url` of each page in `raw/*_manifest.json`.")
    L.append("")
    L.append("## Counts per source and search")
    L.append("")
    L.append("*Reported* is the total hit count the API returned for the query (OpenAlex `meta.count`, arXiv `opensearch:totalResults`, Semantic Scholar `total`). "
             "*Retrieved* is the number of records downloaded and parsed.")
    L.append("")
    L.append("| Source | S1 reported | S1 retrieved | S2 reported | S2 retrieved | S3 reported | S3 retrieved | S4 reported | S4 retrieved |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    parsed = Counter((r["source"], r["search"]) for r in recs)
    for src in SOURCES:
        cells = [SOURCE_LABEL[src]]
        for sid in SEARCHES:
            m = mans.get((src, sid))
            if not m:
                cells += ["not run", "not run"]
                continue
            rep = m["reported_count"]
            ret = parsed[(src, sid)]
            note = ""
            if m.get("capped"):
                note = " (cap)"
            if not m.get("complete"):
                note += " (incomplete)"
            cells += [str(rep) if rep is not None else "n/a", "%d%s" % (ret, note)]
        L.append("| " + " | ".join(cells) + " |")
    L.append("")
    caps = [(src, sid, m) for (src, sid), m in mans.items() if m and m.get("capped")]
    for src, sid, m in caps:
        how = {"openalex": "the first %d by OpenAlex relevance (`sort=relevance_score:desc`)" % m["cap"],
               "arxiv": "the first %d by arXiv relevance (`sortBy=relevance`)" % m["cap"],
               "s2": "the first %d in `sort=citationCount:desc` order, because the bulk endpoint has no relevance ranking" % m["cap"]}[src]
        L.append("- **Cap applied:** %s %s reported %s records, which is over the limit. Kept %s." % (SOURCE_LABEL[src], sid, m["reported_count"], how))
    for (src, sid), m in mans.items():
        if m and not m.get("capped") and m["reported_count"] and m["reported_count"] > m["cap"]:
            L.append("- %s %s reported %s records, which is over the safety cap of %d." % (SOURCE_LABEL[src], sid, m["reported_count"], m["cap"]))
        if m and not m.get("complete"):
            L.append("- **Incomplete:** %s %s did not finish. Problems: %s" % (SOURCE_LABEL[src], sid, "; ".join(m["problems"][-3:])))
    L.append("")
    # unique contributions
    L.append("Unique records (after deduplication) found by each search, across all sources: " + ", ".join(
        "%s = %d" % (sid, sum(1 for r in rows if sid in r["searches"])) for sid in SEARCHES) + ".")
    L.append("")
    L.append("Unique records found by each source: " + ", ".join(
        "%s = %d" % (SOURCE_LABEL[s], sum(1 for r in rows if s in r["found"])) for s in SOURCES) +
        "; found by only one source: " + ", ".join(
        "%s only = %d" % (SOURCE_LABEL[s], sum(1 for r in rows if list(r["found"]) == [s])) for s in SOURCES) + ".")
    L.append("")
    # publisher breakdown
    L.append("### OpenAlex records by publisher / host (retrieved records)")
    L.append("")
    L.append("The bucket comes from the work's DOI prefix (10.1109 is IEEE, 10.1145 ACM, 10.1016 Elsevier/ScienceDirect, 10.18653 ACL, 10.36227 TechRxiv, and so on). "
             "Records without a DOI are bucketed by an ACL Anthology, TechRxiv or arXiv landing URL. "
             "For a capped search the breakdown covers only the retrieved records.")
    L.append("")
    oa = [r for r in recs if r["source"] == "openalex"]
    buckets = Counter(r["publisher_bucket"] for r in oa)
    order = [b for b, _ in buckets.most_common()]
    focus = ["IEEE", "ACM", "Elsevier (ScienceDirect)", "ACL Anthology", "TechRxiv"]
    order = focus + [b for b in order if b not in focus]
    L.append("| Publisher / host | " + " | ".join(SEARCHES) + " |")
    L.append("|---|" + "---|" * len(SEARCHES))
    per = {sid: Counter(r["publisher_bucket"] for r in oa if r["search"] == sid) for sid in SEARCHES}
    shown = 0
    other = Counter()
    for b in order:
        if b in focus or shown < 14:
            L.append("| %s | %s |" % (md_escape(b), " | ".join(str(per[s].get(b, 0)) for s in SEARCHES)))
            if b not in focus:
                shown += 1
        else:
            for s in SEARCHES:
                other[s] += per[s].get(b, 0)
    if other:
        L.append("| (all other buckets) | %s |" % " | ".join(str(other.get(s, 0)) for s in SEARCHES))
    L.append("")
    types = {sid: Counter(r["type"] for r in oa if r["search"] == sid) for sid in SEARCHES}
    L.append("OpenAlex work types among retrieved records: " + "; ".join(
        "%s: %s" % (sid, ", ".join("%s %d" % (t, n) for t, n in types[sid].most_common(6))) for sid in SEARCHES) + ".")
    L.append("")
    noabs = []
    for s in SOURCES:
        rs = [r for r in recs if r["source"] == s]
        if rs:
            k = sum(1 for r in rs if not r["abstract"])
            noabs.append("%s %d of %d (%.0f%%)" % (SOURCE_LABEL[s], k, len(rs), 100.0 * k / len(rs)))
    rows_noabs = sum(1 for r in rows if not r["abstract_full"])
    L.append("Retrieved records with no abstract, by source: " + "; ".join(noabs) +
             ". Unique records with no abstract from any source: %d of %d." % (rows_noabs, len(rows)))
    L.append("")
    zen = [r for r in rows if any(d.startswith("10.5281/") for d in r["doi_keys"])]
    L.append("Unique records with a Zenodo DOI (10.5281): %d (%s). Zenodo deposits are self-published, not peer-reviewed, and include many recent single-author uploads. They make up a large share of the OpenAlex S2 hits." % (
        len(zen), ", ".join("%s %d" % (s, sum(1 for r in zen if s in r["searches"])) for s in SEARCHES)))
    L.append("")
    L.append("## Deviations and source-specific notes")
    L.append("")
    oa_sort = {m.get("sort") for (s, _), m in mans.items() if s == "openalex" and m}
    oa_dupes = {}
    for sid in SEARCHES:
        ids = [r["native_id"] for r in recs if r["source"] == "openalex" and r["search"] == sid]
        oa_dupes[sid] = len(ids) - len(set(ids))
    L.append("**OpenAlex**")
    L.append("")
    L.append("- The boolean query goes in `filter=title_and_abstract.search:<query>` with uppercase AND/OR, parentheses and double-quoted phrases. "
             "Small test queries confirmed that OpenAlex honours them: `quantum` gives 1,760,744 hits, `quantum NOT \"large language model\"` gives 1,759,293, and `quantum AND \"large language model\"` gives 1,451, which add up. "
             "OpenAlex stems terms and treats a hyphen inside a quoted phrase as a space (`\"quantum-inspired\"` and `\"quantum inspired\"` both gave 7,113). This matches the intended title-and-abstract search.")
    L.append("- Computer-science restriction (S3, S4): `primary_topic.field.id:17` (topic-taxonomy field 17 is Computer Science). "
             "OpenAlex files machine learning under Computer Science (subfield 1702 Artificial Intelligence and related topics), so this one filter is the \"computer science or machine learning\" restriction for S4. "
             "Alternatives tested on `quantum AND \"large language model\"`: `primary_topic.field.id:17` gave 800, `topics.field.id:17` (any of up to 3 topics) gave 1,085, legacy concept CS `concepts.id:C41008148` gave 1,258, and legacy concept ML `C119857082` gave 168. "
             "The primary-topic field was chosen as the documented and current taxonomy. It is the strictest of these, so S3 and S4 exclude quantum-ML papers whose primary topic is in Physics and Astronomy. "
             "In a test of `quantum AND \"generative model\"` over 2018-2026, 124 of 1,057 hits were in Physics and Astronomy. These are covered only through the arXiv `stat.ML`/`cs.*` cross-lists, Semantic Scholar, and S2 where they mention language.")
    L.append("- Year limit: `publication_year:2018-2026`. S1 has no year filter.")
    L.append("- Ordering and paging: `sort=relevance_score:desc`, `per-page=200`, **basic paging (`page=1,2,...`)**%s. "
             "The planned cursor paging (`cursor=*`) failed: page 2 returned HTTP 401 `API key required for cursor paging`, because OpenAlex now requires an API key for cursor paging. "
             "Basic paging works without a key for the first 10,000 results, which covers every search here. "
             "All OpenAlex pages were therefore re-fetched with basic paging. "
             "Basic paging can in principle shift records between pages when relevance scores tie. Within-search duplicate OpenAlex ids after paging: %s." % (
        "" if oa_sort <= {"relevance_score:desc"} else ". **Relevance sort was rejected on at least one search, so the default order was used**",
        ", ".join("%s %d" % (sid, oa_dupes.get(sid, 0)) for sid in SEARCHES)))
    L.append("- Budget: unauthenticated OpenAlex calls now draw on a shared daily budget per IP address ($0.10/day at $0.001 per call, so about 100 calls). "
             "The API's notice suggests requesting a key by e-mail. That was not done, per the instruction not to send personal data. "
             "Each page's `X-RateLimit-Remaining-USD` is recorded in the manifest.")
    L.append("- Publisher coverage: OpenAlex includes IEEE, ACM, Elsevier/ScienceDirect, ACL Anthology and TechRxiv metadata. OpenAlex has no abstract for some works, so for those the match can only come from the title. The no-abstract counts above show how many.")
    L.append("")
    L.append("**arXiv**")
    L.append("")
    L.append("- Each term is searched in the title or the abstract: `(ti:<term> OR abs:<term>)`, joined with AND/OR in parentheses. "
             "Tests showed that the arXiv engine stems (`abs:LLM` and `abs:LLMs` both 82,642; `abs:\"tensor network\"` and `abs:\"tensor networks\"` both 3,449) and treats a hyphen in a phrase as a space (`abs:\"quantum-inspired\"` and `abs:\"quantum inspired\"` both 714). The query is therefore the exact boolean expression with no extra variants.")
    L.append("- Year limit: `submittedDate:[201801010000 TO 202612312359]`. This uses the first-version submission date, not the journal publication year.")
    L.append("- CS restriction: `cat:cs.*` for S3 and `(cat:cs.* OR cat:stat.ML)` for S4. `cat:` matches primary **or cross-listed** categories, so quant-ph papers cross-listed to cs.LG or stat.ML are included.")
    L.append("- Ordering: `sortBy=relevance`, pages of %d, at least 3.5 s between calls. On an HTTP error or an empty or short body the script backed off 30-60 s and retried." % AX_PAGE)
    L.append("")
    L.append("**Semantic Scholar (bulk search)**")
    L.append("")
    L.append("- Query syntax: `+` for AND, `|` for OR, double-quoted phrases, parentheses. The bulk endpoint matches title and abstract, and the query is the exact boolean expression. "
             "The string is URL-encoded with `%2B` for `+`. The requested fields are `" + S2_FIELDS + "`; `paperId` is always returned.")
    L.append("- Year limit: `year=2018-2026`. CS restriction (S3, S4): `fieldsOfStudy=Computer Science`. Semantic Scholar has no separate machine-learning field, since ML sits inside Computer Science, so S4 cannot add an explicit ML category.")
    L.append("- Ordering: the bulk endpoint does not rank by relevance. For S4, `sort=citationCount:desc` is set so that if the 3000-record cap applies, the most-cited records are kept rather than an arbitrary `paperId` slice. **This differs from the relevance ordering used for OpenAlex and arXiv.** Other searches use the default order.")
    L.append("- Unauthenticated calls share a public rate-limit pool and returned many HTTP 429 responses. The script kept at least 1.5 s between calls and backed off 30-300 s on 429. Every retry is listed under `problems` in the manifests.")
    L.append("- Semantic Scholar withholds abstracts for some publishers (the `abstract` field is null), so some records have no abstract and their prescreen flag is based on the title only.")
    L.append("")
    probs = [(src, sid, p) for (src, sid), m in mans.items() if m for p in m["problems"]]
    L.append("**Retries and errors during the run:** %d logged events (%s). Details are in each manifest's `problems` list." % (
        len(probs), ", ".join("%s %s: %d" % (SOURCE_LABEL[s], sid, n) for (s, sid), n in Counter((s, sid) for s, sid, _ in probs).items()) or "none"))
    L.append("")
    L.append("## Deduplication")
    L.append("")
    L.append("- Every parsed record (source x search x rank) is a node, and nodes are joined with union-find in three passes:")
    L.append("  1. **DOI.** The DOI is lowercased, stripped of `https://doi.org/`, and stripped of a trailing version suffix `/vN`, which TechRxiv mints per version. arXiv DOIs (`10.48550/arXiv.*`) are handled as arXiv ids.")
    L.append("  2. **arXiv id.** The version suffix is removed. arXiv ids come from arXiv itself, from Semantic Scholar `externalIds.ArXiv`, and from OpenAlex `locations` landing or PDF URLs and arXiv DOIs.")
    L.append("  3. **Normalized title.** Titles are NFKD-normalized, accents and HTML tags are stripped, the text is lowercased, and every non-alphanumeric run becomes one space. "
             "Title merging applies only when the normalized title is at least %d characters, and it is skipped when both years are known and differ by more than %d. This stops generic titles such as \"Quantum machine learning\" from merging unrelated works." % (TITLE_MIN_LEN, TITLE_MAX_YEAR_GAP))
    L.append("- Merges made: DOI %d, arXiv id %d, title %d; title merges skipped because of the year gap: %d." % (
        dstats.get("doi", 0), dstats.get("arxiv", 0), dstats.get("title", 0), dstats.get("title_skipped_year_gap", 0)))
    multi_ax = sum(1 for r in rows if len(r["arxiv_set"]) > 1)
    multi_doi = sum(1 for r in rows if len(r["doi_keys"]) > 1)
    L.append("- Rows with more than one arXiv id: %d. These usually come from a source's metadata linking two arXiv entries, for example a Semantic Scholar record whose arXiv externalId and arXiv DOI differ, which can merge two distinct preprints. They are worth a glance during screening. "
             "Rows with more than one DOI: %d, typically a preprint plus its published version, or several Zenodo version DOIs of the same deposit." % (multi_ax, multi_doi))
    L.append("- How a merged row is filled:")
    L.append("  - `title` comes from OpenAlex, else Semantic Scholar, else arXiv.")
    L.append("  - `year` is the earliest year across the merged records.")
    L.append("  - `venue` is the first non-arXiv venue, else `arXiv (<primary category>)` plus the journal reference.")
    L.append("  - `doi` lists every distinct non-arXiv DOI, separated by `; `.")
    L.append("  - `url` is the first DOI, else the arXiv abstract page.")
    L.append("  - `abstract` is the longest available abstract, truncated to 600 characters.")
    L.append("  - `sources` lists each source with the searches that found the record, for example `openalex:S2,S4; semanticscholar:S2; arxiv:S2`.")
    L.append("  - `uid` is `QRS-` plus the first 10 hex digits of the SHA-1 of the primary key: the smallest DOI key, else the arXiv id, else the title. It stays the same across re-runs as long as that key does not change.")
    L.append("- Rows are sorted by the earliest search that found them (S1 first), then by year (newest first), then by title.")
    L.append("- `candidates.csv` is UTF-8 with a byte-order mark, so Excel opens it correctly.")
    L.append("")
    L.append("**Records parsed: %d. Total unique records: %d.**" % (len(recs), len(rows)))
    L.append("")
    L.append("## Pre-screen flag rules")
    L.append("")
    L.append(PRESCREEN_RULES_MD)
    L.append("")
    flags = Counter(r["prescreen_flag"] for r in rows)
    L.append("| prescreen_flag | unique records | " + " | ".join("in %s" % s for s in SEARCHES) + " |")
    L.append("|---|---|" + "---|" * len(SEARCHES))
    for fl in FLAG_ORDER:
        L.append("| %s | %d | %s |" % (fl, flags.get(fl, 0), " | ".join(
            str(sum(1 for r in rows if r["prescreen_flag"] == fl and s in r["searches"])) for s in SEARCHES)))
    L.append("| **total** | **%d** | %s |" % (len(rows), " | ".join(str(sum(1 for r in rows if s in r["searches"])) for s in SEARCHES)))
    L.append("")
    L.append("## Known-item check")
    L.append("")
    L.append("These items were named in advance to test recall. The check only reports presence. If an item is missing, the diagnostic shows which term groups its title and abstract match, using approximate stem-tolerant regexes of the query terms. "
             "Its metadata was fetched separately (`python -I search.py diagnose`, files `raw/diag_*`). The search queries were not changed to capture any of these items.")
    L.append("")
    L.append("| Item | Id | In candidates.csv | uid | Found by | prescreen_flag | Diagnostic |")
    L.append("|---|---|---|---|---|---|---|")
    for k in known:
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            md_escape(k["label"]), md_escape(k["id"]), "yes" if k["found"] else "**no**", k["uid"],
            md_escape(k["sources"]), k["flag"], md_escape(k["diag"] if not k["found"] else (k["title"] or ""))))
    L.append("")
    with open(os.path.join(BASE, "search_log.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


# --------------------------------------------------------------------------
# Manual query strings for IEEE Xplore, ACM DL, ScienceDirect
# --------------------------------------------------------------------------
def chunks(lst, n):
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def best_split(sizes, budget):
    """Choose chunk sizes c_i (1..size_i) with sum(c_i) <= budget minimizing prod ceil(size_i/c_i)."""
    import itertools
    best = None
    for combo in itertools.product(*[range(1, s + 1) for s in sizes]):
        if sum(combo) > budget:
            continue
        n = 1
        for s, c in zip(sizes, combo):
            n *= -(-s // c)
        key = (n, -sum(combo))
        if best is None or key < best[0]:
            best = (key, combo)
    return best[1]


def split_queries(sid, budget_fn):
    import itertools
    gs = SEARCHES[sid]["groups"]
    sizes = [len(GROUPS[g]) for g in gs]
    combo = best_split(sizes, budget_fn(len(gs)))
    parts = [chunks(GROUPS[g], c) for g, c in zip(gs, combo)]
    return list(itertools.product(*parts))


def ieee_clause(terms):
    return "(" + " OR ".join('"Document Title":%s OR "Abstract":%s' % (qt(t), qt(t)) for t in terms) + ")"


def sd_clause(terms):
    return "(" + " OR ".join(qt(t) for t in terms) + ")" if len(terms) > 1 else qt(terms[0])


def acm_clause(terms):
    inner = " OR ".join(qt(t) for t in terms)
    return "(Title:(%s) OR Abstract:(%s))" % (inner, inner)


def write_manual_queries():
    # API-specific cap wording is dropped from the headings used for manual entry
    for sid in SEARCHES:
        SEARCHES[sid].setdefault("mdesc", SEARCHES[sid]["desc"].split(";")[0])
    M = []
    M.append("# Manual search strings: IEEE Xplore, ACM Digital Library, ScienceDirect")
    M.append("")
    M.append("These strings are generated by `search.py` from the same term groups as the API searches (see `queries.json`). "
             "Run them by hand, export the results (RIS, BibTeX or CSV), and fill in the count tables. Record the date of each run. "
             "Double quotes mark phrases. Hyphenated terms are quoted as phrases.")
    M.append("")
    for g, terms in GROUPS.items():
        M.append("- **%s** (%s): %s" % (g, GROUP_NAMES[g], ", ".join(qt(t) for t in terms)))
    M.append("")
    M.append("| Search | Definition | Year filter | Subject filter |")
    M.append("|---|---|---|---|")
    for sid, spec in SEARCHES.items():
        yr = "%d-%d" % spec["years"] if spec["years"] else "none"
        subj = {"cs": "Computer Science", "cs_ml": "Computer Science (or ML)", None: "none"}[spec["field"]]
        M.append("| %s | %s | %s | %s |" % (sid, " AND ".join(spec["groups"]), yr, subj))
    M.append("")
    M.append("Note: every Q term except Born machine, tensor network, QAOA, QUBO, HUBO and Ising machine contains the word `quantum`. "
             "On platforms that split hyphenated words, the bare term `quantum` already covers them. They are kept so the strings match the API queries exactly.")
    M.append("")

    # IEEE
    M.append("## 1. IEEE Xplore: Command Search")
    M.append("")
    M.append("Go to Advanced Search, then Command Search, and paste each string. "
             "Each term is searched in `\"Document Title\"` OR `\"Abstract\"` (title and abstract). "
             "IEEE Xplore's help states a maximum of **25 search terms per search clause**. Each term appears twice (once for title, once for abstract), so the full strings are split into numbered sub-queries of at most 25 terms. "
             "Together the sub-queries cover the full query. Run each one, export the results, and deduplicate by DOI. "
             "Set the year range (2018-2026) with the Year filter on the results page for S2-S4. "
             "IEEE has no computer-science subject filter, since IEEE content is essentially computing and engineering. If you want a narrower set for S3 and S4, apply the Topic filter (for example, Computing and Processing) and note that you did.")
    M.append("")
    for sid in SEARCHES:
        subs = split_queries(sid, lambda ng: 12)  # 2 terms per item => sum(c_i)*2 <= 25 => sum(c_i) <= 12
        M.append("### %s: %s" % (sid, SEARCHES[sid]["mdesc"]))
        M.append("")
        full = " AND ".join(ieee_clause(GROUPS[g]) for g in SEARCHES[sid]["groups"])
        nterms = 2 * sum(len(GROUPS[g]) for g in SEARCHES[sid]["groups"])
        M.append("Full string (%d terms; over the 25-term limit, so use the %d sub-queries below):" % (nterms, len(subs)))
        M.append("")
        M.append("```")
        M.append(full)
        M.append("```")
        M.append("")
        for i, combo in enumerate(subs, 1):
            M.append("%s-IEEE-%d:" % (sid, i))
            M.append("```")
            M.append(" AND ".join(ieee_clause(c) for c in combo))
            M.append("```")
        M.append("")

    # ACM
    M.append("## 2. ACM Digital Library: Advanced Search (Title and Abstract)")
    M.append("")
    M.append("Go to Advanced Search. Open **Edit Query** (under \"View Query Syntax\") and paste the string. "
             "Each group must appear in the Title or the Abstract: `(Title:(...) OR Abstract:(...))`, and the groups are joined with AND. "
             "Uppercase operators are required. Set Publication Date to a custom range of 2018-2026 for S2-S4. "
             "All of the ACM DL is computing literature, so S3 and S4 need no extra subject filter. "
             "Search **The ACM Full-Text Collection** (not the wider ACM Guide to Computing Literature) if you want ACM-published items only, and record which one you used. "
             "After running each string, open Edit Query again and check that ACM kept the OR operators. Older interface versions dropped OR in multi-field queries.")
    M.append("")
    for sid in SEARCHES:
        M.append("### %s: %s" % (sid, SEARCHES[sid]["mdesc"]))
        M.append("")
        M.append("```")
        M.append(" AND ".join(acm_clause(GROUPS[g]) for g in SEARCHES[sid]["groups"]))
        M.append("```")
        M.append("")

    # ScienceDirect
    M.append("## 3. ScienceDirect: Advanced Search, field \"Title, abstract or author-specified keywords\"")
    M.append("")
    M.append("ScienceDirect allows at most **8 boolean connectors (AND/OR/NOT) per field**. Each string is therefore split into numbered sub-queries with at most 8 connectors each. "
             "Together the sub-queries cover the full query: every combination of a chunk from each term group is run. "
             "Paste each sub-query into the *Title, abstract or author-specified keywords* field. Set *Year(s)* to `2018-2026` for S2-S4. For S3 and S4, refine the results by *Subject areas* = Computer Science. "
             "Note that this field also searches author keywords, which is slightly broader than title and abstract. "
             "ScienceDirect does not support wildcards and matches singular and plural forms. Record the count of each sub-query, then export and deduplicate across the sub-queries by DOI. "
             "The sum of the sub-query counts overstates the unique total.")
    M.append("")
    for sid in SEARCHES:
        subs = split_queries(sid, lambda ng: 8 - (ng - 1) + ng)  # connectors = sum(c_i - 1) + (ng - 1) <= 8 => sum(c_i) <= 8 + 1
        M.append("### %s: %s (%d sub-queries)" % (sid, SEARCHES[sid]["mdesc"], len(subs)))
        M.append("")
        M.append("| # | Sub-query (Title, abstract or author-specified keywords) | Connectors |")
        M.append("|---|---|---|")
        for i, combo in enumerate(subs, 1):
            s = " AND ".join(sd_clause(c) for c in combo)
            nconn = len(re.findall(r"\b(AND|OR|NOT)\b", s))
            assert nconn <= 8, (sid, i, nconn)
            M.append("| %s-SD-%d | `%s` | %d |" % (sid, i, s.replace("|", "\\|"), nconn))
        M.append("")

    # Count tables
    M.append("## 4. Counts to record (fill in)")
    M.append("")
    M.append("Date run: ________ Run by: ________")
    M.append("")
    M.append("| Database | Search | Sub-query | Filters applied (years, subject, collection) | Count reported | Exported | Notes |")
    M.append("|---|---|---|---|---|---|---|")
    for sid in SEARCHES:
        n_ieee = len(split_queries(sid, lambda ng: 12))
        for i in range(1, n_ieee + 1):
            M.append("| IEEE Xplore | %s | %s-IEEE-%d | | | | |" % (sid, sid, i))
    for sid in SEARCHES:
        M.append("| ACM DL | %s | (single string) | | | | |" % sid)
    for sid in SEARCHES:
        n_sd = len(split_queries(sid, lambda ng: 9))
        for i in range(1, n_sd + 1):
            M.append("| ScienceDirect | %s | %s-SD-%d | | | | |" % (sid, sid, i))
    M.append("")
    M.append("Summary after deduplicating within each database:")
    M.append("")
    M.append("| Database | S1 unique | S2 unique | S3 unique | S4 unique | Notes |")
    M.append("|---|---|---|---|---|---|")
    for db in ("IEEE Xplore", "ACM DL", "ScienceDirect"):
        M.append("| %s | | | | | |" % db)
    M.append("")
    with open(os.path.join(BASE, "manual_queries.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(M) + "\n")


# --------------------------------------------------------------------------
def main():
    # `python -I` ignores PYTHONIOENCODING, so force UTF-8 console output here.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["fetch", "diagnose", "build", "all"])
    ap.add_argument("--sources", default=",".join(SOURCES))
    ap.add_argument("--searches", default=",".join(SEARCHES))
    ap.add_argument("--max-pages", type=int, default=None, help="stop after N pages per source x search (resumable)")
    ap.add_argument("--refresh", action="store_true", help="discard cached raw pages and re-fetch")
    a = ap.parse_args()
    os.makedirs(RAW, exist_ok=True)
    if a.cmd in ("fetch", "all"):
        for sid in [s.strip() for s in a.searches.split(",") if s.strip()]:
            for src in [s.strip() for s in a.sources.split(",") if s.strip()]:
                FETCHERS[src](sid, refresh=a.refresh, max_pages=a.max_pages)
    if a.cmd in ("diagnose", "all"):
        diagnose()
    if a.cmd in ("build", "all"):
        build()


if __name__ == "__main__":
    main()
