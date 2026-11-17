"""Build the final eligibility decision of the sampling frame from the phase files, and report agreement.

Phases (folders next to this script):
  phase1_screening/                  screener_A.csv, screener_B.csv: one code per record from each screener (round 1)
  phase2_abstracts_and_rescreening/  retrieved_abstracts.csv: records without an abstract in the search indexes, and
                                     where an abstract was found; screener_A_rescreen.csv, screener_B_rescreen.csv:
                                     both screeners' new codes for the records whose abstract was found (rounds 2, 3)
  phase3_adjudication/               screener_C.csv: the third screener's code for the records on whose eligibility
                                     the two screeners differ, and for a random sample of records on which they agree
  phase4_eligibility/                frame_screening.csv (written here): the latest code of each screener, the third
                                     code where there is one, and the final decision; agreement_report.txt
  phase5_selection/                  eligible_by_role.csv: both role assignments of the eligible records;
                                     role_report.txt (written here)

A record is eligible if both screeners code it IC1 or IC2. Where they differ, the third screener decides.

Usage:  python search/frame_screening/agreement.py      (from the repository root)
"""
import csv
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODES = ["IC1", "IC2", "EC1", "EC2", "EC3", "EC4", "REVIEW", "NO"]
ELIGIBLE = {"IC1", "IC2"}
ROLES = ["R1", "R2", "R3", "R4", "R5", "R6"]


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8", newline="")))


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[c] * cb[c] for c in set(ca) | set(cb)) / n / n
    return po, (po - pe) / (1 - pe)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


def agreement_lines(pairs):
    el = lambda c: "eligible" if c in ELIGIBLE else "not"
    out = []
    for name, pp in (("all eight codes", pairs), ("eligible or not", [(el(a), el(b)) for a, b in pairs])):
        po, k = kappa(pp)
        out.append("  %-18s agreement %.3f   Cohen's kappa %.3f" % (name, po, k))
    return out


def main():
    A = {r["uid"]: dict(r, round="1") for r in read(HERE / "phase1_screening" / "screener_A.csv")}
    B = {r["uid"]: dict(r, round="1") for r in read(HERE / "phase1_screening" / "screener_B.csv")}
    first = [(A[u]["code"], B[u]["code"]) for u in sorted(A)]
    assert set(A) == set(B)
    for tag, cur in (("A", A), ("B", B)):
        for r in sorted(read(HERE / "phase2_abstracts_and_rescreening" / ("screener_%s_rescreen.csv" % tag)), key=lambda r: r["round"]):
            assert r["uid"] in cur and r["code"] in CODES
            cur[r["uid"]] = r
    C_all = read(HERE / "phase3_adjudication" / "screener_C.csv")
    C = {(r["uid"], r["round"]): r for r in C_all if r["use"] == "adjudication"}
    retrieved = {r["uid"]: r for r in read(HERE / "phase2_abstracts_and_rescreening" / "retrieved_abstracts.csv")}
    cand = {r["uid"]: r for r in read(HERE.parent / "candidates.csv")}

    rows = []
    for uid in sorted(A):
        a, b = A[uid], B[uid]
        assert a["round"] == b["round"]
        ea, eb = a["code"] in ELIGIBLE, b["code"] in ELIGIBLE
        src = retrieved[uid]["source_of_abstract"] if uid in retrieved else "search index"
        row = {"uid": uid, "id": a["id"], "title": cand[uid]["title"], "year": cand[uid]["year"], "venue": cand[uid]["venue"],
               "abstract_available": "no" if src == "not found" else "yes", "abstract_source": src, "screening_round": a["round"],
               "code_A": a["code"], "confidence_A": a["confidence"], "reason_A": a["reason"],
               "code_B": b["code"], "confidence_B": b["confidence"], "reason_B": b["reason"],
               "code_C": "", "confidence_C": "", "reason_C": ""}
        if ea == eb:
            row["decided_by"], row["final"] = "both screeners", ("eligible" if ea else "not eligible")
            row["criterion"] = (a["code"] if a["code"] == b["code"] else "IC1 or IC2") if ea else ""
        else:
            c = C[(uid, a["round"])]
            row.update(code_C=c["code"], confidence_C=c["confidence"], reason_C=c["reason"], decided_by="third screener")
            ce = c["code"] in ELIGIBLE
            row["final"] = "eligible" if ce else "not eligible"
            first_el = a["code"] if ea else b["code"]
            row["criterion"] = (c["code"] if c["code"] == first_el else "IC1 or IC2") if ce else ""
        votes = ea + eb + (row["code_C"] in ELIGIBLE)
        row["eligible_votes"] = "%d of %d" % (votes, 3 if row["code_C"] else 2)
        rows.append(row)
    out = HERE / "phase4_eligibility"
    with open(out / "frame_screening.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    st = Counter((r["decided_by"], r["final"]) for r in rows)
    rounds = Counter(r["screening_round"] for r in rows)
    rep = ["Eligibility screening of the sampling frame: %d records outside the core search" % n, "",
           "Phase 1. Two independent screeners, all %d records" % n] + agreement_lines(first)
    e1 = Counter(("eligible" if a in ELIGIBLE else "not", "eligible" if b in ELIGIBLE else "not") for a, b in first)
    rep += ["  eligible by both %d, by one only %d, by neither %d"
            % (e1[("eligible", "eligible")], e1[("eligible", "not")] + e1[("not", "eligible")], e1[("not", "not")]), "",
            "Phase 2. Abstracts",
            "  records without an abstract in the search indexes: %d" % len(retrieved),
            "  abstract retrieved and record screened again by both screeners: %d (round 2: %d, round 3: %d)"
            % (rounds["2"] + rounds["3"], rounds["2"], rounds["3"]),
            "  no abstract found; decided on title and venue: %d" % sum(r["abstract_available"] == "no" for r in rows),
            "  sources: " + ", ".join("%s %d" % kv for kv in Counter(
                r["source_of_abstract"].split(" (")[0] for r in retrieved.values() if r["source_of_abstract"] != "not found").most_common()), "",
            "After phase 2 (latest code of each screener)"] + agreement_lines([(r["code_A"], r["code_B"]) for r in rows])
    both_el, both_not = st[("both screeners", "eligible")], st[("both screeners", "not eligible")]
    adj_el, adj_not = st[("third screener", "eligible")], st[("third screener", "not eligible")]
    rep += ["  eligible by both %d, by one only %d, by neither %d" % (both_el, adj_el + adj_not, both_not), "",
            "Phase 3. Third screener on the %d records on which the two differ" % (adj_el + adj_not),
            "  eligible %d, not eligible %d" % (adj_el, adj_not),
            "  confidence of the third screener: high %d, low %d"
            % (sum(r["confidence_C"] == "high" for r in rows), sum(r["confidence_C"] == "low" for r in rows)),
            "  of these, decided without an abstract: %d" % sum(r["decided_by"] == "third screener" and r["abstract_available"] == "no" for r in rows)]
    sample = [r for r in C_all if r["use"].startswith("agreement sample")]
    for kind in ("eligible", "not eligible"):
        g = [r for r in sample if "(%s by both" % kind in r["use"]]
        k = sum((r["code"] in ELIGIBLE) == (kind == "eligible") for r in g)
        rep.append("  check on a random sample of round-1 agreements (%s by both): third screener agrees on %d of %d (95%% CI %.0f to %.0f%%)"
                   % ((kind, k, len(g)) + wilson(k, len(g))))
    fin = Counter(r["final"] for r in rows)
    crit = Counter(r["criterion"] for r in rows if r["final"] == "eligible")
    rep += ["", "Phase 4. Final eligibility",
            "  eligible %d (by both screeners %d, by the third screener %d); IC1 %d, IC2 %d, criterion differs %d"
            % (fin["eligible"], both_el, adj_el, crit["IC1"], crit["IC2"], crit["IC1 or IC2"]),
            "  not eligible %d (by both screeners %d, by the third screener %d)" % (fin["not eligible"], both_not, adj_not), "",
            "  not eligible by both screeners, by code (records on which the two give the same code):"]
    same = Counter(r["code_A"] for r in rows if r["decided_by"] == "both screeners" and r["final"] == "not eligible" and r["code_A"] == r["code_B"])
    rep += ["    %-7s %5d" % kv for kv in same.most_common()]
    (out / "agreement_report.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep))

    # roles of the eligible records
    E = read(HERE / "phase5_selection" / "eligible_by_role.csv")
    assert {r["uid"]: r["eligible_by"] for r in E} == {r["uid"]: r["decided_by"] for r in rows if r["final"] == "eligible"}
    rr = ["Phase 5. Roles of the %d eligible records (two independent assignments)" % len(E), ""]
    for name, pp in (("role", [(r["role_A"], r["role_B"]) for r in E]), ("family", [(r["family_A"], r["family_B"]) for r in E])):
        po, k = kappa(pp)
        rr.append("%-8s agreement %.3f   Cohen's kappa %.3f" % (name, po, k))
    rr += ["", "role   eligible   by both screeners   by third screener   reports hardware   applied to an LLM   selected in the review"]
    for role in ROLES + [""]:
        g = [r for r in E if r["role"] == role]
        rr.append("%-4s %10d %19d %19d %18d %19d %10d" % (
            role or "none", len(g), sum(r["eligible_by"] == "both screeners" for r in g), sum(r["eligible_by"] == "third screener" for r in g),
            sum(r["hardware"] == "yes" for r in g), sum(r["llm"] == "yes" for r in g), sum(bool(r["selected_in_review"]) for r in g)))
    rr += ["", "none: the two assignments give different roles.",
           "hardware and llm are yes only where both assignments say yes (unclear where they differ).",
           "Both are read from titles and abstracts only, so the counts are lower bounds."]
    (HERE / "phase5_selection" / "role_report.txt").write_text("\n".join(rr) + "\n", encoding="utf-8")
    print("\n" + "\n".join(rr))


if __name__ == "__main__":
    main()
