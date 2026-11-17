# Screening rule: sampling frame of a review on quantum methods for LLM red teaming (route 2)

You screen records (title, year, venue, abstract) from a literature search. Each record gets exactly one code.
The question is whether a record is ELIGIBLE as a primary study under inclusion criterion IC1 or IC2 and
no exclusion criterion (EC1 to EC4). Eligibility is not selection: most eligible studies will not be used.

## Q: a quantum or quantum-inspired method is a working component
Required for IC1 and IC2. A quantum or quantum-inspired method is part of what the study builds or evaluates:
- quantum circuits, simulated or on hardware (variational or parameterized circuits, quantum neural networks, quantum kernels);
- quantum annealing, QAOA, or a QUBO, HUBO or Ising formulation solved by quantum or quantum-inspired means;
- quantum-inspired algorithms (quantum-behaved particle swarm, quantum-inspired evolutionary algorithms, digital annealers, Ising machines);
- quantum-probability or density-matrix models, and tensor networks presented as quantum-inspired.

Not Q: "quantum" as a metaphor or product name; quantum dots, quantum wells, quantum yield, quantum chemistry or
quantum physics as the subject studied with classical methods; quantum computing named only as a future threat or outlook.

## Codes (exactly one per record)

| Code | Meaning |
|---|---|
| `IC1` | ELIGIBLE. Q holds, and the method is applied to natural-language text or to a language model: it generates or scores text; or it works at a stage of a language-model pipeline (model architecture, fine-tuning, compression, decoding and sampling, scoring, or selection of prompt components, reasoning steps, or retrieved evidence); or it optimizes a discrete structure that maps to text. Examples: quantum natural language processing, quantum or hybrid language models and transformers for text, quantum or quantum-inspired text classifiers and embeddings, quantum-inspired tensor-network compression or fine-tuning of LLMs, QUBO selection of prompt or retrieval items. |
| `IC2` | ELIGIBLE. Q holds, IC1 does not, and the main contribution is a quantum or quantum-inspired GENERATIVE MODEL OR SAMPLER (Born machines, quantum GANs, quantum Boltzmann machines, quantum diffusion models, quantum-enhanced Monte Carlo sampling, quantum-inspired tensor-network generative models; for classical or quantum data) or a quantum or quantum-inspired method for DISCRETE OPTIMIZATION OR SEARCH (quantum annealing, QAOA, QUBO, HUBO or Ising solvers, quantum-inspired evolutionary or swarm algorithms). The model or method must be general: proposed, analyzed, or benchmarked as a model or algorithm in its own right, or on generic benchmark problems or data. The abstract must describe the method and an evaluation or analysis of it. |
| `EC1` | Language models or LLMs used FOR quantum computing: to write quantum programs, design or compile circuits, or assist quantum research. (A quantum method used inside or for a language model is IC1, not EC1.) |
| `EC2` | Adversarial robustness of quantum machine learning models (attacks on, or defenses of, quantum classifiers), with no bearing on generation. |
| `EC3` | Post-quantum or quantum cryptography: quantum-resistant algorithms, quantum key distribution, cryptographic protocols as the object of study. (A quantum random number generator used in model sampling is not cryptography.) |
| `EC4` | No technical content: no method and no evaluation. Calls for papers, front matter, prefaces, editorials, slides, software or dataset releases, tables of contents, opinion or news pieces. |
| `REVIEW` | A survey, review, tutorial, or other secondary study, on any topic. Not a primary study. |
| `NO` | Everything else: a primary study that meets neither IC1 nor IC2. This includes: no quantum or quantum-inspired method (Q fails); quantum methods for other tasks, such as classifiers or regressors for images, signals, or tabular data, quantum reinforcement learning, quantum chemistry and simulation, error correction, hardware, communication, sensing; a quantum generative or optimization method that is only applied to one application domain outside language (for example a QUBO for a logistics, finance, energy, or drug-design problem) without contributing a general model or algorithm; speech, audio, images, biological sequences, or time series treated as "language". |

## Precedence
1. `EC4` if the record has no technical content.
2. Otherwise `REVIEW` if it is a secondary study.
3. Otherwise `EC3`, then `EC1`, then `EC2`, if one applies.
4. Otherwise `IC1` if it applies; otherwise `IC2` if it applies.
5. Otherwise `NO`.

## What to base each decision on
Only the title, year, venue, and abstract in the batch. Do not search the web and do not use other files.
Some records have no abstract: decide from the title and venue, and set confidence to `low`.

## Output
One CSV row per record, in the order of the batch, with the header `id,code,confidence,reason`:
- `id`: the record id, such as `P01234`;
- `code`: one of `IC1`, `IC2`, `EC1`, `EC2`, `EC3`, `EC4`, `REVIEW`, `NO`;
- `confidence`: `high` or `low`;
- `reason`: at most 12 words, specific to the record (no commas inside, or quote the field).
