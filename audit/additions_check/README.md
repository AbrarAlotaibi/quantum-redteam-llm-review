# Second scoring of the seven studies added on 18 November 2026

Seven studies of the eligible pool were added to the primary studies after the sampling frame had been screened: `dallaire2018qgan`, `amin2018qbm`, `benedetti2019generative` (R1), `romero2025hubo`, `pelofske2023qaoa` (R3), `gilliam2021grover` (R4), and `lorenz2023qnlp` (R5). They were chosen by the stated order of priority: studies that introduced a method family, then studies that report its largest scale or a hardware result.

## Procedure
1. **First scoring.** An LLM agent read the full text of each study (the arXiv version) and wrote an audit record in the format of `../audit_scores.json`, scoring QA1 to QA5 under `../audit_check/rubric.md` with evidence for each score.
2. **Second scoring.** A second LLM agent read the same full text and scored QA1 to QA5 under the same rubric, without access to the first record. Its scores and evidence are in `second_scoring_<key>.json`, next to the first scores.
3. **Adjudication.** The two scorings agree on 33 of 35 scores (Cohen's kappa 0.90). The two differences were settled from the evidence quoted by both, and the reason is in the `notes` field of the record:
   - `amin2018qbm`, QA2: Y and P. Recorded as P, because the model is evaluated by exact diagonalization and has no circuit depth to report.
   - `lorenz2023qnlp`, QA1: P and Y. Recorded as P, because the optimizer's gain settings are not stated.

## Limitation
Both scorings were made by LLM agents. The authors have not yet checked these seven records against the papers.

## Study no longer counted as a primary study
`singh2026qubo` was read again in full. The only solver it names is classical simulated annealing on a generic QUBO, and quantum and Ising hardware are named as future work, so it does not meet IC1. Its earlier audit record is kept in `../full_text_exclusions.json`.
