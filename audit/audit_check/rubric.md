# Evidence-audit rubric (QA1 to QA5)

Score each study from its full text, which is in `texts/<key>.txt`. Use exactly one of Y (met), P (partly met), N (not met) or NA (not applicable) per criterion.

| Criterion | Y | P | N | NA |
|---|---|---|---|---|
| **QA1 Reproducible detail** | The method (circuit or architecture), hyperparameters, training or solving procedure and data are described well enough to reimplement. | Partly. | No. | |
| **QA2 Execution reporting** | The paper states classical simulation vs. quantum hardware, AND reports the qubit count, AND reports circuit depth or layer count (and the number of shots where sampling or measurement statistics are used). | It states simulation vs. hardware but omits qubits or depth. | It is unclear whether a simulator or hardware was used. | Purely classical quantum-inspired methods and classical solvers. For a hardware random-number generator, score how well the device is described. |
| **QA3 Classical baseline of matched size** | A classical model or solver of comparable size, capacity or budget, on the same task and formulation (for example, the same parameter count, or simulated annealing on the same objective). | A classical baseline exists but is not matched in size or setup, or the quantum component is not isolated from the classical parts. | No classical baseline. | Theory-only papers. |
| **QA4 Standard data and metrics** | Public standard benchmarks and metrics for the task. | Small, synthetic or non-standard data that is public or reproducible. | Private or ad hoc data. | |
| **QA5 Code or data released** | The paper links a public repository. You may check that a link printed in the paper resolves, using `curl -I` on that link only. | Partial release, or "available on request". | Nothing released. | |

Give one short piece of evidence for every score: a quote of at most 15 words, or a paraphrase, with its location (section, table or figure).
