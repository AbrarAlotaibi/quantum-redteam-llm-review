# Blind re-scoring check on the evidence audit (10-study subset)

Run on 2026-10-24.

## Subset
Ten of the 30 audited studies, stratified across all six roles and all execution modes:
- **R1:** layden2023qmcmc, huang2025generative
- **R2:** khatri2024quixer, kong2025hyqut, kong2025qtha
- **R3:** floresgarrigos2025qcr
- **R4:** chen2024qpsoattack
- **R5:** bajaj2026hybridjailbreak, li2025qkd
- **R6:** you2026seed

## Procedure
Two LLM agents read only `rubric.md` and the ten full texts. They had no access to the original scores, and no web access except `curl -I` on code links printed in a paper.

| Agent | Persona | Strategy | Output |
|---|---|---|---|
| A | Experimental quantum computing reviewer | Strict: credits only what is explicitly reported; lower score when information is missing | `scorer_A.csv` |
| B | ML methodologist (NLP and LLM evaluation) | Reads for intent; higher score on genuinely borderline cases | `scorer_B.csv` |

`audit_agreement.py` pools the 50 ratings (10 studies x QA1 to QA5) and writes `audit_disagreements.csv`.

## Results

| Comparison | Kappa |
|---|---|
| Fleiss, three scorers | 0.728 (observed 0.827) |
| Cohen, primary vs. A | 0.717 |
| Cohen, primary vs. B | 0.719 |
| Cohen, A vs. B | 0.751 |

Number of studies (out of 10) on which all three scorers agreed, per criterion:

| QA1 | QA2 | QA3 | QA4 | QA5 |
|---|---|---|---|---|
| 5 | 8 | 8 | 7 | 9 |

## Adjudication (first author, 13 disagreements)
- **Changed by majority:**
  - chen2024qpsoattack QA1: P to Y
  - huang2025generative QA1: P to Y
  - kong2025hyqut QA4: N to P
- **Kept against both re-scorers:**
  - **huang2025generative QA3 = P.** Its classical baselines are 1e6 to 1e8 times larger than the quantum model, which we do not count as matched in size.
  - **layden2023qmcmc QA5 = Y.** The version of record (Nature) links a Zenodo code archive; the re-scorers only had the arXiv v1 text.
- **Majority equals the primary score (no change):** the other 8.

The headline counts are unchanged: 4 of 19 circuit-based studies have a matched classical baseline, 1 of the 9 with hardware results does, and 11 of 30 studies release code.

**Limitation:** this is a transparency check on the rubric, not formal agreement between independent human reviewers.
