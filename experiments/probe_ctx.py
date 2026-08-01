#!/usr/bin/env python3
import os, sys, json, urllib.request
import run_exp2 as R

src = "data/cargotracker/src"
graph = "data/cargotracker/callGraph.json"
pkgs = ["org.eclipse.cargotracker", "org.eclipse.pathfinder"]
source, classes = R.read_sources(src, pkgs, compact=True)
user = (f"Application: CargoTracker — Java EE cargo booking, routing, and tracking system\n\n"
        f"Classes to partition ({len(classes)}):\n" + ", ".join(classes) + "\n\n"
        f"Class dependency graph (caller -> callee : weight = number of static references):\n"
        + R.fmt_graph(graph) + "\n\nSource files:\n" + source +
        "\n\nDEBUG CHECK ONLY: do not decompose anything. Just answer: "
        "(1) how many classes were listed under 'Classes to partition' above? "
        "(2) name the first 3 and last 3 of them, verbatim. "
        "(3) name the very first class name that appears in the 'Source files' section below that heading.")

print(f"probe prompt: {len(user)} chars (~{len(user)//4} tokens)", file=sys.stderr)

model = os.environ.get("LLM_MODEL", "qwen3:32b")
num_ctx = int(os.environ.get("LLM_NUM_CTX", "40960"))

# --- test A: OpenAI-compatible endpoint (what run_exp2.py currently uses) ---
base = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
bodyA = {"model": model, "temperature": 0.0, "max_tokens": 500,
         "messages": [{"role": "user", "content": user}],
         "options": {"num_ctx": num_ctx}}
reqA = urllib.request.Request(base.rstrip("/") + "/chat/completions",
    data=json.dumps(bodyA).encode(),
    headers={"Content-Type": "application/json",
             "Authorization": "Bearer " + os.environ.get("LLM_KEY", "ul-dissertation-local")})
with urllib.request.urlopen(reqA, timeout=300) as r:
    respA = json.load(r)
print("=== A: OpenAI-compat endpoint (/v1/chat/completions) ===")
print(respA["choices"][0]["message"]["content"])

# --- test B: Ollama's native endpoint ---
reqB = urllib.request.Request("http://localhost:11434/api/chat",
    data=json.dumps({"model": model, "stream": False, "options": {"num_ctx": num_ctx, "temperature": 0.0},
                      "messages": [{"role": "user", "content": user}]}).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(reqB, timeout=300) as r:
    respB = json.load(r)
print("\n=== B: Ollama native endpoint (/api/chat) ===")
print(respB["message"]["content"])

print("\n---")
print("real answer: 101 classes; real first 3:", classes[:3], "; real last 3:", classes[-3:])
