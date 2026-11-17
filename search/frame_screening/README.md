# Screening of the sampling frame (7,258 records)

Run 2026-11-18. The 7,312 records of `../candidates.csv` are the 54 records of the core search, screened in `../agreement_check/`, and 7,258 further records that form the sampling frame for the representative studies (Section 2.3 of the article). This folder holds the screening of those 7,258 records for eligibility.

## Procedure
1. **Rule.** `criteria.md` states the codes: eligible under `IC1` or `IC2`; not eligible under `EC1` to `EC4`, `REVIEW` (secondary study), or `NO` (meets neither inclusion criterion); and the order of precedence.
2. **Two independent screeners.** Two LLM agents each read only the rule and the records (title, year, venue, abstract), with no web access and no access to the other screening. Each received the records in its own random order, in batches of up to 150, and gave every record one code, a confidence, and a short reason.
   - **Screener A:** persona of a quantum machine learning researcher; applies the rule strictly and chooses the code that is not eligible when a record is ambiguous.
   - **Screener B:** persona of a researcher in LLM safety and natural language processing; applies the intent of the rule and chooses the eligible code when a record is ambiguous.
3. **Merge.** `agreement.py` merges the two into `frame_screening.csv` and writes `agreement_report.txt`. A record is counted as eligible only if both screeners found it eligible.
4. **Roles.** The eligible records were assigned to the six roles of the article twice, independently, under `role_rule.md`. `eligible_by_role.csv` holds both assignments; `role` is filled where they agree. `role_report.txt` gives the counts.

## Results

| | Records |
|---|---|
| Screened | 7,258 |
| Eligible by both screeners (IC1 433, IC2 1,428, criterion differs 1) | 1,862 |
| Eligible by one screener only | 663 |
| Not eligible by both | 4,733 |

Agreement on all eight codes is 86.7% (Cohen's kappa 0.81); on eligible or not, 90.9% (kappa 0.79). Agreement on the role of the eligible records is 99.1% (kappa 0.99). Eligible records by role: R1 322, R2 117, R3 1,054, R4 76, R5 274, R6 3; 16 records received different roles and are not assigned.

The 23 representative studies that are records of the frame are all eligible by both screeners (`../check_selection.py`).

## Limitations
- The decisions rest on titles and abstracts. The authors did not review them record by record.
- The 663 records on which the screeners differ are not adjudicated. They are marked `unresolved` in `frame_screening.csv` and in `../candidates.csv`.
- Eligibility is not selection. The article reviews 27 representative studies chosen by role from the eligible records and from snowballing, and does not review the other eligible records.
- Abstracts are not included here (see "What is not included" in the main README).
