"""Check the illustration's numbers in the manuscript against the run log, and print the table rows.

Recomputes every cell of the pilot table (ASR, coverage, time to 50% coverage, new codes,
diversity) and the paired differences quoted in the text from the per-query log of a run of
protocol_pilot_tier1.ipynb, then compares the table cells with those typed in main.tex.
A real-target (Tier 2) run that writes the same log columns can be checked the same way.

Usage: python check_pilot_numbers.py <log.csv> [main.tex]
Without main.tex it prints the recomputed table rows and paired differences only.
"""
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats

N_BITS, N_CELLS, WARMUP = 12, 40, 60


def untrack(text):
    """Drop \\del{...} and unwrap \\add{...}, so tables parse the same with or without tracking marks."""
    out, i = [], 0
    while i < len(text):
        if text.startswith("\\del{", i) or text.startswith("\\add{", i):
            keep = text[i + 1:i + 4] == "add"
            j, depth = i + 5, 1
            while depth:
                depth += (text[j] == "{") - (text[j] == "}")
                j += 1
            if keep:
                out.append(untrack(text[i + 5:j - 1]))
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)

log = pd.read_csv(sys.argv[1])
tex = untrack(open(sys.argv[2], encoding="utf-8").read()) if len(sys.argv) > 2 else None
ORDER = ["random", "product", "autoregressive", "born", "linear", "anneal", "qaoa"]
BITS = (np.arange(2 ** N_BITS)[:, None] >> np.arange(N_BITS - 1, -1, -1)) & 1


def ci(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return x.mean(), h, len(x)


def hamming(codes):
    if len(codes) < 2:
        return np.nan
    b = BITS[codes]
    return (b[:, None, :] != b[None, :, :]).sum(-1)[np.triu_indices(len(b), 1)].mean()


rec = []
for (m, s), g in log.groupby(["method", "seed"]):
    g = g.sort_values("t")
    cov = g["coverage"].to_numpy()
    hit = np.nonzero(cov >= 0.5)[0]
    warm = set(g[(g["t"] <= WARMUP) & g["success"]]["code"])
    late = set(g[(g["t"] > WARMUP) & g["success"]]["code"])
    rec.append(dict(method=m, seed=s, asr=g["success"].mean(), cov=cov[-1],
                    ttd=hit[0] + 1 if len(hit) else np.nan, new=len(late - warm),
                    div=hamming(g[g["success"]]["code"].to_numpy())))
per = pd.DataFrame(rec)

rows = []
for m in ORDER:
    d = per[per["method"] == m]
    a, c, t, n, v = (ci(d[k]) for k in ("asr", "cov", "ttd", "new", "div"))
    miss = len(d) - t[2]
    rows.append("$%.3f\\pm%.3f$ & $%.3f\\pm%.3f$ & $%.1f\\pm%.1f$%s & $%.1f\\pm%.1f$ & $%.2f\\pm%.2f$"
                % (a[0], a[1], c[0], c[1], t[0], t[1], " (%d)" % miss if miss else "", n[0], n[1], v[0], v[1]))

if tex is None:
    for m, mine in zip(ORDER, rows):
        print("%-15s %s" % (m, mine))
else:
    body = tex[tex.index(r"\label{tab:pilot}"):]
    body = body[body.index(r"\midrule") + 8:body.index(r"\bottomrule")]
    typed = [" & ".join(c.strip() for c in r.split("&")[3:]) for r in body.split(r"\\") if r.count("&") == 7]
    ok = 0
    for m, mine, theirs in zip(ORDER, rows, typed):
        same = mine.replace(" ", "") == theirs.replace(" ", "")
        ok += same
        print("%-15s %s  %s" % (m, "matches" if same else "DIFFERS", mine if same else "\n   data:  %s\n   paper: %s" % (mine, theirs)))
    print("table rows that match the log: %d of %d" % (ok, len(ORDER)))


def paired(metric, a, b):
    pa = per[per["method"] == a].set_index("seed")[metric]
    pb = per[per["method"] == b].set_index("seed")[metric]
    mu, h, n = ci((pa - pb).dropna())
    return "%+.3f, 95%% CI [%+.3f, %+.3f], n=%d" % (mu, mu - h, mu + h, n)


print("\npaired differences over seeds (quoted in the text of the illustration):")
print("  coverage, Born - autoregressive:  ", paired("cov", "born", "autoregressive"))
print("  coverage, Born - product:         ", paired("cov", "born", "product"))
print("  coverage, Born - random:          ", paired("cov", "born", "random"))
print("  new codes, Born - autoregressive: ", paired("new", "born", "autoregressive"))
print("  coverage, annealer - linear:      ", paired("cov", "anneal", "linear"))
