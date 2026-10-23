# Screening rule: core search of a review on quantum methods for LLM red teaming

**Screening question.** Does the record propose or evaluate a quantum or quantum-inspired method for generating, detecting, or defending against adversarial inputs to language models (LLMs or other NLP systems)?

A record is a **primary study for inclusion** only if all three conditions hold:

- **Q (quantum):** A quantum or quantum-inspired method is a working component of what the study builds or evaluates. Examples:
  - quantum circuits, whether simulated or run on hardware;
  - quantum annealing, QAOA, or a QUBO/Ising formulation solved by quantum or quantum-inspired means;
  - quantum-inspired algorithms such as quantum-behaved particle swarm or quantum-inspired evolutionary algorithms;
  - quantum-probability or density-matrix models, and tensor networks presented as quantum-inspired.

  Using the word "quantum" as a metaphor, or naming quantum computing only as a future threat, does not count.
- **S (adversarial):** The study concerns adversarial inputs. That covers generating attacks, jailbreaks, or adversarial examples; detecting or defending against them; or red-teaming or safety evaluation that uses such inputs.
- **L (language):** The attacked, defended, or evaluated system processes natural-language text: LLMs, text classifiers, or other NLP models.

## Decision codes (use exactly one per record)

| Code | Meaning |
|---|---|
| `INCLUDE` | A primary study meeting Q, S and L. |
| `RELATED_REVIEW` | A review, survey or systematic literature review whose topic spans quantum computing, language models and security. It is not a primary study. |
| `DUPLICATE` | The same work as another record in this packet. Give that record's id in the rationale. |
| `EXCLUDE-E1` | Concerns post-quantum or quantum cryptography (PQC, QKD, quantum-resistant algorithms, or cryptographic protocols as the object of study) rather than a quantum method used to attack, defend or evaluate language models. |
| `EXCLUDE-E2` | A scholarly work that fails Q, S, or L. |
| `EXCLUDE-E3` | Not a scholarly study: a call for papers, slides, a software or dataset release, or a self-published manuscript without a method and an evaluation. |

**Precedence:**
1. If E3 applies, choose E3.
2. Otherwise, if both E1 and E2 apply, choose E1.
3. A review that would otherwise be E1 or E2 but whose topic spans quantum computing, language models and security is `RELATED_REVIEW`.

**What to base each decision on:** only the title, year, venue and abstract given in the packet. Four records have no abstract; decide those from the title and venue, and say so in the rationale.
