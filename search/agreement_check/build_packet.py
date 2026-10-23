"""Build a blind screening packet for the 54 core-search (S1) records.

Usage: python -I build_packet.py <search_dir> <out_dir>
Writes packet.jsonl (randomized order, no decisions) and id_map.csv (packet id -> uid).
"""
import csv
import glob
import json
import os
import random
import re
import sys
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
csv.field_size_limit(10**8)
search_dir, out_dir = sys.argv[1], sys.argv[2]
os.makedirs(out_dir, exist_ok=True)


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def oa_abstract(item):
    inv = item.get("abstract_inverted_index")
    if not inv:
        return ""
    pos = {p: w for w, ps in inv.items() for p in ps}
    return " ".join(pos[i] for i in sorted(pos))


# Collect the longest abstract per normalized title from the raw S1 responses.
abstracts = {}


def keep(title, abstract):
    k = norm(title)
    if k and len(abstract or "") > len(abstracts.get(k, "")):
        abstracts[k] = abstract


raw = os.path.join(search_dir, "raw")
for f in glob.glob(os.path.join(raw, "openalex_S1_*.json")):
    for it in json.load(open(f, encoding="utf-8")).get("results", []):
        keep(it.get("title") or it.get("display_name"), oa_abstract(it))
for f in glob.glob(os.path.join(raw, "semanticscholar_S1_*.json")) + glob.glob(os.path.join(raw, "s2_S1_*.json")):
    for it in json.load(open(f, encoding="utf-8")).get("data", []):
        keep(it.get("title"), it.get("abstract") or "")
ns = {"a": "http://www.w3.org/2005/Atom"}
for f in glob.glob(os.path.join(raw, "arxiv_S1_*.xml")):
    for e in ET.parse(f).getroot().findall("a:entry", ns):
        keep(e.find("a:title", ns).text, " ".join((e.find("a:summary", ns).text or "").split()))

rows = [r for r in csv.DictReader(open(os.path.join(search_dir, "candidates.csv"), encoding="utf-8-sig")) if "S1" in r["sources"]]
random.Random(20261024).shuffle(rows)
with open(os.path.join(out_dir, "packet.jsonl"), "w", encoding="utf-8") as fp, \
        open(os.path.join(out_dir, "id_map.csv"), "w", encoding="utf-8", newline="") as fm:
    mw = csv.writer(fm)
    mw.writerow(["packet_id", "uid"])
    for i, r in enumerate(rows, 1):
        pid = f"R{i:02d}"
        ab = abstracts.get(norm(r["title"])) or r["abstract"]
        rec = {"id": pid, "title": r["title"], "year": r["year"], "venue": r["venue"],
               "doi": r["doi"], "arxiv_id": r["arxiv_id"], "abstract": " ".join((ab or "").split())}
        fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        mw.writerow([pid, r["uid"]])
print(len(rows), "records written;", sum(1 for r in rows if not (abstracts.get(norm(r['title'])) or r['abstract'])), "without abstract")
