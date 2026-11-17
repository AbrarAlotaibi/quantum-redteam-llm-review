"""Check one role-assignment output: python3 check_roles.py <A|B> <batch number, e.g. 01>"""
import csv, re, sys
from collections import Counter
tag, n = sys.argv[1], sys.argv[2]
base = "."  # the working folder that holds batches_<A|B>/ and out_<A|B>/
FAM = "born_machine quantum_gan quantum_boltzmann_or_annealer_generative quantum_diffusion quantum_autoencoder tensor_network_generative quantum_sampling_mcmc quantum_language_model_or_transformer quantum_recurrent quantum_finetuning_or_adapter tensor_network_compression quantum_annealing qaoa_or_variational_optimization qubo_ising_formulation_or_solver quantum_inspired_evolutionary quantum_inspired_swarm grover_or_amplitude_amplification compositional_qnlp hybrid_circuit_text_classifier quantum_kernel quantum_inspired_language_model qrng other".split()
ids = re.findall(r"^### (P\d{5})\s*$", open("%s/batches_%s/batch_%s_%s.txt" % (base, tag, tag, n), encoding="utf-8").read(), flags=re.M)
path = "%s/out_%s/batch_%s_%s.csv" % (base, tag, tag, n)
try:
    rows = list(csv.DictReader(open(path, encoding="utf-8", newline="")))
except FileNotFoundError:
    print("PROBLEM: output file not found:", path); sys.exit(1)
p = []
if not rows or list(rows[0].keys()) != ["id", "role", "family", "hardware", "llm"]:
    p.append("header must be exactly: id,role,family,hardware,llm")
else:
    got = [r["id"] for r in rows]
    if got != ids:
        p.append("ids differ from the batch: %d rows for %d records; missing %s; unexpected %s" % (len(got), len(ids), [i for i in ids if i not in got][:10], [i for i in got if i not in ids][:10]))
    for col, ok in (("role", {"R1", "R2", "R3", "R4", "R5", "R6"}), ("family", set(FAM)), ("hardware", {"yes", "no"}), ("llm", {"yes", "no"})):
        bad = [r["id"] for r in rows if r[col] not in ok]
        if bad: p.append("invalid %s in rows: %s" % (col, bad[:10]))
if p:
    print("PROBLEM:\n- " + "\n- ".join(p)); sys.exit(1)
print("OK: %d rows. %s" % (len(rows), dict(Counter(r["role"] for r in rows))))
