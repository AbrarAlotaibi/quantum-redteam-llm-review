# Quantum and quantum-inspired methods for red teaming LLMs: review data and code

Companion repository for the critical review *"Quantum and quantum-inspired methods for red teaming large language models: A critical review of roles and evidence"* (Alotaibi and Ahmed, under review).

It contains the documented literature search, the screening of the core intersection with its agreement check, and the per-study evidence audit. All tables in the article's review method (Section 2) and evidence audit (Section 5) can be traced to these files.

## Contents

```
search/
  search.py              reproducible search over OpenAlex, arXiv and Semantic Scholar (Python standard library only)
  queries.json           exact query strings sent to each source, for each search
  search_log.md          run date, per-source counts, deduplication rules, pre-screen keyword rules
  manual_queries.md      the same strings formatted for IEEE Xplore, ACM DL and ScienceDirect
  manual_counts.md       direct IEEE Xplore, ACM DL and ScienceDirect counts (2026-10-24), a coverage check
  candidates.csv         7,312 unique records (metadata only; see "What is not included")
  s1_screening.csv       final decisions for the 54 core-search records, with all three screenings and the adjudication
  agreement_check/       blind two-agent agreement check on the core screening (README inside)
audit/
  audit_scores.json/csv  evidence audit of the 30 primary studies: QA1 to QA5, execution mode, scale, baselines, evidence
  audit_check/           blind two-agent re-scoring of a 10-study subset (README inside)
  table2_check/          full-text evidence for the related-review coverage marks
```

## Search design (summary)
The searches match titles and abstracts and combine four term groups:
- **Q:** quantum and quantum-inspired methods
- **L:** a language-model anchor
- **G:** generative and optimization components
- **S:** adversarial evaluation

There are four searches:
- the **core search**, Q∧L∧S with no year limit, which gave 54 unique records, all screened;
- three **sampling-frame searches** for 2018 to 2026: Q∧L, then Q∧S and Q∧G, the last two restricted to computer science.

Together they returned 13,122 records, or 7,312 unique records after deduplication by DOI, arXiv id and normalized title. The searches were run on 2026-10-23. Exact strings and counts are in `search/queries.json` and `search/search_log.md`.

## Screening and agreement check (summary)
The 54 core records were screened against the rule in `search/agreement_check/criteria.md`. The first screening was LLM-assisted. Two further LLM agents then re-screened all 54 blind, using distinct personas and decision strategies:
- **Agent A:** a quantum-ML researcher using a strict checklist, excluding on ambiguity;
- **Agent B:** an LLM-safety researcher reading for intent, including on ambiguity.

Fleiss' kappa across the three screenings was 0.89 on include vs. not and 0.79 over all six decision codes. The first author adjudicated all 11 disagreements. This is a transparency probe on how precisely the inclusion rule can be applied, not formal human inter-rater agreement.

## Audit check (summary)
Two blind LLM agents with distinct reviewer personas re-scored a stratified subset of ten studies on QA1-QA5. Fleiss' kappa over the 50 ratings was 0.73; the first author adjudicated the 13 disagreements. Details in `audit/audit_check/README.md`.

## Reproducing
- `python search.py fetch` re-queries the APIs. The results will drift as the indexes grow.
- `python search.py build` rebuilds every output from cached responses. The cache is not included (see below) but is available from the authors on request.
- `search/agreement_check/agreement.py` recomputes the kappa values from the screening files.

## What is not included
- **Abstracts and raw API responses.** These contain publisher and API-provider content, so `candidates.csv` and the agreement-check packets keep metadata only (title, year, venue, DOI, arXiv id). The full versions are available from the corresponding author on request.
- **Full texts of the audited papers.** Retrieve them through their DOIs.

## Licence
- **Code** (`*.py`): MIT, see `LICENSE`.
- **Our annotations** (screening decisions, audit scores, agreement-check records): CC BY 4.0, see `LICENSE-DATA`.
- **Bibliographic metadata:** from OpenAlex (CC0), arXiv (CC0 metadata) and Semantic Scholar, under their respective terms.

## Citation
Please cite the article (citation to be added on publication).
