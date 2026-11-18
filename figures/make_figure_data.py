"""Build the data files behind the data-driven figures of the review.

Nothing is typed in by hand: every number is read from the manuscript's own
tables (the audit table and the pilot table in main.tex), and the audit counts
are cross-checked against audit/audit_scores.csv when that file is given.

Usage:
    python make_figure_data.py <main.tex> <out_dir> [audit_scores.csv]
    python make_figure_data.py <audit_scores.csv> <out_dir>

The second form needs only the released audit scores (no manuscript). It writes the
audit files and skips the pilot table.

Outputs (plain whitespace-separated tables read by pgfplots):
    audit_by_criterion.dat   met / partly / not met / not applicable per QA1..QA5
    audit_qa3_by_mode.dat    QA3 scores by execution group
    audit_by_role.dat        QA3 scores per role (a study with two roles counts in both)
    pilot_summary.dat        mean and 95% CI half-width per generator, from the pilot table
    figure_data_report.txt   the counts quoted in the text, recomputed, with any mismatch
    figure_numbers.tex       counts and register sizes as LaTeX macros for the figure labels

Input read from the output folder, if present:
    scale_registers.csv      one row per bar of the scale figure: value, unit, execution mode,
                             location in the source, and the exact text of the audit scores and of
                             the manuscript that states it
"""
import csv
import os
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

def untrack(text):
    """Drop \\del{...}, unwrap \\add{...} and remove \\addcell, so tables parse the same with or without tracking marks."""
    text = text.replace("\\addcell ", "")
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


SCORE = {r"\yes": "Y", r"\pcov": "P", r"\no": "N", "--": "NA"}
QA = ["QA1", "QA2", "QA3", "QA4", "QA5"]


def table_body(tex, label):
    """Rows of the long table that carries \\label{label} (after \\endlastfoot)."""
    start = tex.index(r"\label{%s}" % label)
    body_start = tex.index(r"\endlastfoot", start) + len(r"\endlastfoot")
    body_end = tex.index(r"\end{xltabular}", body_start)
    rows = [r.strip() for r in tex[body_start:body_end].split(r"\\")]
    return [r for r in rows if r]


def parse_audit(tex):
    studies = []
    for row in table_body(tex, "tab:audit"):
        cells = [c.strip() for c in row.split("&")]
        if len(cells) != 9:
            raise ValueError("unexpected audit row: %r" % row)
        key = re.search(r"\\citet\{([^}]+)\}", cells[0]).group(1)
        execution = re.sub(r"\$\^\{a\}\$", "", cells[2]).strip()
        scores = {q: SCORE[c] for q, c in zip(QA, cells[3:8])}
        studies.append(dict(key=key, roles=cells[1].split("/"), execution=execution, **scores))
    return studies


def load_audit_csv(path):
    """The same records as parse_audit, read from the released audit_scores.csv."""
    studies = []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        execution = re.sub(r"\$\^\{a\}\$", "", r["execution_code"]).strip()
        studies.append(dict(key=r["key"], roles=r["role"].replace(" ", "").split("/"), execution=execution,
                            **{q: r[q] for q in QA}))
    return studies


def group_of(execution):
    """Execution group used in the text of the audit summary."""
    if "QRNG" in execution:
        return "QRNG"
    if "Sim." in execution or execution.startswith("HW") or ", HW" in execution and "Cl." not in execution:
        return "Circuit"
    if "Cl." in execution and "HW" in execution:
        return "Circuit"          # classical solver and quantum hardware (QCR-LLM)
    if "QI" in execution:
        return "QI"
    if execution.startswith("Cl."):
        return "Classical"
    raise ValueError(execution)


def parse_pilot(tex):
    start = tex.index(r"\label{tab:pilot}")
    body = tex[tex.index(r"\midrule", start) + len(r"\midrule"):tex.index(r"\bottomrule", start)]
    out = []
    for row in body.split(r"\\"):
        cells = [c.strip() for c in row.split("&")]
        if len(cells) != 8:
            continue

        def pm(cell):
            m = re.match(r"\$([\d.]+)\\pm([\d.]+)\$", cell)
            return float(m.group(1)), float(m.group(2))

        out.append(dict(role=cells[0], name=cells[1], params=int(cells[2]),
                        asr=pm(cells[3]), cov=pm(cells[4]), ttd=pm(cells[5]),
                        new=pm(cells[6]), div=pm(cells[7])))
    return out


def main():
    from_csv = sys.argv[1].lower().endswith(".csv")
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    if from_csv:
        tex = None
        studies = load_audit_csv(sys.argv[1])
        report = ["Recomputed from %s" % Path(sys.argv[1]).name, ""]
    else:
        tex = untrack(Path(sys.argv[1]).read_text(encoding="utf-8"))
        studies = parse_audit(tex)
        report = ["Recomputed from the audit table in %s" % Path(sys.argv[1]).name, ""]
    n = len(studies)
    report.append("studies in the audit table: %d" % n)

    # --- scores by criterion -------------------------------------------------
    with open(out / "audit_by_criterion.dat", "w") as f:
        f.write("criterion met partly notmet na\n")
        for q in QA:
            c = Counter(s[q] for s in studies)
            f.write("%s %d %d %d %d\n" % (q, c["Y"], c["P"], c["N"], c["NA"]))
            report.append("%s: met %d, partly %d, not met %d, not applicable %d"
                          % (q, c["Y"], c["P"], c["N"], c["NA"]))

    # --- QA3 by execution group ---------------------------------------------
    groups = OrderedDict([("Circuit", "Quantum circuits"), ("QI", "Quantum-inspired"),
                          ("Classical", "Classical solver"), ("QRNG", "QRNG")])
    for s in studies:
        s["group"] = group_of(s["execution"])
    gcount = Counter(s["group"] for s in studies)
    with open(out / "audit_qa3_by_mode.dat", "w") as f:
        f.write("group n met partly notmet\n")
        for g in groups:
            c = Counter(s["QA3"] for s in studies if s["group"] == g)
            f.write("%s %d %d %d %d\n" % (g, gcount[g], c["Y"], c["P"], c["N"]))
    circ = [s for s in studies if s["group"] == "Circuit"]
    hw = [s for s in circ if "HW" in s["execution"]]
    qi = [s for s in studies if s["group"] == "QI"]
    report += ["",
               "execution groups: circuits %d, quantum-inspired %d, classical solver only %d, QRNG %d"
               % (gcount["Circuit"], gcount["QI"], gcount["Classical"], gcount["QRNG"]),
               "circuit studies meeting QA2: %d of %d" % (sum(s["QA2"] == "Y" for s in circ), len(circ)),
               "circuit studies meeting QA3: %d of %d" % (sum(s["QA3"] == "Y" for s in circ), len(circ)),
               "circuit studies with QA3 not met: %d" % sum(s["QA3"] == "N" for s in circ),
               "circuit studies with hardware results: %d, of which QA3 met: %d (%s)"
               % (len(hw), sum(s["QA3"] == "Y" for s in hw),
                  ", ".join(s["key"] for s in hw if s["QA3"] == "Y")),
               "quantum-inspired studies meeting QA3: %d of %d" % (sum(s["QA3"] == "Y" for s in qi), len(qi)),
               "studies meeting QA5 (code or data released): %d of %d"
               % (sum(s["QA5"] == "Y" for s in studies), n)]

    # --- QA3 per role --------------------------------------------------------
    roles = ["R1", "R2", "R3", "R4", "R5", "R6"]
    with open(out / "audit_by_role.dat", "w") as f:
        f.write("role n met partly notmet\n")
        report.append("")
        for r in roles:
            rs = [s for s in studies if r in s["roles"]]
            c = Counter(s["QA3"] for s in rs)
            f.write("%s %d %d %d %d\n" % (r, len(rs), c["Y"], c["P"], c["N"]))
            report.append("%s: %d studies; QA3 met %d, partly %d, not met %d"
                          % (r, len(rs), c["Y"], c["P"], c["N"]))

    # --- cross-check against the released audit scores -----------------------
    if len(sys.argv) > 3:
        rows = {r["key"]: r for r in csv.DictReader(open(sys.argv[3], encoding="utf-8"))}
        mism = []
        for s in studies:
            r = rows.get(s["key"])
            if r is None:
                mism.append("%s: not in the csv" % s["key"])
                continue
            for q in QA:
                if r[q] != s[q]:
                    mism.append("%s %s: table %s, csv %s" % (s["key"], q, s[q], r[q]))
            if r["role"].replace(" ", "") != "/".join(s["roles"]):
                mism.append("%s role: table %s, csv %s" % (s["key"], "/".join(s["roles"]), r["role"]))
        report += ["", "cross-check against %s: %d rows, %d mismatches"
                   % (Path(sys.argv[3]).name, len(rows), len(mism))] + mism

    # --- pilot table (needs the manuscript) -----------------------------------
    pilot = parse_pilot(tex) if tex is not None else []
    short = {"Random composition": "Random composition", "Product Bernoulli": "Product Bernoulli",
             "Classical autoregressive": "Classical autoregressive", "Born machine": "Born machine",
             "Linear selector": "Linear selector", "Annealer": "Annealer", "QAOA": "QAOA"}
    with open(out / "pilot_summary.dat", "w") if pilot else open(os.devnull, "w") as f:
        f.write("idx role name params asr asr_ci cov cov_ci new new_ci\n")
        for i, p in enumerate(pilot):
            f.write("%d %s {%s} %d %.3f %.3f %.3f %.3f %.1f %.1f\n"
                    % (len(pilot) - i, p["role"].replace("--", "none"), short[p["name"]], p["params"],
                       p["asr"][0], p["asr"][1], p["cov"][0], p["cov"][1], p["new"][0], p["new"][1]))
    if pilot:
        report += ["", "pilot table rows read: %d" % len(pilot)]

    # --- counts as LaTeX macros, so that figure labels are never typed by hand ---
    macros = ["%% Generated by scripts/make_figure_data.py from the tables in main.tex. Do not edit.",
              "\\newcommand{\\figstat}[2]{\\csname figstat@#1@#2\\endcsname}"]

    def put(a, b, v):
        macros.append("\\expandafter\\def\\csname figstat@%s@%s\\endcsname{%s}" % (a, b, v))

    put("all", "n", n)
    for g in groups:
        c = Counter(s["QA3"] for s in studies if s["group"] == g)
        put(g, "n", gcount[g])
        for k, name in (("Y", "met"), ("P", "partly"), ("N", "notmet")):
            put(g, name, c[k])
    for r in roles:
        rs = [s for s in studies if r in s["roles"]]
        c = Counter(s["QA3"] for s in rs)
        put(r, "n", len(rs))
        for k, name in (("Y", "met"), ("P", "partly"), ("N", "notmet")):
            put(r, name, c[k])
    # --- register sizes of the scale figure --------------------------------------
    # scale_registers.csv (in the output folder) holds one row per bar with its source location.
    # Each value is checked against the released audit scores (when given) and against the
    # sentence or table row of the manuscript that quotes it, then written as a macro.
    reg_path = out / "scale_registers.csv"
    if reg_path.exists():
        regs = list(csv.DictReader(open(reg_path, encoding="utf-8")))
        audit_rows = ({r["key"]: r for r in csv.DictReader(open(sys.argv[3], encoding="utf-8"))}
                      if len(sys.argv) > 3 else
                      {r["key"]: r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8"))} if from_csv else {})
        report += ["", "register sizes of the scale figure (%s): %d rows" % (reg_path.name, len(regs))]
        bad = 0
        for r in regs:
            notes = []
            if r["key"] in audit_rows:
                a = audit_rows[r["key"]]
                hay = " ".join([a["scale"], a["execution"], a["QA2_evidence"]])
                ok = r["audit_pattern"] in hay and r["value"] in r["audit_pattern"]
                notes.append("audit csv " + ("ok" if ok else "MISSING"))
                bad += not ok
            if tex is not None:
                ok = r["manuscript_pattern"] in tex and r["value"] in r["manuscript_pattern"]
                notes.append("manuscript " + ("ok" if ok else "MISSING"))
                bad += not ok
            report.append("  %-8s %4s %-34s %s" % (r["macro"], r["value"], r["unit"], "; ".join(notes)))
            macros.append("\\expandafter\\def\\csname figscale@%s\\endcsname{%s}" % (r["macro"], r["value"]))
        macros.append("\\newcommand{\\figscale}[1]{\\csname figscale@#1\\endcsname}")
        report.append("register sizes not confirmed: %d" % bad)
    (out / "figure_numbers.tex").write_text("\n".join(macros) + "\n", encoding="utf-8")

    (out / "figure_data_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
