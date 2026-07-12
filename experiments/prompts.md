# Prompts for Experiments 2 & 3 (self-hosted LLM)

Both experiments call the vLLM OpenAI-compatible endpoint from Phase 4 of the deploy guide.
Generation params (fix these for reproducibility): `temperature=0.2, top_p=0.95, seed=42, max_tokens=4096`.
Runnable drivers: `run_exp2.py` (decomposer) and `run_exp3.py` (Service-Cutter-input reconstructor).

---

## Experiment 2 — LLM as decomposer

**System prompt**
```
You are a senior software architect who decomposes monolithic Java applications
into microservices. You are given a monolith's source code and its class-dependency
graph. Propose candidate service boundaries that maximise cohesion and minimise
coupling, grounded in the application's business capabilities and in the actual
dependencies between classes. Reason about the domain first, then decide.

Output ONLY a single valid JSON object, with no markdown fences and no commentary,
matching exactly this schema:
{"services":[{"name":"<PascalCaseServiceName>","classes":["<SimpleClassName>", ...],
  "rationale":"<one concise sentence>"}]}

Constraints:
- Every application class listed in the input must appear in exactly one service.
- Use simple class names (no package prefix), exactly as given in the input.
- Do not invent, rename, merge away, split, or omit any class.
- Choose the number of services that best fits the domain; do NOT pad to a target count.
```

**User prompt** (filled by `run_exp2.py`)
```
Application: {APP_NAME} — {APP_DESC}

Classes to partition ({N}):
{CLASS_LIST}

Class dependency graph (caller -> callee : weight = number of static references):
{DEPS}

Source files:
{SOURCE}

Propose the microservice decomposition as specified.
```

Output → `exp2_<app>_decomposition.json`, then scored with `eval_metrics.py` (ICP, ACS, BCP, CHI, NED, GS Jaccard) exactly as in Experiment 1.

---

## Experiment 3 — Reverse-engineer business rules / use cases as Service Cutter INPUT
*(JJ's version: the LLM produces the tool's INPUT, not a decomposition.)*

**System prompt**
```
You are a domain analyst. Reading a monolithic Java application's source code, you
reconstruct the domain knowledge that a human domain expert would normally supply
as input to the Service Cutter decomposition tool. You do NOT decompose the system
into services yourself; you only produce the input model.

Output ONLY a single valid JSON object, no markdown fences, matching exactly the
Service Cutter user-representation schema:
{
  "useCases": [
    {"name":"<UseCase>",
     "nanoentitiesRead":["<Entity>.<field>", ...],
     "nanoentitiesWritten":["<Entity>.<field>", ...]}
  ],
  "sharedOwnerGroups": [
    {"name":"<groupName>","nanoentities":["<Entity>.<field>", ...]}
  ],
  "compatibilities": {
    "contentVolatility":      [{"characteristic":"Often|Regularly|Rarely","nanoentities":[...]}],
    "structuralVolatility":   [{"characteristic":"Often|Regularly|Rarely","nanoentities":[...]}],
    "availabilityCriticality":[{"characteristic":"Critical|Normal","nanoentities":[...]}],
    "consistencyCriticality": [{"characteristic":"High|Eventually","nanoentities":[...]}],
    "storageSimilarity":      [{"characteristic":"Tiny|Normal|Huge","nanoentities":[...]}],
    "securityCriticality":    [{"characteristic":"Critical|Internal|Public","nanoentities":[...]}]
  }
}

Rules:
- Nanoentities are "<Entity>.<field>" using the domain entities and fields found in the source.
- Use cases are the business operations the app supports; list the nanoentities each reads/writes.
- sharedOwnerGroups group nanoentities owned/managed together (e.g. all Account fields).
- Fill each compatibility criterion where the code/domain implies it; leave its list empty if unclear.
- Base everything on the actual source; do not invent entities or fields.
```

**User prompt** (filled by `run_exp3.py`)
```
Application: {APP_NAME} — {APP_DESC}

Source files:
{SOURCE}

Produce the Service Cutter user-representation JSON.
```

Output → `exp3_<app>_user_representations.json`. **Then**: upload it into Service Cutter
(same "Upload User Representations" step as Experiment 1) and run all four algorithms
(Girvan-Newman, Leung, Chinese Whispers, Markov). Compare the resulting decomposition
against the Experiment 1 baseline built from the *manually* authored
`jpetstore_2_user_representations.json`, using the same five metrics + GS Jaccard. The
only variable that changes is who produced the input model (LLM vs human), so the delta
isolates the domain-modelling step.

---

## Notes
- Keep the exact system/user prompts above verbatim in the repo — they are part of the method.
- If a source set is too large for the context window (e.g. Cargo Tracker, 104 classes),
  restrict `--package` to `domain,application,interfaces` and drop `infrastructure`.
- Record model id + revision, vLLM version, and these params in the thesis for reproducibility.
