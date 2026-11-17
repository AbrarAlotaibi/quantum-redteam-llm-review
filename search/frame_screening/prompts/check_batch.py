"""Check one screener output: python3 check_batch.py <A|B> <batch number, e.g. 01>"""
import csv, re, sys
tag, n = sys.argv[1], sys.argv[2]
base = "."  # the working folder that holds batches_<A|B>/ and out_<A|B>/
ids = re.findall(r"^### (P\d{5})\s*$", open("%s/batches_%s/batch_%s_%s.txt" % (base, tag, tag, n), encoding="utf-8").read(), flags=re.M)
path = "%s/out_%s/batch_%s_%s.csv" % (base, tag, tag, n)
try:
    rows = list(csv.DictReader(open(path, encoding="utf-8", newline="")))
except FileNotFoundError:
    print("PROBLEM: output file not found:", path); sys.exit(1)
problems = []
if not rows or list(rows[0].keys()) != ["id", "code", "confidence", "reason"]:
    problems.append("header must be exactly: id,code,confidence,reason (found %s)" % (list(rows[0].keys()) if rows else "no rows"))
else:
    got = [r["id"] for r in rows]
    if got != ids:
        missing = [i for i in ids if i not in got]; extra = [i for i in got if i not in ids]
        dup = sorted({i for i in got if got.count(i) > 1})
        problems.append("ids differ from the batch: %d rows for %d records; missing %s; unexpected %s; duplicated %s; order %s"
                        % (len(got), len(ids), missing[:10], extra[:10], dup[:10], "ok" if sorted(got) != sorted(ids) or got == ids else "differs from the batch order"))
    bad = [r["id"] for r in rows if r["code"] not in ("IC1", "IC2", "EC1", "EC2", "EC3", "EC4", "REVIEW", "NO")]
    if bad: problems.append("invalid code in rows: %s" % bad[:10])
    bad = [r["id"] for r in rows if r["confidence"] not in ("high", "low")]
    if bad: problems.append("confidence must be high or low in rows: %s" % bad[:10])
    bad = [r["id"] for r in rows if not (r["reason"] or "").strip() or None in r.values() or len(r) != 4]
    if bad: problems.append("empty reason or wrong number of fields (quote reasons that contain commas) in rows: %s" % bad[:10])
if problems:
    print("PROBLEM:\n- " + "\n- ".join(problems)); sys.exit(1)
from collections import Counter
print("OK: %d rows. %s" % (len(rows), dict(Counter(r["code"] for r in rows))))
