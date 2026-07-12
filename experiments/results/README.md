# Experiment 2 — LLM-as-decomposer, scored partitions

Self-hosted LLM (Ollama, 2x NVIDIA A100 80GB). Target monolith: MyBatis JPetStore 6.1.0
(24 classes). Each file is the partition that was scored with `eval_metrics.py`
against `../data/jpetstore/callGraph.json` (coupling metrics) and the Sellami et al.
class-level gold standard (BCP, GS Jaccard). Reproduce any row with:

```
python ../eval_metrics.py --partition <file> \
    --graph ../data/jpetstore/callGraph.json --src ../data/jpetstore/src
```

| File | Model | Prompt | Invented classes | k | ICP | BCP | CHI | NED | GS Jaccard |
|------|-------|--------|------------------|---|-----|-----|-----|-----|------------|
| `exp2_qwen3_freeform.json`       | qwen3:32b        | free-form            | 8  | 7 | 0.759 | 0.876 | 0.241 | 0.497 | 0.542 |
| `exp2_qwen25coder_freeform.json` | qwen2.5-coder:32b| free-form            | 31 | 5 | 0.690 | 0.892 | 0.310 | 0.418 | 0.446 |
| `exp2_qwen25coder_strict.json`   | qwen2.5-coder:32b| strict (enum+repair) | 0  | 5 | 0.569 | 0.708 | 0.431 | 0.555 | 0.699 |

**Finding.** Under free-form prompting both models reconstruct a template architecture
from their training prior rather than analysing the actual code: qwen3 invents a
DAO/JDBC layer (`AccountDao`, `JdbcConnection`, ...) and non-existent `InventoryService`
/`PaymentService`; qwen2.5-coder invents a full Spring Controller/Service/Repository/
Validator stack for `User`/`Cart`/`Catalog`. Constraining generation to the real class
set (JSON-schema enum) plus a validate-and-repair loop (2 rounds here) yields a faithful
partition (0 invented, all 24 classes placed once) that also tracks the gold standard
more closely than either free-form run (GS 0.699 vs 0.542 / 0.446).

Generation params (fixed for reproducibility): temperature=0.2, top_p=0.95, seed=42,
max_tokens=8192. The strict run used `run_exp2.py` defaults; the free-form runs used
`--free`.
