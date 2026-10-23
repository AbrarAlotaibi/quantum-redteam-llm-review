# Direct database counts (run 2026-10-24)

Field: title and abstract. For ScienceDirect, "Title, abstract or author-specified keywords".

**Simplification used.** Every quantum term except "Born machine", "tensor network", QAOA, QUBO, HUBO and "Ising machine" contains the word `quantum`, so the quantum group reduces exactly to `quantum OR "Born machine" OR "tensor network" OR QAOA OR QUBO OR HUBO OR "Ising machine"`. This let IEEE Xplore and ACM DL run each search as a single query.

## IEEE Xplore
Command search, `"Document Title"` OR `"Abstract"`. Counts came from the site's own search endpoint, called from the results page. 2018 to 2026 via the year range for S2 to S4. No subject filter is available.

| Search | Records | Notes |
|---|---|---|
| S1 core (Q AND L AND S) | 3 | All three are already in the core set: bajaj2026hybridjailbreak (include), chen2024qpsoattack (include), kamath2026quantumaware (related review) |
| S2 (Q AND L) | 249 | |
| S3 (Q AND S) | 29 | No CS filter on IEEE |
| S4 (Q AND G) | 645 | No CS filter on IEEE |

## ACM Digital Library
Advanced search, ACM Full-Text Collection (`expand=dl`), `Title:(...) OR Abstract:(...)` for each group. ACM's parsed query confirmed that every OR was kept. E-publication date 2018 to 2026 for S2 to S4.

| Search | Records |
|---|---|
| S1 core | 0 |
| S2 | 42 |
| S3 | 4 |
| S4 | 96 |

## ScienceDirect
At most 8 boolean connectors per field, so the quantum group was split into {quantum}, {"Born machine", "tensor network", QAOA} and {QUBO, HUBO, "Ising machine"}. For S1, the language and security groups were each split into halves, giving 12 sub-queries.

**S1 core, sub-queries 1 to 11:** 2 unique records in total, both from sub-query 4 (quantum AND NLP/text/language generation AND adversarial attack/attack strategy/safety evaluation):
- S108480452400208X: JNCA 6G adversarial-attacks survey (R44, already in the core set, excluded E2)
- S1566253524007000: Information Fusion "AI-driven fusion with cybersecurity" review (R46, already in the core set, excluded E2)

All other sub-queries returned 0.

**Sub-query S1-12: 0 records.** It was blocked for the automated run, because ScienceDirect rate-limited the browser after 11 queries. The first author then ran it manually on 2026-10-24, and it returned no records. The query is: (QUBO OR HUBO OR "Ising machine") AND ("natural language processing" OR "text generation" OR "language generation") AND ("adversarial attack" OR "attack strategy" OR "safety evaluation").

**ScienceDirect core total: 2 unique records, both already in the core set.**

**S2 to S4 (sampling frame).** 2018 to 2026. S3 and S4 are restricted to the Computer Science subject area (`subjectAreas=1700`), matching the API searches; S2 has no subject filter. Each search is split into the same three quantum sub-groups, and the union is deduplicated by PII. All results fit on one page (`show=100`), so every PII was read.

| Search | {quantum} | {Born machine, tensor network, QAOA} | {QUBO, HUBO, Ising machine} | Unique |
|---|---|---|---|---|
| S2 (Q AND L) | 103 | 5 | 2 | 110 |
| S3 (Q AND S), CS | 18 | 0 | 0 | 18 |
| S4 (Q AND G), CS | 71 | 16 (2 not in sub-query 1) | 16 (4 not in sub-queries 1 or 2) | 77 |

The first author loaded the S2 to S4 sub-queries manually in the browser after the rate limit, and the counts and PIIs were read from those pages.

## Summary

| Search | IEEE Xplore | ACM DL | ScienceDirect |
|---|---|---|---|
| S1 core | 3 (all in core set) | 0 | 2 (both in core set) |
| S2 (Q AND L) | 249 | 42 | 110 |
| S3 (Q AND S) | 29 (no CS filter) | 4 | 18 |
| S4 (Q AND G) | 645 (no CS filter) | 96 | 77 |

**Conclusion.** No direct database search returned a core record outside the 54 screened from the open indexes. The S2 to S4 results were not merged into `candidates.csv`; they are reported as a coverage check only.
