"""Agreement between the primary audit scores and two blind re-scorers (10-study subset).

Usage: python -I audit_agreement.py <audit_scores.json> <audit_check_dir>
Pools the 50 study-by-criterion ratings (10 studies x QA1-QA5) and reports Cohen's
kappa for each pair, Fleiss' kappa for the three raters, and per-criterion agreement.
Writes audit_disagreements.csv.
"""
import csv
import itertools
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
scores_json, d = sys.argv[1], sys.argv[2]
QA = ["QA1", "QA2", "QA3", "QA4", "QA5"]
prim_all = {o["key"]: o for o in json.load(open(scores_json, encoding="utf-8"))}


def norm(v):
    v = str(v).strip().upper().split()[0] if v else "?"
    return {"UNKNOWN": "?"}.get(v, v)


raters = {}
evid = {}
for n in ("A", "B"):
    rows = list(csv.DictReader(open(os.path.join(d, f"scorer_{n}.csv"), encoding="utf-8-sig")))
    raters[n] = {(r["key"].strip(), q): norm(r[q]) for r in rows for q in QA}
    evid[n] = {(r["key"].strip(), q): r.get(q + "_evidence", "") for r in rows for q in QA}
keys = sorted({k for k, _ in raters["A"]})
raters["Primary"] = {(k, q): norm(prim_all[k][q]) for k in keys for q in QA}
items = [(k, q) for k in keys for q in QA]


def cohen(a, b, subset=items):
    n = len(subset)
    po = sum(a[i] == b[i] for i in subset) / n
    ca, cb = Counter(a[i] for i in subset), Counter(b[i] for i in subset)
    pe = sum(ca[c] * cb[c] for c in set(ca) | set(cb)) / n / n
    return po, pe, (po - pe) / (1 - pe) if pe < 1 else 1.0


def fleiss(rs, subset=items):
    cats = sorted({r[i] for r in rs for i in subset})
    m, n = len(rs), len(subset)
    counts = [[sum(r[i] == c for r in rs) for c in cats] for i in subset]
    pbar = sum((sum(x * x for x in row) - m) / (m * (m - 1)) for row in counts) / n
    pj = [sum(row[j] for row in counts) / (n * m) for j in range(len(cats))]
    pe = sum(p * p for p in pj)
    return pbar, pe, (pbar - pe) / (1 - pe) if pe < 1 else 1.0


print("studies:", keys)
print("\n[pooled, 50 ratings]")
for x, y in itertools.combinations(("Primary", "A", "B"), 2):
    po, pe, k = cohen(raters[x], raters[y])
    print(f"  Cohen {x} vs {y}: observed {po:.3f}, chance {pe:.3f}, kappa {k:.3f}")
po, pe, k = fleiss([raters["Primary"], raters["A"], raters["B"]])
print(f"  Fleiss (3 raters): observed {po:.3f}, chance {pe:.3f}, kappa {k:.3f}")
print("\n[per criterion: share of studies where all three agree]")
for q in QA:
    sub = [(k, q) for k in keys]
    allagree = sum(len({raters[r][i] for r in ("Primary", "A", "B")}) == 1 for i in sub)
    print(f"  {q}: {allagree}/10 unanimous")

with open(os.path.join(d, "audit_disagreements.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["key", "criterion", "primary", "A", "B", "A_evidence", "B_evidence"])
    print("\n[disagreements]")
    for i in items:
        vals = [raters[r][i] for r in ("Primary", "A", "B")]
        if len(set(vals)) > 1:
            w.writerow([i[0], i[1], *vals, evid["A"][i], evid["B"][i]])
            print(f"  {i[0]:26s} {i[1]}: P={vals[0]:2s} A={vals[1]:2s} B={vals[2]:2s}")
