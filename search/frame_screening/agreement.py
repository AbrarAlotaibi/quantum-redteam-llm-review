"""Merge the two screenings of the sampling frame and report their agreement.

Reads screener_A.csv and screener_B.csv (one code per record from each screener),
eligible_by_role.csv (the two role assignments of the eligible records), and
../candidates.csv (titles). Writes frame_screening.csv (one row per record, both codes
and the resulting status), agreement_report.txt, and role_report.txt.

Usage:  python search/frame_screening/agreement.py      (from the repository root)
"""
import csv
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


def main():
    A = {r["uid"]: r for r in read(HERE / "screener_A.csv")}
    B = {r["uid"]: r for r in read(HERE / "screener_B.csv")}
    cand = {r["uid"]: r for r in read(HERE.parent / "candidates.csv")}
    assert set(A) == set(B) and set(A) <= set(cand)
    assert all(r["code"] in CODES for r in list(A.values()) + list(B.values()))

    rows, pairs = [], []
    for uid in sorted(A):
        a, b = A[uid]["code"], B[uid]["code"]
        pairs.append((a, b))
        if a in ELIGIBLE and b in ELIGIBLE:
            status, consensus = "eligible", (a if a == b else "IC1 or IC2")
        elif a in ELIGIBLE or b in ELIGIBLE:
            status, consensus = "unresolved", ""
        else:
            status, consensus = "not eligible", (a if a == b else "%s / %s" % (a, b))
        c = cand[uid]
        rows.append({"uid": uid, "id": A[uid]["id"], "title": c["title"], "year": c["year"], "venue": c["venue"],
                     "code_A": a, "confidence_A": A[uid]["confidence"], "reason_A": A[uid]["reason"],
                     "code_B": b, "confidence_B": B[uid]["confidence"], "reason_B": B[uid]["reason"],
                     "status": status, "consensus": consensus})
    with open(HERE / "frame_screening.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    rep = ["Screening of the sampling frame: %d records outside the core search, two independent screenings" % len(rows), ""]
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    both = Counter(a for a, b in pairs if a == b)
    rep.append("code      screener A   screener B   both")
    for c in CODES:
        rep.append("%-8s %11d %12d %6d" % (c, ca[c], cb[c], both[c]))
    el = lambda c: "eligible" if c in ELIGIBLE else "not"
    g3 = lambda c: c if c in ELIGIBLE else "not"
    for name, pp in (("all eight codes", pairs), ("eligible or not", [(el(a), el(b)) for a, b in pairs]),
                     ("IC1, IC2, or not eligible", [(g3(a), g3(b)) for a, b in pairs])):
        po, k = kappa(pp)
        rep.append("%-26s agreement %.3f   Cohen's kappa %.3f" % (name, po, k))
    st = Counter(r["status"] for r in rows)
    rep += ["", "eligible by both screeners:     %5d  (IC1 %d, IC2 %d, criterion differs %d)"
            % (st["eligible"], sum(r["consensus"] == "IC1" for r in rows), sum(r["consensus"] == "IC2" for r in rows),
               sum(r["consensus"] == "IC1 or IC2" for r in rows)),
            "eligible by one screener only:  %5d  (unresolved)" % st["unresolved"],
            "not eligible by both screeners: %5d" % st["not eligible"], "", "disagreements by pair of codes (A, B):"]
    for (a, b), n in Counter((a, b) for a, b in pairs if a != b).most_common():
        rep.append("  %-7s %-7s %4d" % (a, b, n))
    (HERE / "agreement_report.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep[:17]))

    # roles of the eligible records
    E = read(HERE / "eligible_by_role.csv")
    assert {r["uid"] for r in E} == {r["uid"] for r in rows if r["status"] == "eligible"}
    rr = ["Role assignment of the %d records eligible by both screeners (two independent assignments)" % len(E), ""]
    for name, pp in (("role", [(r["role_A"], r["role_B"]) for r in E]), ("family", [(r["family_A"], r["family_B"]) for r in E])):
        po, k = kappa(pp)
        rr.append("%-8s agreement %.3f   Cohen's kappa %.3f" % (name, po, k))
    rr += ["", "role   eligible   reports hardware   applied to an LLM   selected in the review"]
    for role in ROLES:
        g = [r for r in E if r["role"] == role]
        rr.append("%-4s %10d %18d %19d %10d" % (role, len(g), sum(r["hardware"] == "yes" for r in g),
                                               sum(r["llm"] == "yes" for r in g), sum(bool(r["selected_in_review"]) for r in g)))
    rr.append("none %10d   (the two assignments differ)" % sum(r["role"] == "" for r in E))
    rr += ["", "hardware and llm are yes only where both assignments say yes (unclear where they differ).",
           "Both are read from titles and abstracts only, so the counts are lower bounds."]
    (HERE / "role_report.txt").write_text("\n".join(rr) + "\n", encoding="utf-8")
    print("\n" + "\n".join(rr))


if __name__ == "__main__":
    main()
