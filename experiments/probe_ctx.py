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

base = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
body = {
    "model": os.environ.get("LLM_MODEL", "qwen3:32b"),
    "temperature": 0.0, "max_tokens": 500,
    "messages": [{"role": "user", "content": user}],
}
if os.environ.get("LLM_NUM_CTX"):
    body["options"] = {"num_ctx": int(os.environ["LLM_NUM_CTX"])}
req = urllib.request.Request(base.rstrip("/") + "/chat/completions",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json",
             "Authorization": "Bearer " + os.environ.get("LLM_KEY", "ul-dissertation-local")})
with urllib.request.urlopen(req, timeout=300) as r:
    resp = json.load(r)
print(resp["choices"][0]["message"]["content"])
print("---")
print("real answer: 101 classes; real first 3:", classes[:3], "; real last 3:", classes[-3:])
