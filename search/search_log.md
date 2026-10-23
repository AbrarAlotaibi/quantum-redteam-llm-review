# Literature search log

Survey: quantum and quantum-inspired methods for LLMs, read through LLM red teaming.

This log records what the searches returned. Nothing here is an inclusion decision. `include` and `exclusion_reason` in `candidates.csv` are left empty for the authors.

## Run

- Run date: 2026-10-23 (the API calls ran from 2026-10-23T00:30:44Z to 2026-10-23T00:33:28Z UTC; per-page timestamps are in `raw/*_manifest.json`).
- Log built: 2026-10-23T00:39:34Z UTC.
- Command: `set PYTHONIOENCODING=utf-8` then `python -I search.py all` (equivalently `fetch`, `diagnose`, `build`). The script uses only the Python 3.13 standard library. Raw responses are cached in `raw/`, and `build` regenerates every output offline from them.
- No API keys were used. No e-mail address, `mailto` parameter or other personal data was sent. The User-Agent is generic (`quantum-redteam-survey-literature-search/1.0 (Python-urllib)`).

## Term groups

- **Q** (quantum): quantum, "quantum-inspired", "quantum-enhanced", "hybrid quantum-classical", "variational quantum circuit", "parameterized quantum circuit", "Born machine", "tensor network", "quantum annealing", QAOA, QUBO, HUBO, "Ising machine"
- **L** (language anchor): "large language model", LLM, "language model", "natural language processing", "text generation", "language generation"
- **G** (generative/optimization components): "generative model", "Born machine", "quantum GAN", "quantum diffusion", "quantum Boltzmann machine", "combinatorial optimization"
- **S** (security): "red teaming", jailbreak, "adversarial prompt", "adversarial attack", "attack strategy", "safety evaluation"

Searches: **S1** = Q AND L AND S, no year limit; **S2** = Q AND L, 2018-2026; **S3** = Q AND S, 2018-2026, computer science; **S4** = Q AND G, 2018-2026, computer science or machine learning; first 3000 per source.
Exact strings sent to each source are in `queries.json` and in the `url` of each page in `raw/*_manifest.json`.

## Counts per source and search

*Reported* is the total hit count the API returned for the query (OpenAlex `meta.count`, arXiv `opensearch:totalResults`, Semantic Scholar `total`). *Retrieved* is the number of records downloaded and parsed.

| Source | S1 reported | S1 retrieved | S2 reported | S2 retrieved | S3 reported | S3 retrieved | S4 reported | S4 retrieved |
|---|---|---|---|---|---|---|---|---|
| OpenAlex | 58 | 58 | 3320 | 3320 | 552 | 552 | 3141 | 3000 (cap) |
| arXiv | 1 | 1 | 614 | 614 | 76 | 76 | 777 | 777 |
| Semantic Scholar | 17 | 17 | 1476 | 1476 | 383 | 383 | 2848 | 2848 |

- **Cap applied:** OpenAlex S4 reported 3141 records, which is over the limit. Kept the first 3000 by OpenAlex relevance (`sort=relevance_score:desc`).

Unique records (after deduplication) found by each search, across all sources: S1 = 54, S2 = 3275, S3 = 582, S4 = 3587.

Unique records found by each source: OpenAlex = 6355, arXiv = 1441, Semantic Scholar = 4552; found by only one source: OpenAlex only = 2712, arXiv only = 40, Semantic Scholar only = 708.

### OpenAlex records by publisher / host (retrieved records)

The bucket comes from the work's DOI prefix (10.1109 is IEEE, 10.1145 ACM, 10.1016 Elsevier/ScienceDirect, 10.18653 ACL, 10.36227 TechRxiv, and so on). Records without a DOI are bucketed by an ACL Anthology, TechRxiv or arXiv landing URL. For a capped search the breakdown covers only the retrieved records.

| Publisher / host | S1 | S2 | S3 | S4 |
|---|---|---|---|---|
| IEEE | 6 | 258 | 82 | 486 |
| ACM | 0 | 37 | 8 | 73 |
| Elsevier (ScienceDirect) | 2 | 97 | 23 | 101 |
| ACL Anthology | 0 | 22 | 0 | 0 |
| TechRxiv | 2 | 15 | 6 | 7 |
| arXiv (no publisher DOI) | 2 | 445 | 49 | 735 |
| Zenodo | 19 | 1016 | 64 | 122 |
| other DOI prefix | 16 | 650 | 118 | 300 |
| Springer Nature | 2 | 210 | 83 | 365 |
| APS | 0 | 21 | 16 | 209 |
| SSRN | 3 | 99 | 11 | 35 |
| IOP | 0 | 23 | 18 | 104 |
| MDPI | 0 | 45 | 19 | 45 |
| no DOI, unknown host | 1 | 53 | 7 | 31 |
| Wiley | 1 | 38 | 5 | 45 |
| Research Square | 1 | 41 | 6 | 39 |
| Preprints.org | 0 | 28 | 3 | 8 |
| RSC | 0 | 16 | 0 | 22 |
| Optica | 0 | 1 | 5 | 32 |
| (all other buckets) | 3 | 205 | 29 | 241 |

OpenAlex work types among retrieved records: S1: article 22, preprint 15, conference-paper 6, book-chapter 4, other 4, dissertation 2; S2: preprint 1171, article 1109, conference-paper 416, book-chapter 173, other 73, dissertation 72; S3: article 275, conference-paper 105, preprint 98, book-chapter 36, book 9, review 8; S4: article 1271, preprint 851, conference-paper 621, book-chapter 75, dissertation 64, peer-review 23.

Retrieved records with no abstract, by source: OpenAlex 905 of 6930 (13%); arXiv 0 of 1468 (0%); Semantic Scholar 460 of 4724 (10%). Unique records with no abstract from any source: 810 of 7312.

Unique records with a Zenodo DOI (10.5281): 1165 (S1 20, S2 999, S3 64, S4 129). Zenodo deposits are self-published, not peer-reviewed, and include many recent single-author uploads. They make up a large share of the OpenAlex S2 hits.

## Deviations and source-specific notes

**OpenAlex**

- The boolean query goes in `filter=title_and_abstract.search:<query>` with uppercase AND/OR, parentheses and double-quoted phrases. Small test queries confirmed that OpenAlex honours them: `quantum` gives 1,760,744 hits, `quantum NOT "large language model"` gives 1,759,293, and `quantum AND "large language model"` gives 1,451, which add up. OpenAlex stems terms and treats a hyphen inside a quoted phrase as a space (`"quantum-inspired"` and `"quantum inspired"` both gave 7,113). This matches the intended title-and-abstract search.
- Computer-science restriction (S3, S4): `primary_topic.field.id:17` (topic-taxonomy field 17 is Computer Science). OpenAlex files machine learning under Computer Science (subfield 1702 Artificial Intelligence and related topics), so this one filter is the "computer science or machine learning" restriction for S4. Alternatives tested on `quantum AND "large language model"`: `primary_topic.field.id:17` gave 800, `topics.field.id:17` (any of up to 3 topics) gave 1,085, legacy concept CS `concepts.id:C41008148` gave 1,258, and legacy concept ML `C119857082` gave 168. The primary-topic field was chosen as the documented and current taxonomy. It is the strictest of these, so S3 and S4 exclude quantum-ML papers whose primary topic is in Physics and Astronomy. In a test of `quantum AND "generative model"` over 2018-2026, 124 of 1,057 hits were in Physics and Astronomy. These are covered only through the arXiv `stat.ML`/`cs.*` cross-lists, Semantic Scholar, and S2 where they mention language.
- Year limit: `publication_year:2018-2026`. S1 has no year filter.
- Ordering and paging: `sort=relevance_score:desc`, `per-page=200`, **basic paging (`page=1,2,...`)**. The planned cursor paging (`cursor=*`) failed: page 2 returned HTTP 401 `API key required for cursor paging`, because OpenAlex now requires an API key for cursor paging. Basic paging works without a key for the first 10,000 results, which covers every search here. All OpenAlex pages were therefore re-fetched with basic paging. Basic paging can in principle shift records between pages when relevance scores tie. Within-search duplicate OpenAlex ids after paging: S1 0, S2 0, S3 0, S4 1.
- Budget: unauthenticated OpenAlex calls now draw on a shared daily budget per IP address ($0.10/day at $0.001 per call, so about 100 calls). The API's notice suggests requesting a key by e-mail. That was not done, per the instruction not to send personal data. Each page's `X-RateLimit-Remaining-USD` is recorded in the manifest.
- Publisher coverage: OpenAlex includes IEEE, ACM, Elsevier/ScienceDirect, ACL Anthology and TechRxiv metadata. OpenAlex has no abstract for some works, so for those the match can only come from the title. The no-abstract counts above show how many.

**arXiv**

- Each term is searched in the title or the abstract: `(ti:<term> OR abs:<term>)`, joined with AND/OR in parentheses. Tests showed that the arXiv engine stems (`abs:LLM` and `abs:LLMs` both 82,642; `abs:"tensor network"` and `abs:"tensor networks"` both 3,449) and treats a hyphen in a phrase as a space (`abs:"quantum-inspired"` and `abs:"quantum inspired"` both 714). The query is therefore the exact boolean expression with no extra variants.
- Year limit: `submittedDate:[201801010000 TO 202612312359]`. This uses the first-version submission date, not the journal publication year.
- CS restriction: `cat:cs.*` for S3 and `(cat:cs.* OR cat:stat.ML)` for S4. `cat:` matches primary **or cross-listed** categories, so quant-ph papers cross-listed to cs.LG or stat.ML are included.
- Ordering: `sortBy=relevance`, pages of 500, at least 3.5 s between calls. On an HTTP error or an empty or short body the script backed off 30-60 s and retried.

**Semantic Scholar (bulk search)**

- Query syntax: `+` for AND, `|` for OR, double-quoted phrases, parentheses. The bulk endpoint matches title and abstract, and the query is the exact boolean expression. The string is URL-encoded with `%2B` for `+`. The requested fields are `title,year,venue,externalIds,abstract,publicationTypes`; `paperId` is always returned.
- Year limit: `year=2018-2026`. CS restriction (S3, S4): `fieldsOfStudy=Computer Science`. Semantic Scholar has no separate machine-learning field, since ML sits inside Computer Science, so S4 cannot add an explicit ML category.
- Ordering: the bulk endpoint does not rank by relevance. For S4, `sort=citationCount:desc` is set so that if the 3000-record cap applies, the most-cited records are kept rather than an arbitrary `paperId` slice. **This differs from the relevance ordering used for OpenAlex and arXiv.** Other searches use the default order.
- Unauthenticated calls share a public rate-limit pool and returned many HTTP 429 responses. The script kept at least 1.5 s between calls and backed off 30-300 s on 429. Every retry is listed under `problems` in the manifests.
- Semantic Scholar withholds abstracts for some publishers (the `abstract` field is null), so some records have no abstract and their prescreen flag is based on the title only.

**Retries and errors during the run:** 4 logged events (Semantic Scholar S1: 1, Semantic Scholar S2: 1, Semantic Scholar S3: 1, Semantic Scholar S4: 1). Details are in each manifest's `problems` list.

## Deduplication

- Every parsed record (source x search x rank) is a node, and nodes are joined with union-find in three passes:
  1. **DOI.** The DOI is lowercased, stripped of `https://doi.org/`, and stripped of a trailing version suffix `/vN`, which TechRxiv mints per version. arXiv DOIs (`10.48550/arXiv.*`) are handled as arXiv ids.
  2. **arXiv id.** The version suffix is removed. arXiv ids come from arXiv itself, from Semantic Scholar `externalIds.ArXiv`, and from OpenAlex `locations` landing or PDF URLs and arXiv DOIs.
  3. **Normalized title.** Titles are NFKD-normalized, accents and HTML tags are stripped, the text is lowercased, and every non-alphanumeric run becomes one space. Title merging applies only when the normalized title is at least 30 characters, and it is skipped when both years are known and differ by more than 2. This stops generic titles such as "Quantum machine learning" from merging unrelated works.
- Merges made: DOI 3186, arXiv id 2329, title 295; title merges skipped because of the year gap: 43.
- Rows with more than one arXiv id: 2. These usually come from a source's metadata linking two arXiv entries, for example a Semantic Scholar record whose arXiv externalId and arXiv DOI differ, which can merge two distinct preprints. They are worth a glance during screening. Rows with more than one DOI: 1407, typically a preprint plus its published version, or several Zenodo version DOIs of the same deposit.
- How a merged row is filled:
  - `title` comes from OpenAlex, else Semantic Scholar, else arXiv.
  - `year` is the earliest year across the merged records.
  - `venue` is the first non-arXiv venue, else `arXiv (<primary category>)` plus the journal reference.
  - `doi` lists every distinct non-arXiv DOI, separated by `; `.
  - `url` is the first DOI, else the arXiv abstract page.
  - `abstract` is the longest available abstract, truncated to 600 characters.
  - `sources` lists each source with the searches that found the record, for example `openalex:S2,S4; semanticscholar:S2; arxiv:S2`.
  - `uid` is `QRS-` plus the first 10 hex digits of the SHA-1 of the primary key: the smallest DOI key, else the arXiv id, else the title. It stays the same across re-runs as long as that key does not change.
- Rows are sorted by the earliest search that found them (S1 first), then by year (newest first), then by title.
- `candidates.csv` is UTF-8 with a byte-order mark, so Excel opens it correctly.

**Records parsed: 13122. Total unique records: 7312.**

## Pre-screen flag rules

Rules are applied in this order to `title + abstract` (the full abstract, before truncation); the first rule that fires sets the flag. Matching is case-insensitive regular expressions defined in `search.py` (`RX`).

"Co-occur" below means that the two terms appear in the same sentence, or that one of them is in the title and the other appears anywhere.

1. **post_quantum_crypto** fires when `RX["PQC"]` matches in the title, or matches at least twice in title + abstract. A single passing mention does not fire it. `RX["PQC"]` covers post-quantum, quantum-safe, quantum-resistant, quantum-resilient, quantum-secure, quantum-proof, lattice-based cryptography, signature or encryption schemes, Kyber, Dilithium, ML-KEM, ML-DSA, SPHINCS, CRYSTALS and NTRU. It also catches **quantum cryptography and QKD** (quantum key distribution, quantum secure direct communication), which are equally off-topic for this survey. The bare abbreviations "PQC" and "QKD" are deliberately not used, because they collide with "parameterized quantum circuit (PQC)" and "quantum kernel discriminator (QKD)".
2. **llm_for_quantum** fires when three conditions hold:
   - A language-anchor term (`RX["L"]`) co-occurs with an LLM-for-quantum term (`RX["LFQ"]`). `RX["L"]` covers LLM(s), (large) language model(s), NLP, natural language processing, text generation, language generation, ChatGPT and GPT-n.
   - `RX["LFQ"]` matches any of these:
     - the tool and language names Qiskit, OpenQASM, QASM, Cirq and PennyLane;
     - "quantum code", "quantum program(ming)", "quantum software", "quantum compiler";
     - "quantum circuit" followed by design, generation, synthesis, compilation, optimization or discovery;
     - generate, design, synthesize, write, compose, construct, discover or translate, then up to three words, then quantum circuits, programs, algorithms or code;
     - "LLM(s)", "language model(s)" or "agent(s)", then for, in or to, then a quantum field such as computing, software, programming, circuits, chemistry, physics, simulation or error correction;
     - quantum circuits, programs, code or algorithms, then using, with, via or by, then an LLM, language model or GPT.
   - The text does **not** match `RX["Q4L"]`, the quantum-methods-for-language markers. These are QNLP, quantum natural language, DisCoCat, DisCoCirc and lambeq; quantum-inspired, quantum-enhanced, quantum-assisted or hybrid quantum-classical followed by LLM, language model, transformer, NLP, text, sentence, fine-tuning or adapter; quantum transformer, attention, word embedding, language model, fine-tuning, adapter, LoRA, text classification or sentiment; and an LLM or language model "using", "with" or "via" a quantum method or tensor networks. Without this exemption, QNLP papers that "construct quantum circuits from sentences in Qiskit" would be mislabelled.
3. **quantum_ml_robustness**: **no** language-anchor term, **and** an attack term (`RX["ADV"]`: adversarial attacks, examples, perturbations, robustness, samples, inputs, noise, threats or defence, plus attack(s), attacker, poisoning, backdoor and evasion; a bare "adversarial" is not enough, so quantum GANs are not caught) **and** a quantum-model target (`RX["QML_TARGET"]`: quantum machine learning / classifier / neural network / model / kernel / SVM / convolutional / image classification / learning, QML, QNN, QCNN, VQC, variational quantum classifier|circuit|algorithm, parameterized quantum circuit).
4. **likely_relevant**: a quantum-*method* term (`RX["QM"]`: quantum-inspired, quantum-enhanced, hybrid quantum(-classical), variational/parameterized quantum, Born machine, tensor network, matrix product state/operator, tensor train, quantum annealing, QAOA, QUBO, HUBO, Ising machine, qubit, NISQ, QNLP, DisCoCat/DisCoCirc, lambeq, QML, QNN, VQC, VQE, or "quantum" followed by a computing word such as computing, circuit, algorithm, machine learning, neural, natural language, kernel, hardware, advantage, walk, Boltzmann, GAN, generative, diffusion, transformer, attention, embedding, optimization, sampling, reservoir, probability, cognition, -like, software, search, learning, language model, LLM, classifier, encoding, superposition, entanglement, interference, annealer, simulation) **co-occurring** with either a language-anchor term or an LLM-security term (`RX["SEC_LLM"]`: jailbreak, red team(ing), adversarial prompt, prompt injection). A bare "quantum" (e.g. "quantum dot", "quantum yield", "quantum chemistry") does not satisfy the quantum-method test. Records whose title looks like a call for papers or front matter (`RX["CFP"]`: "Nth International Conference/Workshop/Symposium ...", "call for papers", "Preface", "Front matter", "Editorial") are never flagged likely_relevant, because their topic lists mention every term.
5. **other**: everything else. Note that S4-only records (quantum generative / optimization models that do not mention language) will mostly be flagged `other` by construction; the flag says nothing about their value as candidate components and they still need screening on their own terms.

The flag is a sorting hint for the screeners, never an inclusion or exclusion decision.

| prescreen_flag | unique records | in S1 | in S2 | in S3 | in S4 |
|---|---|---|---|---|---|
| post_quantum_crypto | 248 | 10 | 108 | 131 | 21 |
| llm_for_quantum | 128 | 0 | 127 | 0 | 3 |
| quantum_ml_robustness | 104 | 0 | 0 | 94 | 15 |
| likely_relevant | 1000 | 6 | 993 | 8 | 41 |
| other | 5832 | 38 | 2047 | 349 | 3507 |
| **total** | **7312** | 54 | 3275 | 582 | 3587 |

## Known-item check

These items were named in advance to test recall. The check only reports presence. If an item is missing, the diagnostic shows which term groups its title and abstract match, using approximate stem-tolerant regexes of the query terms. Its metadata was fetched separately (`python -I search.py diagnose`, files `raw/diag_*`). The search queries were not changed to capture any of these items.

| Item | Id | In candidates.csv | uid | Found by | prescreen_flag | Diagnostic |
|---|---|---|---|---|---|---|
| QCR-LLM | 2510.24509 | yes | QRS-f32601e848 | arxiv:S2; semanticscholar:S2 | likely_relevant | Quantum combinatorial reasoning for large language models |
| QTHA | 2503.12790 | yes | QRS-987f14783b | arxiv:S2; semanticscholar:S2 | likely_relevant | Quantum-Enhanced LLM Efficient Fine Tuning |
| CompactifAI | 2401.14109 | yes | QRS-404bd4afa3 | openalex:S2; arxiv:S2; semanticscholar:S2 | likely_relevant | CompactifAI: Extreme Compression of Large Language Models using Quantum-Inspired Tensor Networks |
| combinatorial reasoning | 2407.00071 | yes | QRS-e3af596283 | openalex:S2,S4; arxiv:S2,S4; semanticscholar:S2,S4 | likely_relevant | Combinatorial Reasoning: Selecting Reasons in Generative AI Pipelines via Combinatorial Optimization |
| QUBO RAG | 2607.12334 | yes | QRS-a6034f5a03 | openalex:S2; arxiv:S2; semanticscholar:S2 | likely_relevant | QUBO-Optimized Evidence Selection for Retrieval-Augmented Question Answering with Unconventional Solvers |
| QAA | 2509.16244 | yes | QRS-6b486f531a | openalex:S2; arxiv:S2; semanticscholar:S2 | likely_relevant | How Can Quantum Deep Learning Improve Large Language Models? |
| TechRxiv survey | 10.36227/techrxiv.177004376.69666864/v1 | yes | QRS-5cd2b98ecd | openalex:S2 | likely_relevant | Quantum Computing Meets Large Language Models: Insights, Challenges, and Future Directions |

