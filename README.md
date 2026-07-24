# UL Dissertation Materials

Supplementary data files referenced in the MSc dissertation
**"An LLM-Assisted Comparative Evaluation Framework for Microservices Decomposition Methods"**
(Le Nguyen Thanh Tan, 25045229, University of Limerick).

These are the concrete input/output artefacts named in the text, provided for reproducibility.

## Contents

### `service-cutter/` — Service Cutter user representations (Experiment 1 input)
- `jpetstore_2_user_representations.json` — the JPetStore coupling-criteria model (entities, nanoentities, use cases, shared-owner groups) uploaded via the Service Cutter Editor.
- `ddd_2_user_representations.json` — the Cargo Tracker coupling-criteria model.

### `interface-analysis/` — Interface Analysis / Decomposer input, output, and reference model
- `schemaOrgTree.jsonld` — the Schema.org shared vocabulary (JSON-LD) used as the reference model by the Baresi et al. Decomposer.
- `input/jpetstore.json`, `input/cargotracker.json` — the operations submitted to the tool for each benchmark.
- `results/` — the tool's per-operation concept matches and aggregated concept buckets for both benchmarks. See `interface-analysis/README.md` for details.

### `mono2micro/` — Mono2Micro JPetStore partition output
- `vertical_cluster_assignment_fixedk4.json` — the Fixed-k (k=4) class-to-partition assignment.
- `vertical_cluster_assignment_autok5.json` — the Auto-k (k=5) class-to-partition assignment.
- `Oriole-Report_autok5.html` — the tool's business-use-case partition report (Auto-k=5 run), underlying the dissertation's Oriole figure and business-use-case coverage table.
- `Cardinal-Report_autok5.html` — the tool's deep partition analysis report (Auto-k=5 run), underlying the dissertation's Cardinal figure and cross-partition call detail table.
