# Role assignment for eligible studies (review of quantum methods for LLM red teaming)

Every record in your batch is a primary study that uses a quantum or quantum-inspired method and was judged
eligible for the review. For each record, record four things from its title and abstract.

## 1. role: the one role the study's method would most naturally take in a red-teaming pipeline

| Code | Role | Typical studies |
|---|---|---|
| `R1` | Distribution sampler: a generative model or sampler that learns or draws from a distribution | Born machines, quantum GANs, quantum Boltzmann machines, annealer-based generative models, quantum diffusion models, quantum autoencoders used generatively, quantum-enhanced Monte Carlo sampling, tensor-network generative models; for classical or quantum data |
| `R2` | Sequence generator: a model that produces text, or a component of a language model that does | quantum or hybrid language models, transformers and recurrent networks for text; quantum or quantum-inspired fine-tuning, adapters, or compression of language models; machine translation and text generation |
| `R3` | Combinatorial composer: discrete (combinatorial) optimization or selection through an explicit objective | quantum annealing, QAOA and other variational optimizers for combinatorial problems, QUBO, HUBO or Ising formulations and their solvers (including digital annealers and Ising machines); QUBO selection of prompt, reasoning or retrieval items |
| `R4` | Search operator: a search or metaheuristic operator | quantum-inspired evolutionary algorithms, quantum-behaved particle swarm and other quantum-inspired metaheuristics, Grover search and amplitude amplification |
| `R5` | Scorer or surrogate judge: a model that scores, classifies, embeds, ranks or detects text | compositional quantum NLP classifiers, hybrid circuit text classifiers, quantum kernels for text, quantum-inspired (density-matrix, complex-valued) language models for classification, matching or retrieval, sentiment analysis, detection |
| `R6` | Entropy source: a source of randomness for sampling | quantum random number generators used in model sampling |

Choose exactly one. If two fit, choose the one that matches the study's main contribution.

## 2. family: the method family, chosen from this list
`born_machine`, `quantum_gan`, `quantum_boltzmann_or_annealer_generative`, `quantum_diffusion`, `quantum_autoencoder`,
`tensor_network_generative`, `quantum_sampling_mcmc`, `quantum_language_model_or_transformer`, `quantum_recurrent`,
`quantum_finetuning_or_adapter`, `tensor_network_compression`, `quantum_annealing`, `qaoa_or_variational_optimization`,
`qubo_ising_formulation_or_solver`, `quantum_inspired_evolutionary`, `quantum_inspired_swarm`, `grover_or_amplitude_amplification`,
`compositional_qnlp`, `hybrid_circuit_text_classifier`, `quantum_kernel`, `quantum_inspired_language_model`, `qrng`, `other`.

## 3. hardware
`yes` if the abstract or title reports results obtained on a quantum device: a quantum processor, a quantum annealer,
a physical Ising machine, or a hardware quantum random number generator. `no` if results are from classical
simulation or classical computation only, or if the record does not say.

## 4. llm
`yes` if the method is applied to, built into, or evaluated with a large pretrained language model (an LLM such as
a GPT, LLaMA, or BERT-scale model or larger). `no` otherwise, including small language models trained from scratch.

## Output
One CSV row per record, in the order of the batch, with the header `id,role,family,hardware,llm`.
Base every value only on the title, year, venue and abstract in the batch. Do not search the web and do not use other files.
