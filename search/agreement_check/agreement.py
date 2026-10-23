"""Agreement between the primary screening and two blind LLM screeners.

Usage: python -I agreement.py <packet_dir> <s1_screening.csv>
Prints pairwise Cohen's kappa and Fleiss' kappa (six-way and include-vs-not),
and writes disagreements.csv to the packet dir.
"""
import csv
import itertools
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
pdir, primary_csv = sys.argv[1], sys.argv[2]
idmap = {r["uid"]: r["packet_id"] for r in csv.DictReader(open(os.path.join(pdir, "id_map.csv"), encoding="utf-8"))}


def code(dec, reason):
    if dec == "include":
        return "INCLUDE"
    if dec == "related_review":
        return "RELATED_REVIEW"
    if dec == "duplicate":
        return "DUPLICATE"
    return "EXCLUDE-" + reason.split(":")[0].strip()


prim = {}
titles = {}
for r in csv.DictReader(open(primary_csv, encoding="utf-8")):
    pid = idmap[r["uid"]]
    prim[pid] = code(r["decision"], r["reason"])
    titles[pid] = r["title"]
raters = {"Primary": prim}
for name in ("A", "B"):
    rows = list(csv.DictReader(open(os.path.join(pdir, f"screener_{name}_final.csv"), encoding="utf-8-sig")))
    raters[name] = {r["id"].strip(): r["decision"].strip().upper() for r in rows}
    raters[name + "_why"] = {r["id"].strip(): r.get("rationale", "") for r in rows}
ids = sorted(prim)
for n in ("A", "B"):
    missing = set(ids) - set(raters[n])
    assert not missing, f"screener {n} missing {sorted(missing)}"


def cohen(a, b, f=lambda x: x):
    xa = [f(a[i]) for i in ids]
    xb = [f(b[i]) for i in ids]
    n = len(ids)
    po = sum(x == y for x, y in zip(xa, xb)) / n
    ca, cb = Counter(xa), Counter(xb)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return po, pe, (po - pe) / (1 - pe) if pe < 1 else 1.0


def fleiss(rs, f=lambda x: x):
    cats = sorted({f(r[i]) for r in rs for i in ids})
    n, m = len(ids), len(rs)
    counts = [[sum(f(r[i]) == c for r in rs) for c in cats] for i in ids]
    p_i = [(sum(x * x for x in row) - m) / (m * (m - 1)) for row in counts]
    pbar = sum(p_i) / n
    pj = [sum(row[j] for row in counts) / (n * m) for j in range(len(cats))]
    pe = sum(p * p for p in pj)
    return pbar, pe, (pbar - pe) / (1 - pe) if pe < 1 else 1.0


binary = lambda x: "INCLUDE" if x == "INCLUDE" else "OTHER"
for name in ("Primary", "A", "B"):
    print(name, dict(Counter(raters[name][i] for i in ids)))
for label, f in (("six-way", lambda x: x), ("include vs not", binary)):
    print(f"\n[{label}]")
    for x, y in itertools.combinations(("Primary", "A", "B"), 2):
        po, pe, k = cohen(raters[x], raters[y], f)
        print(f"  Cohen {x} vs {y}: observed {po:.3f}, chance {pe:.3f}, kappa {k:.3f}")
    po, pe, k = fleiss([raters["Primary"], raters["A"], raters["B"]], f)
    print(f"  Fleiss (3 raters): observed {po:.3f}, chance {pe:.3f}, kappa {k:.3f}")

with open(os.path.join(pdir, "disagreements.csv"), "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["id", "title", "primary", "A", "B", "A_rationale", "B_rationale", "include_level_disagreement"])
    for i in ids:
        vals = {raters["Primary"][i], raters["A"][i], raters["B"][i]}
        if len(vals) > 1:
            inc = len({binary(raters[k][i]) for k in ("Primary", "A", "B")}) > 1
            w.writerow([i, titles[i], raters["Primary"][i], raters["A"][i], raters["B"][i], raters["A_why"][i], raters["B_why"][i], "yes" if inc else "no"])
            print(f"{i} {'*' if inc else ' '} P={raters['Primary'][i]:15s} A={raters['A'][i]:15s} B={raters['B'][i]:15s} {titles[i][:70]}")
