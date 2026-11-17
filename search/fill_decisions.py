"""Fill the decision columns of search/candidates.csv from the records of the selection.

search.py writes `include` and `exclusion_reason` empty. This script fills them, and a third
column `decision_basis`, from the three files that hold the decisions:

  search/s1_screening.csv                      final decision for each of the 54 records of the core search
  search/frame_screening/frame_screening.csv   the two screenings of the other 7,258 records (sampling frame)
  search/selected_studies.csv                  the 30 primary studies, with route and criterion

Every record gets one of four values in `include`:

  yes                     a primary study of the review: included by the core screening (route 1),
                          or selected as a representative study under IC1 or IC2 (route 2)
  eligible, not selected  a record of the sampling frame that both screeners found eligible
                          (IC1 or IC2 and no exclusion criterion) and that was not selected as a
                          representative study (Section 2.3 of the article)
  unresolved              a record of the sampling frame that one screener found eligible and
                          the other did not; not adjudicated
  no                      not included by the core screening, or not eligible by both screeners
                          of the sampling frame; the reason is in `exclusion_reason`

The four representative studies found by snowballing are not records of the sampling frame;
they appear in selected_studies.csv only.

Usage:  python search/fill_decisions.py      (from the repository root; safe to run again)
"""
import csv
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE_REASON = {
    "EXCLUDE-E1": "post-quantum or quantum cryptography",
    "EXCLUDE-E2": "no quantum or quantum-inspired method for the adversarial evaluation of language models",
    "EXCLUDE-E3": "not a scholarly study",
    "RELATED_REVIEW": "related review: discussed in Section 3.4, not a primary study",
    "DUPLICATE": "another version of a record already counted",
}
BASIS_CORE = "core search (route 1): screened on title and abstract, see s1_screening.csv"
BASIS_FRAME = "sampling frame (route 2): screened on title and abstract by two independent screeners, see frame_screening/frame_screening.csv"
FRAME_REASON = {
    "EC1": "EC1: language models applied to quantum computing",
    "EC2": "EC2: adversarial robustness of quantum machine learning",
    "EC3": "EC3: post-quantum or quantum cryptography",
    "EC4": "EC4: no method and no evaluation",
    "REVIEW": "secondary study (review, survey, or tutorial)",
    "NO": "meets neither IC1 nor IC2",
}


def main():
    path = HERE / "candidates.csv"
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        cols = list(rows[0].keys())
    if "decision_basis" not in cols:
        cols.append("decision_basis")
    core = {r["uid"]: r["final_decision"] for r in csv.DictReader(open(HERE / "s1_screening.csv", encoding="utf-8"))}
    selected = {r["uid"]: r for r in csv.DictReader(open(HERE / "selected_studies.csv", encoding="utf-8")) if r["uid"]}
    frame = {r["uid"]: r for r in csv.DictReader(open(HERE / "frame_screening" / "frame_screening.csv", encoding="utf-8", newline=""))}
    known = {r["uid"] for r in rows}
    assert set(core) | set(frame) == known and not set(core) & set(frame), "core and frame screenings must cover every record once"
    missing = (set(core) | set(selected)) - known
    assert not missing, "records with a decision that are not in candidates.csv: %s" % sorted(missing)

    for r in rows:
        uid = r["uid"]
        if uid in selected and selected[uid]["route"] == "representative":
            assert uid not in core, "%s is both a representative study and a record of the core search" % uid
            assert frame[uid]["status"] == "eligible", "%s was selected but is not eligible by both screeners" % uid
            r["include"], r["exclusion_reason"] = "yes", ""
            r["decision_basis"] = "representative study (route 2): %s, role %s" % (selected[uid]["criterion"], selected[uid]["role"])
        elif uid in core:
            if core[uid] == "INCLUDE":
                assert uid in selected, "%s was included by the core screening but is not in selected_studies.csv" % uid
                r["include"], r["exclusion_reason"] = "yes", ""
                r["decision_basis"] = BASIS_CORE.replace("screened", "included after screening")
            else:
                r["include"], r["exclusion_reason"] = "no", CORE_REASON[core[uid]]
                r["decision_basis"] = BASIS_CORE
        else:
            fr = frame[uid]
            r["decision_basis"] = BASIS_FRAME
            if fr["status"] == "eligible":
                r["include"], r["exclusion_reason"] = "eligible, not selected", ""
                r["decision_basis"] += "; criterion " + fr["consensus"]
            elif fr["status"] == "unresolved":
                r["include"], r["exclusion_reason"] = "unresolved", ""
                r["decision_basis"] += "; screener A %s, screener B %s" % (fr["code_A"], fr["code_B"])
            else:
                r["include"] = "no"
                if fr["code_A"] == fr["code_B"]:
                    r["exclusion_reason"] = FRAME_REASON[fr["code_A"]]
                else:
                    r["exclusion_reason"] = "not eligible; the screeners give different reasons (A: %s; B: %s)" % (
                        FRAME_REASON[fr["code_A"]], FRAME_REASON[fr["code_B"]])

    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print("candidates.csv: %d records" % len(rows))
    for value, n in sorted(Counter(r["include"] for r in rows).items()):
        print("  include = %-12s %5d" % (value, n))
    for value, n in Counter(r["exclusion_reason"] for r in rows if r["include"] == "no").most_common(12):
        print("    %-90s %4d" % (value[:90], n))


if __name__ == "__main__":
    main()
