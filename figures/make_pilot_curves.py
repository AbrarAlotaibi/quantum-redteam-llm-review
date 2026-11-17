"""Coverage per target query for the protocol illustration (Fig. pilot).

Reads the per-query log written by a run of the released notebook
(protocol_pilot_tier1.ipynb) and writes mean coverage with a 95% confidence
interval over seeds, for every generator, as a table that pgfplots reads.

Usage:
    python make_pilot_curves.py <log.csv> <out_dir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

log = pd.read_csv(sys.argv[1])
out = Path(sys.argv[2])
methods = ["random", "product", "autoregressive", "born", "linear", "anneal", "qaoa"]
table = {"t": np.arange(1, log["t"].max() + 1)}
for m in methods:
    curves = np.stack([g.sort_values("t")["coverage"].to_numpy()
                       for _, g in log[log["method"] == m].groupby("seed")])
    n = len(curves)
    mean = curves.mean(0)
    half = stats.t.ppf(0.975, n - 1) * curves.std(0, ddof=1) / np.sqrt(n)
    table[m] = mean
    table[m + "_lo"] = mean - half
    table[m + "_hi"] = mean + half
    print("%-15s seeds %d  final coverage %.3f +/- %.3f" % (m, n, mean[-1], half[-1]))
pd.DataFrame(table).to_csv(out / "pilot_coverage.dat", sep=" ", index=False, float_format="%.4f")
