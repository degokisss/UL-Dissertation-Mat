# Interface Analysis / Decomposer — input and output artefacts

Baresi et al.'s Decomposer prototype (DISCO 2.1 + Schema.org vocabulary), built and
executed under Java 8 (Lucene 5.x inside DISCO does not run under Java 9+). See the
dissertation's tool-selection section for methodology and the Experiment 1 results
sections for discussion.

## `input/` — operations submitted to the tool
- `jpetstore.json` — the 15 JPetStore operations (Stripes ActionBean methods) plus
  resource/parameter names.
- `cargotracker.json` — the 10 Cargo Tracker operations exposed by
  `BookingServiceFacade` (the application's single façade for booking, routing, and
  tracking) plus resource/parameter names.

## `results/` — per-operation matches and aggregated concept buckets
Each `*_matches.txt` lists, per operation, the closest Schema.org concept and the
DISCO similarity score (lower = more similar). Each `*_result.txt` aggregates the
matches that clear the author-recommended 1.5 threshold into their parent
Schema.org concept.

| File | Operations | Cleared threshold (≤1.5) | Aggregated buckets |
|---|---|---|---|
| `jpetstore_matches.txt` / `jpetstore_result.txt` | 15 | 14 (93%) | Action:7, Intangible:3, Product:2, FinancialProduct:2 |
| `cargotracker_matches.txt` / `cargotracker_result.txt` | 10 | 3 (30%) | StructuredValue:1, Product:1, Place:1 |

**Finding.** JPetStore's e-commerce operations map cleanly onto Schema.org's own
e-commerce-oriented vocabulary. Cargo Tracker's shipping/logistics operations mostly
find no confident match at all; the three that do
(`changeDestination`→`TouristAttraction`, `listShippingLocations`→`LocationFeatureSpecification`,
`listAllCargos`→`Vehicle`) match on incidental lexical overlap (destination, location,
cargo) rather than functional similarity. Decomposer's output is at the operation
level, not the class level, so none of these runs produce a class partition scoreable
against the ICP/ACS/BCP/CHI/NED/GS-Jaccard suite used for the other tools.

Reproduce with (Java 8 required):
```
java -jar decomposer-1.0-SNAPSHOT-jar-with-dependencies.jar schemaOrgTree.jsonld <disco-word-space-path> 1.5
```
with only the relevant file present in the tool's `./input/` directory (the tool
processes every file found there in one run). The word space used is
`enwiki-20130403-sim-lemma-mwl-lc` (DISCOLuceneIndex format, API 2.x/3.x), available
from linguatools.de.
