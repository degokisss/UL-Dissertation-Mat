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

SIG_TAIL_RE = re.compile(r'\)\s*(?:throws\s+[\w.<>\[\],\s]*[\w])?\s*\{\Z')
TYPE_HEAD_RE = re.compile(r'\b(?:class|interface|enum|@interface)\b')
IMPORT_RE = re.compile(r'(?m)^\s*import\s+[\w.*]+\s*;\s*\n')
MAX_HEAD_LEN = 600   # a real method/ctor signature is never longer than this

def compact_source(text, shorten_strings=25):
    """Shrink one Java file for prompt-size budget: drop imports and
    comments, replace method/constructor body CONTENTS with a placeholder,
    truncate long string literals. Keeps package/class/field/method
    signatures and annotations intact (the structural information a
    decomposition task needs). Comment- and string-literal-aware so stray
    braces inside them don't corrupt the brace-depth count."""
    text = IMPORT_RE.sub('', text)
    out = []
    i, n = 0, len(text)
    buf_start = 0
    depth = 0
    strip_body_at = None
    while i < n:
        ch = text[i]
        if ch == '/' and i + 1 < n and text[i + 1] == '/':
            j = text.find('\n', i)
            end = n if j == -1 else j + 1
            if buf_start is not None:
                out.append(text[buf_start:i]); buf_start = end
            i = end; continue
        if ch == '/' and i + 1 < n and text[i + 1] == '*':
            j = text.find('*/', i + 2)
            end = n if j == -1 else j + 2
            if buf_start is not None:
                out.append(text[buf_start:i]); buf_start = end
            i = end; continue
        if ch == '"':
            j = i + 1
            while j < n and text[j] != '"':
                if text[j] == '\\': j += 1
                j += 1
            end = min(j + 1, n)
            if shorten_strings and buf_start is not None and (end - i) > shorten_strings + 2:
                out.append(text[buf_start:i])
                out.append('"' + text[i + 1:i + 1 + shorten_strings] + '..."')
                buf_start = end
            i = end; continue
        if ch == "'":
            j = i + 1
            while j < n and text[j] != "'":
                if text[j] == '\\': j += 1
                j += 1
            i = min(j + 1, n); continue
        if ch == '{':
            if strip_body_at is None:
                back = max(text.rfind(c, max(0, i - MAX_HEAD_LEN), i) for c in (';', '{', '}'))
                head = text[max(back + 1, i - MAX_HEAD_LEN):i + 1].strip()
                if SIG_TAIL_RE.search(head) and not TYPE_HEAD_RE.search(head):
                    out.append(text[buf_start:i + 1])
                    strip_body_at = depth + 1
                    buf_start = None
            depth += 1
        elif ch == '}':
            depth -= 1
            if strip_body_at is not None and depth == strip_body_at - 1:
                out.append(" /* body omitted for prompt size */ }")
                strip_body_at = None
                buf_start = i + 1
        i += 1
    if buf_start is not None:
        out.append(text[buf_start:])
    return "".join(out)

SYSTEM = """You are a senior software architect who decomposes ONE SPECIFIC EXISTING \
monolithic Java application into microservices. You are given that application's actual \
class list, class-dependency graph, and source code. Base the decomposition strictly on \
THESE classes and their real dependencies. This is a concrete codebase, NOT a generic \
e-commerce reference design: do not invent services, entities, databases, or classes that \
are not in the provided class list, and do not reproduce a textbook microservices diagram.

Output ONLY a single valid JSON object, no markdown, matching exactly this schema:
{"services":[{"name":"<PascalCaseServiceName>","classes":["<SimpleClassName>", ...],"rationale":"<one concise sentence>"}]}

Hard constraints:
- The "classes" array of every service must contain ONLY names copied verbatim from the
  provided class list. No invented entities (no User, Payment, Notification, Warehouse, etc.).
- Every class in the provided list must appear in exactly one service; do not omit, rename,
  split, or add classes.
- Group by cohesion and by the actual dependencies shown; choose the number of services that
  best fits the code, do NOT pad to a target count."""

def read_sources(src, pkgs, compact=False):
    out, classes = [], []
    for root, _, files in os.walk(src):
        if pkgs and not any(("/"+p.replace(".", "/")+"/") in (root+"/") for p in pkgs):
            continue
        for f in sorted(files):
            if f.endswith(".java"):
                p = os.path.join(root, f)
                text = open(p, encoding="utf-8", errors="ignore").read()
                if compact:
                    text = re.sub(r'\n{3,}', '\n\n', compact_source(text))
                    out.append(f"// {f}\n" + text)
                else:
                    out.append(f"// FILE: {os.path.relpath(p, src)}\n" + text)
                classes.append(f[:-5])
    return "\n\n".join(out), sorted(set(classes))

def fmt_graph(path):
    if not path or not os.path.exists(path): return "(not provided)"
    d = json.load(open(path)); S = lambda x: x.split(".")[-1]
    return "\n".join(f"  {S(e['source'])} -> {S(e['target'])} : {e.get('weight',1)}"
                     for e in sorted(d.get("edges", []), key=lambda e: -e.get("weight", 1)))

def decomposition_schema(classes):
    """JSON schema whose class items are an enum of the real class names, so the
    decoder structurally cannot emit an invented class (grammar-constrained)."""
    return {"type": "json_schema", "json_schema": {"name": "decomposition", "strict": True,
        "schema": {"type": "object", "additionalProperties": False,
            "properties": {"services": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "classes": {"type": "array", "items": {"type": "string", "enum": classes}},
                    "rationale": {"type": "string"}},
                "required": ["name", "classes", "rationale"]}}},
            "required": ["services"]}}}

def call_llm(messages, response_format):
    base = os.environ.get("LLM_BASE_URL", "http://localhost:8000/v1")
    model = os.environ.get("LLM_MODEL", "qwen-coder-32b")
    temperature = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
    seed = int(os.environ.get("LLM_SEED", "42"))
    max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "8192"))
    num_ctx = os.environ.get("LLM_NUM_CTX")

    if num_ctx:
        # Verified empirically (probe_ctx.py): Ollama's OpenAI-compatible
        # endpoint (/v1/chat/completions) silently ignores options.num_ctx
        # and keeps its small default context, truncating large prompts
        # without erroring. Only Ollama's own native endpoint (/api/chat)
        # actually honours it. Use the native endpoint whenever a context
        # override is requested; the default (no LLM_NUM_CTX) path below is
        # unchanged from Experiment 2's original OpenAI-compatible calls.
        fmt = "json"
        if response_format.get("type") == "json_schema":
            fmt = response_format["json_schema"]["schema"]
        native_base = re.sub(r"/v1/?$", "", base.rstrip("/"))
        body = json.dumps({
            "model": model, "stream": False, "format": fmt,
            "messages": messages,
            "options": {"num_ctx": int(num_ctx), "temperature": temperature,
                        "seed": seed, "num_predict": max_tokens},
        }).encode()
        req = urllib.request.Request(native_base + "/api/chat", data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.load(r)["message"]["content"]

    body = json.dumps({
        "model": model, "temperature": temperature,
        "top_p": 0.95, "seed": seed, "max_tokens": max_tokens,
        "response_format": response_format,
        "messages": messages,
    }).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + os.environ.get("LLM_KEY", "ul-dissertation-local")})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]["content"]

def extract_json(text):
    if "</think>" in text:                       # drop reasoning (even if opening tag is missing)
        text = text.rsplit("</think>", 1)[-1]
    text = re.sub(r"```(?:json)?", "", text).strip()
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in model output")
    depth = 0                                     # balanced-brace scan from first '{'
    for i in range(start, len(text)):
        if text[i] == "{": depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("unbalanced JSON braces")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True); ap.add_argument("--desc", default="")
    ap.add_argument("--src", required=True); ap.add_argument("--graph", default="")
    ap.add_argument("--package", default="", help="comma-separated package filter, e.g. domain,application,interfaces")
    ap.add_argument("--out", required=True)
    ap.add_argument("--free", dest="strict", action="store_false",
                    help="free-form prompting (no enum constraint / repair); use to reproduce the hallucination baseline")
    ap.add_argument("--max-repairs", type=int, default=3, help="max validate-and-repair rounds in strict mode")
    ap.add_argument("--compact-source", action="store_true",
                    help="drop imports/comments, strip method-body contents, truncate long string "
                         "literals; use when full source would exceed the model's context window")
    a = ap.parse_args()
    pkgs = [p.strip() for p in a.package.split(",") if p.strip()]
    source, classes = read_sources(a.src, pkgs, compact=a.compact_source)
    user = (f"Application: {a.app} — {a.desc}\n\n"
            f"Classes to partition ({len(classes)}):\n" + ", ".join(classes) + "\n\n"
            f"Class dependency graph (caller -> callee : weight = number of static references):\n"
            + fmt_graph(a.graph) + "\n\nSource files:\n" + source +
            "\n\nPropose the microservice decomposition. Partition ONLY the "
            f"{len(classes)} classes listed above (every one, exactly once); "
            "do not introduce any new service, entity, or class name.")
    print(f"[exp2] {a.app}: {len(classes)} classes, prompt ~{len(user)//4} tokens; calling LLM...", file=sys.stderr)
    known = set(classes)
    rf = decomposition_schema(classes) if a.strict else {"type": "json_object"}
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    rounds, result = 0, None
    while True:
        raw = call_llm(messages, rf)
        open(a.out + ".raw.txt", "w").write(raw)      # keep last raw model output for debug/repro
        try:
            result = extract_json(raw)
        except Exception as e:
            print(f"[exp2] JSON parse failed: {e}\n[exp2] raw output saved to {a.out}.raw.txt", file=sys.stderr)
            raise
        placed = [c for s in result.get("services", []) for c in s.get("classes", [])]
        extra   = sorted(set(placed) - known)
        missing = sorted(known - set(placed))
        dups    = sorted({c for c in placed if placed.count(c) > 1})
        if not (extra or missing or dups) or not a.strict or rounds >= a.max_repairs:
            break
        rounds += 1
        fix = "Your previous decomposition is invalid; correct it. "
        if extra:   fix += f"Remove these (not real classes): {extra}. "
        if missing: fix += f"Add these real classes, each in exactly one service: {missing}. "
        if dups:    fix += f"These appear in more than one service, keep each once: {dups}. "
        fix += (f"Return the full corrected JSON partitioning all {len(classes)} provided "
                "classes, each exactly once, using only names from the class list.")
        print(f"[exp2] repair round {rounds}: extra={extra} missing={missing} dups={dups}", file=sys.stderr)
        messages += [{"role": "assistant", "content": raw}, {"role": "user", "content": fix}]
    result["_repair_rounds"] = rounds
    json.dump(result, open(a.out, "w"), indent=2)
    print(f"[exp2] saved {a.out} (repair rounds: {rounds})")
    for s in result.get("services", []):
        print(f"  {s['name']} ({len(s['classes'])}): {', '.join(s['classes'])}")

if __name__ == "__main__":
    main()
