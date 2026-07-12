#!/usr/bin/env python3
"""Experiment 2 — LLM as decomposer.
Reads a monolith's Java source (+ optional call graph), asks the self-hosted LLM to
propose microservice boundaries, and saves the decomposition JSON.

Usage:
  python run_exp2.py --app JPetStore \
      --desc "Spring MVC e-commerce pet store" \
      --src /path/to/jpetstore/src/main/java \
      --graph /path/to/callGraph.json \
      --out exp2_jpetstore_decomposition.json

LLM endpoint via env (defaults match the deploy guide):
  LLM_BASE_URL=http://localhost:8000/v1  LLM_MODEL=qwen-coder-32b  LLM_KEY=ul-dissertation-local
"""
import argparse, json, os, re, sys, urllib.request

SYSTEM = """You are a senior software architect who decomposes monolithic Java applications \
into microservices. You are given a monolith's source code and its class-dependency \
graph. Propose candidate service boundaries that maximise cohesion and minimise \
coupling, grounded in the application's business capabilities and in the actual \
dependencies between classes. Reason about the domain first, then decide.

Output ONLY a single valid JSON object, with no markdown fences and no commentary, \
matching exactly this schema:
{"services":[{"name":"<PascalCaseServiceName>","classes":["<SimpleClassName>", ...],"rationale":"<one concise sentence>"}]}

Constraints:
- Every application class listed in the input must appear in exactly one service.
- Use simple class names (no package prefix), exactly as given in the input.
- Do not invent, rename, merge away, split, or omit any class.
- Choose the number of services that best fits the domain; do NOT pad to a target count."""

def read_sources(src, pkgs):
    out, classes = [], []
    for root, _, files in os.walk(src):
        if pkgs and not any(("/"+p.replace(".", "/")+"/") in (root+"/") for p in pkgs):
            continue
        for f in sorted(files):
            if f.endswith(".java"):
                p = os.path.join(root, f)
                out.append(f"// FILE: {os.path.relpath(p, src)}\n" + open(p, encoding="utf-8", errors="ignore").read())
                classes.append(f[:-5])
    return "\n\n".join(out), sorted(set(classes))

def fmt_graph(path):
    if not path or not os.path.exists(path): return "(not provided)"
    d = json.load(open(path)); S = lambda x: x.split(".")[-1]
    return "\n".join(f"  {S(e['source'])} -> {S(e['target'])} : {e.get('weight',1)}"
                     for e in sorted(d.get("edges", []), key=lambda e: -e.get("weight", 1)))

def call_llm(system, user):
    base = os.environ.get("LLM_BASE_URL", "http://localhost:8000/v1")
    body = json.dumps({
        "model": os.environ.get("LLM_MODEL", "qwen-coder-32b"),
        "temperature": float(os.environ.get("LLM_TEMPERATURE", "0.2")),
        "top_p": 0.95, "seed": int(os.environ.get("LLM_SEED", "42")), "max_tokens": 4096,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + os.environ.get("LLM_KEY", "ul-dissertation-local")})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]["content"]

def extract_json(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)          # strip Qwen3-style reasoning
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    i, j = text.find("{"), text.rfind("}")
    return json.loads(text[i:j+1])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True); ap.add_argument("--desc", default="")
    ap.add_argument("--src", required=True); ap.add_argument("--graph", default="")
    ap.add_argument("--package", default="", help="comma-separated package filter, e.g. domain,application,interfaces")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pkgs = [p.strip() for p in a.package.split(",") if p.strip()]
    source, classes = read_sources(a.src, pkgs)
    user = (f"Application: {a.app} — {a.desc}\n\n"
            f"Classes to partition ({len(classes)}):\n" + ", ".join(classes) + "\n\n"
            f"Class dependency graph (caller -> callee : weight = number of static references):\n"
            + fmt_graph(a.graph) + "\n\nSource files:\n" + source +
            "\n\nPropose the microservice decomposition as specified.")
    print(f"[exp2] {a.app}: {len(classes)} classes, prompt ~{len(user)//4} tokens; calling LLM...", file=sys.stderr)
    raw = call_llm(SYSTEM, user)
    result = extract_json(raw)
    json.dump(result, open(a.out, "w"), indent=2)
    print(f"[exp2] saved {a.out}")
    for s in result.get("services", []):
        print(f"  {s['name']} ({len(s['classes'])}): {', '.join(s['classes'])}")

if __name__ == "__main__":
    main()
