# Eligibility screening of the sampling frame (7,258 records)

The 7,312 records of `../candidates.csv` are the 54 records of the core search, screened in `../agreement_check/`, and 7,258 further records that form the sampling frame for the representative studies (Section 2.3 of the article). This folder holds the screening of those 7,258 records for eligibility, in the order in which it was done (17 and 18 November 2026).

## Phases

| Phase | Folder | What was done | Result |
|---|---|---|---|
| 1. Screening | `phase1_screening/` | Two LLM agents (screeners A and B) each gave every record one code from title, year, venue, and abstract, under the rule in `criteria.md`. | Eligible by both 1,862, by one only 663, by neither 4,733 |
| 2. Abstracts | `phase2_abstracts_and_rescreening/` | 860 records had no abstract in the search indexes. An abstract was retrieved for 699 of them (Crossref, Semantic Scholar, OpenAlex, arXiv, the publishers' pages, and a web search by title), and a partial text from a search result for 5 more. Both screeners coded those 704 records again, blind to their first codes. | Eligible by both 1,961, by one only 583, by neither 4,714 |
| 3. Adjudication | `phase3_adjudication/` | A third LLM agent (screener C) coded the records on whose eligibility A and B differ, blind to their codes. It also coded a random sample of 200 records on which they agreed in phase 1, as a check. | Of the 583: eligible 361, not eligible 222. Sample: agrees on 199 of 200 |
| 4. Eligibility | `phase4_eligibility/` | `frame_screening.csv` holds, per record, the latest code of A and B, the code of C where there is one, and the final decision. A record is eligible if A and B both find it eligible; where they differ, C decides. | Eligible 2,322, not eligible 4,936 |
| 5. Selection | `phase5_selection/` | The eligible records were assigned to the six roles of the article twice, independently, under `role_rule.md`. The representative studies of the article are selected from this pool by role; they are listed in `../selected_studies.csv`. | 23 of the eligible records are reviewed; all 23 are eligible by both screeners |

`agreement.py` rebuilds `phase4_eligibility/frame_screening.csv`, `agreement_report.txt`, and `phase5_selection/role_report.txt` from the files of phases 1 to 3 and the role assignments. `../fill_decisions.py` then writes the decision of every record into `../candidates.csv`, and `../check_selection.py` checks the counts above.

## The screeners

- **Screener A:** persona of a quantum machine learning researcher; applies the rule strictly and chooses the code that is not eligible when a record is ambiguous.
- **Screener B:** persona of a researcher in LLM safety and natural language processing; applies the intent of the rule and chooses the eligible code when a record is ambiguous.
- **Screener C:** persona of the first author, who wrote the criteria; decides each record on its merits with no default in either direction.

Each agent read only the rule and its own batch of records, with no web access and no access to any other screening. Each screener received the records in its own random order, in batches of up to 150.

## Files

| File | Content |
|---|---|
| `criteria.md`, `role_rule.md` | the two rules, as given to the agents |
| `prompts/` | the instructions given for each batch (`screener_prompt.txt` with the personas, `role_prompt.txt`), and the format checks each agent ran on its own output |
| `phase1_screening/screener_A.csv`, `screener_B.csv` | one row per record: batch, code, confidence, reason; rows are in the order in which the screener received them |
| `phase2_abstracts_and_rescreening/retrieved_abstracts.csv` | the 860 records without an abstract in the search indexes: where an abstract was found, and the round in which the record was screened again |
| `phase2_abstracts_and_rescreening/screener_A_rescreen.csv`, `screener_B_rescreen.csv` | the new codes of the 704 records whose abstract was found |
| `phase3_adjudication/screener_C.csv` | the third screener's codes; the column `use` says whether a row is an adjudication, part of the agreement sample, or superseded because the record was screened again with its abstract |
| `phase4_eligibility/frame_screening.csv` | the final sheet: all codes and reasons, the number of eligible votes, who decided, and the final decision |
| `phase5_selection/eligible_by_role.csv` | the 2,322 eligible records: both role and family assignments, the agreed role, hardware and LLM use, and the study key if the record is reviewed in the article |

The prompts are verbatim except that the absolute paths of the working folder are shortened, the batch number is a placeholder, and three sentences about the first author in the persona of screener C are left out. The numbers that the article quotes from this screening are computed by `../../figures/make_screening_numbers.py`.

## Agreement

Between A and B, on all eight codes: 86.7% in phase 1 (Cohen's kappa 0.81) and 88.0% after phase 2 (kappa 0.83). On eligible or not: 90.9% (kappa 0.79) and 92.0% (kappa 0.81). Agreement on the role of the eligible records is 98.7% (kappa 0.98); 30 records received different roles and are not assigned.

## Limitations

- The decisions rest on titles and abstracts, and they were made by LLM agents. The authors did not review them record by record.
- For 156 records no abstract was found, and they are decided on title and venue; 33 of these went to the third screener. They are marked in the column `abstract_available`.
- The third screener marked 526 of its 583 decisions as low confidence. These are the records that two screeners read differently, so its decision is a third vote on an ambiguous record.
- The three screeners are instances of the same model, so their agreement does not rule out errors that they share.
- Eligibility is not selection. The article reviews 27 representative studies chosen by role from the eligible records and from snowballing, and does not review the other eligible records.
- Abstracts are not included here (see "What is not included" in the main README), so the batch files that the agents read are not in this folder.
