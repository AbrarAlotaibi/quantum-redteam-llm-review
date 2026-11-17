"""Check the selection of the 30 primary studies against the released records.

Reads search/selected_studies.csv (one row per primary study: its record in the sampling
frame, if any, the route by which it entered the review, and the inclusion criterion),
and checks it against the other released files:

  audit/audit_scores.csv     the 30 audited studies; task, scale and execution mode
  search/candidates.csv      the 7,312 records of the sampling frame, with the prescreen flag and the
                             decision columns filled by fill_decisions.py
  search/s1_screening.csv    the screening of the 54 records of the core search
  search/frame_screening/    the eligibility screening of the other 7,258 records in phases (two
                             screeners, abstracts retrieved and records screened again, third
                             screener where the two differ), and the roles of the eligible ones

Usage:  python search/check_selection.py        (from the repository root)
Exits with status 1 if any check fails.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_TOPIC_FLAGS = {"llm_for_quantum": "EC1", "quantum_ml_robustness": "EC2", "post_quantum_crypto": "EC3"}


def rows(path):
    return list(csv.DictReader(open(ROOT / path, encoding="utf-8")))


def main():
    sel = rows("search/selected_studies.csv")
    audit = {r["key"]: r for r in rows("audit/audit_scores.csv")}
    cand = {r["uid"]: r for r in rows("search/candidates.csv")}
    s1 = rows("search/s1_screening.csv")
    core_included = {r["uid"] for r in s1 if r["final_decision"] == "INCLUDE"}
    problems = []

    def check(ok, message):
        print(("ok    " if ok else "FAIL  ") + message)
        if not ok:
            problems.append(message)

    check({r["key"] for r in sel} == set(audit) and len(sel) == len(audit),
          "the selected studies are exactly the %d audited studies" % len(audit))
    check(all(r["uid"] in cand for r in sel if r["uid"]), "every record id given exists in the sampling frame")

    routes = Counter(r["route"] for r in sel)
    check(routes == Counter({"representative": 27, "core": 3}), "routes: 3 from the core search, 27 representative (%s)" % dict(routes))
    check({r["uid"] for r in sel if r["route"] == "core"} == core_included,
          "the three core studies are the records screened as INCLUDE in s1_screening.csv")

    rep = [r for r in sel if r["route"] == "representative"]
    in_frame = [r for r in rep if r["uid"]]
    check(len(in_frame) == 23 and len(rep) - len(in_frame) == 4,
          "representative studies: %d records of the sampling frame, %d from snowballing" % (len(in_frame), len(rep) - len(in_frame)))
    crit = Counter(r["criterion"] for r in rep)
    check(crit == Counter({"IC1": 16, "IC2": 11}), "criteria of the representative studies: %s" % dict(crit))
    check(all(r["criterion"] == "core rule" for r in sel if r["route"] == "core"), "core studies carry the rule of the core search")

    flags = Counter(cand[r["uid"]]["prescreen_flag"] for r in sel if r["uid"])
    check(not (set(flags) & set(EXCLUDED_TOPIC_FLAGS)),
          "no selected study carries the flag of an excluded topic (flags: %s)" % dict(flags))

    filled = all(audit[r["key"]][f].strip() for r in sel for f in ("task_data", "scale", "execution"))
    check(filled, "task, scale and execution mode are recorded for every study (the detail that IC2 requires)")
    check(all(audit[r["key"]]["fulltext_read"] == "True" for r in sel), "every study was read in full")

    topic = Counter(r["prescreen_flag"] for r in cand.values())
    check((topic["llm_for_quantum"], topic["quantum_ml_robustness"], topic["post_quantum_crypto"]) == (128, 104, 248),
          "records flagged on the excluded topics: EC1 %d, EC2 %d, EC3 %d of %d"
          % (topic["llm_for_quantum"], topic["quantum_ml_robustness"], topic["post_quantum_crypto"], len(cand)))
    dec = Counter(r["final_decision"] for r in s1)
    check((len(s1), dec["INCLUDE"], dec["RELATED_REVIEW"], dec["DUPLICATE"], dec["EXCLUDE-E1"], dec["EXCLUDE-E2"], dec["EXCLUDE-E3"])
          == (54, 3, 6, 1, 5, 26, 13),
          "core screening: 54 records, 3 included, 6 related reviews, 1 duplicate, 5 cryptography, 26 off topic, 13 not scholarly")

    # the decision columns of the candidate sheet (filled by fill_decisions.py)
    frame = {r["uid"]: r for r in rows("search/frame_screening/phase4_eligibility/frame_screening.csv")}
    fs = Counter((r["decided_by"], r["final"]) for r in frame.values())
    both_el, both_not = fs[("both screeners", "eligible")], fs[("both screeners", "not eligible")]
    adj_el, adj_not = fs[("third screener", "eligible")], fs[("third screener", "not eligible")]
    check(set(frame) == set(cand) - {r["uid"] for r in s1} and len(frame) == 7258,
          "the frame screening covers the %d records outside the core search" % len(frame))
    check((both_el, adj_el + adj_not, both_not) == (1930, 609, 4719),
          "two screeners: eligible by both %d, by one only %d, by neither %d" % (both_el, adj_el + adj_not, both_not))
    check((adj_el, adj_not) == (391, 218), "third screener on the %d: eligible %d, not eligible %d" % (adj_el + adj_not, adj_el, adj_not))
    check(both_el + adj_el == 2321, "final eligibility: %d eligible, %d not eligible" % (both_el + adj_el, both_not + adj_not))
    check(all(r["code_C"] for r in frame.values() if r["decided_by"] == "third screener")
          and not any(r["code_C"] for r in frame.values() if r["decided_by"] == "both screeners"),
          "every record on which the screeners differ has a third code, and no other record has one")
    check(all(frame[r["uid"]]["decided_by"] == "both screeners" and frame[r["uid"]]["final"] == "eligible"
              and frame[r["uid"]]["criterion"] == r["criterion"] for r in in_frame),
          "the %d selected records of the frame are eligible by both screeners, with the criterion listed here" % len(in_frame))
    by_role = rows("search/frame_screening/phase5_selection/eligible_by_role.csv")
    pool = Counter(r["role"] for r in by_role)
    pool2 = Counter(r["role"] for r in by_role if r["eligible_by"] == "both screeners")
    keys = ("R1", "R2", "R3", "R4", "R5", "R6", "")
    check({r["uid"] for r in by_role} == {u for u, r in frame.items() if r["final"] == "eligible"}
          and [pool[k] for k in keys] == [382, 160, 1317, 108, 321, 3, 30],
          "eligible records by role: R1 %d, R2 %d, R3 %d, R4 %d, R5 %d, R6 %d, no role %d" % tuple(pool[k] for k in keys))
    check([pool2[k] for k in keys] == [335, 119, 1092, 87, 277, 3, 17],
          "of these, eligible by both screeners: R1 %d, R2 %d, R3 %d, R4 %d, R5 %d, R6 %d, no role %d" % tuple(pool2[k] for k in keys))

    inc = Counter(r["include"] for r in cand.values())
    check(inc == Counter({"yes": len(core_included) + len(in_frame), "eligible, not selected": both_el + adj_el - len(in_frame),
                          "no": len(s1) - len(core_included) + both_not + adj_not}),
          "candidate sheet: include = yes %d, eligible but not selected %d, no %d" % (inc["yes"], inc["eligible, not selected"], inc["no"]))
    yes = {u for u, r in cand.items() if r["include"] == "yes"}
    check(yes == {r["uid"] for r in sel if r["uid"]}, "the records marked yes are the selected studies that are in the sheet")
    no = {u for u, r in cand.items() if r["include"] == "no"}
    check(no == {r["uid"] for r in s1 if r["final_decision"] != "INCLUDE"} | {u for u, r in frame.items() if r["final"] == "not eligible"}
          and all(cand[u]["exclusion_reason"] for u in no),
          "the records marked no are those not included by the core screening or not eligible in the frame screening, each with a reason")
    check(all(not r["exclusion_reason"] for r in cand.values() if r["include"] != "no"), "no reason is given where no exclusion was decided")

    print("\n%d problem(s)" % len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
