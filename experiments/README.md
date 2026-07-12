# Experiments 2 & 3 — runnable bundle (self-hosted LLM)

Run these **on the GPU server** where Ollama is serving at `localhost:11434`
(no SSH tunnel needed). Requires only `python3` (standard library).

## 0. Start the model (once, in tmux)
```bash
export PATH=$HOME/ollama/bin:$PATH
ollama serve            # in one tmux window
ollama pull qwen3:32b   # or qwen3-coder:30b (no "thinking", faster)
```

## 1. Point the scripts at Ollama
```bash
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=qwen3:32b        # the model was pulled
export LLM_KEY=ollama             # any value; Ollama ignores it
```

## 2. Experiment 2 — LLM as decomposer
```bash
cd experiments
python3 run_exp2.py --app JPetStore --desc "Spring MVC e-commerce pet store" \
    --src data/jpetstore/src --graph data/jpetstore/callGraph.json \
    --out exp2_jpetstore.json
python3 eval_metrics.py --partition exp2_jpetstore.json
```
Prints ICP / ACS / BCP / CHI / NED + GS Jaccard for the LLM's decomposition.

## 3. Experiment 3 — reverse-engineer Service Cutter input
```bash
python3 run_exp3.py --app JPetStore --desc "Spring MVC e-commerce pet store" \
    --src data/jpetstore/src \
    --out exp3_jpetstore_user_representations.json
```
Then upload `exp3_...json` into Service Cutter, run the four algorithms, and compare
against the manual baseline (`../service-cutter/jpetstore_2_user_representations.json`).

## Notes
- The scripts strip Qwen3 `<think>...</think>` blocks automatically, so a "thinking"
  model still yields clean JSON. For speed, use `qwen3-coder:30b` instead.
- Prompts + generation params are documented in `prompts.md`.
- Copy the two output JSON files back to machine to write the results into the thesis.
