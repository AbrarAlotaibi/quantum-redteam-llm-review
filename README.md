# Quantum and quantum-inspired methods for red teaming LLMs: review data and code

Companion repository for the critical review *"Utilizing quantum and quantum-inspired methods in red teaming large language models: A critical review of potential, applications, and risks"* (Alotaibi and Ahmed, under review).

It contains the documented literature search, the screening of the core intersection with its agreement check, the per-study evidence audit, and the illustration of the evaluation methodology. All tables in the article's review method (Section 2) and evidence audit (Section 6) can be traced to these files, and the data-driven figures (the audit summary, the summary by role, and the coverage curves of the illustration) can be regenerated from them.

## Contents

```
search/
  search.py              reproducible search over OpenAlex, arXiv and Semantic Scholar (Python standard library only)
  queries.json           exact query strings sent to each source, for each search
  search_log.md          run date, per-source counts, deduplication rules, pre-screen keyword rules
  manual_queries.md      the same strings formatted for IEEE Xplore, ACM DL and ScienceDirect
  manual_counts.md       direct IEEE Xplore, ACM DL and ScienceDirect counts (2026-10-24), a coverage check
  candidates.csv         7,312 unique records (metadata only; see "What is not included"). Its `include` and
                         `exclusion_reason` columns are empty: the sampling frame was not screened record by
                         record, and the studies selected from it are listed in selected_studies.csv
  s1_screening.csv       final decisions for the 54 core-search records, with all three screenings and the adjudication
  selected_studies.csv   the 30 primary studies: record in the sampling frame (if any), route into the review, criterion
  check_selection.py     checks that list against candidates.csv, s1_screening.csv and the audit scores
  agreement_check/       blind two-agent agreement check on the core screening (README inside)
audit/
  audit_scores.json/csv  evidence audit of the 30 primary studies: QA1 to QA5, execution mode, scale, baselines, evidence
  audit_check/           blind two-agent re-scoring of a 10-study subset (README inside)
  table2_check/          full-text evidence for the related-review coverage marks, including the risk-analysis column
figures/
  make_figure_data.py    audit scores -> the counts behind the audit summary and the summary by role;
                         also checks the register sizes of the scale figure against the audit scores
  make_pilot_curves.py   pilot log -> coverage per target query, mean and 95% CI over seeds
  data/                  the generated tables that the figures read; scale_registers.csv lists each register
                         size of the scale figure with its unit, execution mode, and location in the source
pilot/
  rerun/                 per-query log, per-seed results, summary and sensitivity check of a rerun of the notebook
  nb_to_script.py        turns the notebook into a script that saves its log
  check_pilot_numbers.py recomputes the illustration's table and paired differences from the log
protocol_pilot_tier1.ipynb   executed notebook of the illustration (synthetic judge, exact simulation)
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

## Illustration of the evaluation methodology (summary)
`protocol_pilot_tier1.ipynb` applies the six steps of the article's evaluation methodology (Section 7.4) to a synthetic benchmark: 12 attack components, 100 goals in 10 categories, 40 behavior cells, 200 target queries per generator and seed, and 20 seeds. It compares a Born machine with a classical autoregressive model of matched size, and an annealer and QAOA with a linear selector. The target and judge are a fixed synthetic success function and all circuits are simulated exactly, so the result illustrates the methodology and is not evidence about real targets or quantum hardware.

`pilot/rerun/` holds the log of an independent rerun (torch 2.15.0, pennylane 0.45.1). It reproduces the table of the illustration and the paired differences quoted in the article. The article calls the six steps an evaluation methodology; the notebook's file name and code keep the earlier word, protocol.

## Reproducing
- `python search.py fetch` re-queries the APIs. The results will drift as the indexes grow.
- `python search.py build` rebuilds every output from cached responses. The cache is not included (see below) but is available from the authors on request.
- `search/agreement_check/agreement.py` recomputes the kappa values from the screening files.
- `python figures/make_figure_data.py audit/audit_scores.csv figures/data` rebuilds the audit counts behind the figures.
- `python search/check_selection.py` checks the selection of the 30 primary studies against the released records.
- `python pilot/nb_to_script.py protocol_pilot_tier1.ipynb run_pilot.py`, then `python run_pilot.py`, reruns the illustration and writes `log.csv` (about ten minutes on a CPU; needs numpy, pandas, scipy, scikit-learn, matplotlib, torch and pennylane).
- `python pilot/check_pilot_numbers.py pilot/rerun/log.csv` recomputes the table of the illustration and the paired differences, and `python figures/make_pilot_curves.py pilot/rerun/log.csv figures/data` rebuilds the coverage curves.

## What is not included
- **Abstracts and raw API responses.** These contain publisher and API-provider content, so `candidates.csv` and the agreement-check packets keep metadata only (title, year, venue, DOI, arXiv id). The full versions are available from the corresponding author on request.
- **Full texts of the audited papers.** Retrieve them through their DOIs.

## Licence
- **Code** (`*.py`): MIT, see `LICENSE`.
- **Our annotations and run logs** (screening decisions, audit scores, agreement-check records, figure data, logs of the illustration): CC BY 4.0, see `LICENSE-DATA`.
- **Bibliographic metadata:** from OpenAlex (CC0), arXiv (CC0 metadata) and Semantic Scholar, under their respective terms.

## Citation
Please cite the article (citation to be added on publication).
