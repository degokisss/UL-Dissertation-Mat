# UL Dissertation Materials

Supplementary data files referenced in the MSc dissertation
**"An LLM-Assisted Comparative Evaluation Framework for Microservices Decomposition Methods"**
(Le Nguyen Thanh Tan, 25045229, University of Limerick).

These are the concrete input/output artefacts named in the text, provided for reproducibility.

## Contents

### `service-cutter/` — Service Cutter user representations (Experiment 1 input)
- `jpetstore_2_user_representations.json` — the JPetStore coupling-criteria model (entities, nanoentities, use cases, shared-owner groups) uploaded via the Service Cutter Editor.
- `ddd_2_user_representations.json` — the Cargo Tracker coupling-criteria model.

### `interface-analysis/` — Interface Analysis / Decomposer reference model
- `schemaOrgTree.jsonld` — the Schema.org shared vocabulary (JSON-LD) used as the reference model by the Baresi et al. Decomposer.

### `mono2micro/` — Mono2Micro JPetStore partition output
- `vertical_cluster_assignment_fixedk4.json` — the Fixed-k (k=4) class-to-partition assignment.
- `vertical_cluster_assignment_autok5.json` — the Auto-k (k=5) class-to-partition assignment.
