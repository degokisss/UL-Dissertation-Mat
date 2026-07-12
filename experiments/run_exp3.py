#!/usr/bin/env python3
"""Experiment 3 — reverse-engineer business rules / use cases as Service Cutter INPUT.
The LLM reads the monolith's source and produces the Service Cutter user-representation
JSON (useCases, sharedOwnerGroups, compatibilities). This is the tool's INPUT, not a
decomposition. Feed the output into Service Cutter and run the same 4 algorithms as
Experiment 1, comparing against the manually authored representation.

Usage:
  python run_exp3.py --app JPetStore \
      --desc "Spring MVC e-commerce pet store" \
      --src /path/to/jpetstore/src/main/java \
      --out exp3_jpetstore_user_representations.json

LLM endpoint via env: LLM_BASE_URL, LLM_MODEL, LLM_KEY (defaults match the deploy guide).
"""
import argparse, json, os, re, sys, urllib.request

SYSTEM = """You are a domain analyst. Reading a monolithic Java application's source \
code, you reconstruct the domain knowledge that a human domain expert would normally \
supply as input to the Service Cutter decomposition tool. You do NOT decompose the \
system into services yourself; you only produce the input model.

Output ONLY a single valid JSON object, no markdown fences, matching exactly the \
Service Cutter user-representation schema:
{
  "useCases": [{"name":"<UseCase>","nanoentitiesRead":["<Entity>.<field>", ...],"nanoentitiesWritten":["<Entity>.<field>", ...]}],
  "sharedOwnerGroups": [{"name":"<groupName>","nanoentities":["<Entity>.<field>", ...]}],
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
- Base everything on the actual source; do not invent entities or fields."""

def read_sources(src, pkgs):
    out = []
    for root, _, files in os.walk(src):
        if pkgs and not any(("/"+p.replace(".", "/")+"/") in (root+"/") for p in pkgs):
            continue
        for f in sorted(files):
            if f.endswith(".java"):
                p = os.path.join(root, f)
                out.append(f"// FILE: {os.path.relpath(p, src)}\n" + open(p, encoding="utf-8", errors="ignore").read())
    return "\n\n".join(out)

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
    ap.add_argument("--src", required=True)
    ap.add_argument("--package", default="", help="comma-separated package filter for large apps")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pkgs = [p.strip() for p in a.package.split(",") if p.strip()]
    source = read_sources(a.src, pkgs)
    user = (f"Application: {a.app} — {a.desc}\n\nSource files:\n" + source +
            "\n\nProduce the Service Cutter user-representation JSON.")
    print(f"[exp3] {a.app}: prompt ~{len(user)//4} tokens; calling LLM...", file=sys.stderr)
    result = extract_json(call_llm(SYSTEM, user))
    json.dump(result, open(a.out, "w"), indent=2)
    uc = result.get("useCases", []); sg = result.get("sharedOwnerGroups", [])
    print(f"[exp3] saved {a.out}: {len(uc)} use cases, {len(sg)} shared-owner groups")
    print("  Next: upload into Service Cutter, run 4 algorithms, compare vs manual baseline.")

if __name__ == "__main__":
    main()
