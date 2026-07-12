#!/usr/bin/env python3
"""Score a JPetStore decomposition with the Experiment-1 metric suite.
ICP/ACS/CHI/NED are objective (from the class call graph); BCP and GS Jaccard use a
class-level gold standard derived from the Sellami 4-service partition.

Usage:
  # score an LLM decomposition produced by run_exp2.py:
  python eval_metrics.py --partition exp2_jpetstore_decomposition.json --graph callGraph.json
  # with no --partition it scores the built-in manual reference decomposition.
"""
import argparse, json, statistics
from collections import Counter

DEFAULT_GRAPH = "data/jpetstore/callGraph.json"
S = lambda x: x.split(".")[-1]

# class-level gold standard from Sellami et al. 4 services
GOLD = {
  "account": ["Account", "AccountService", "AccountActionBean"],
  "catalog": ["Category", "Product", "Item", "CatalogService", "CatalogActionBean"],
  "cart":    ["Cart", "CartItem", "CartActionBean"],
  "order":   ["Order", "LineItem", "OrderService", "OrderActionBean", "Sequence"],
}
CAP = {c: s for s, cl in GOLD.items() for c in cl}
CAP["AbstractActionBean"] = "shared"

# built-in reference (used when --partition is omitted)
REFERENCE = {
  "AccountService": ["Account", "AccountService", "AccountActionBean"],
  "CatalogService": ["Category", "Product", "Item", "CatalogService", "CatalogActionBean", "AbstractActionBean"],
  "CartService":    ["Cart", "CartItem", "CartActionBean"],
  "OrderService":   ["Order", "LineItem", "OrderService", "OrderActionBean", "Sequence"],
}

def _strip(c):
    return c.split(".")[-1] if isinstance(c, str) else c

def _service_list(d):
    """A list of service dicts, or None."""
    if isinstance(d, list) and d and isinstance(d[0], dict):
        return d
    if isinstance(d, dict):
        if isinstance(d.get("services"), list):
            return d["services"]
        for v in d.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and \
               any(k in v[0] for k in ("classes", "members", "classNames")):
                return v
    return None

def _name_to_classes(d):
    """A dict mapping serviceName -> [classes], possibly under a wrapper key, or None."""
    for cand in (d.get("services"), d.get("decomposition"), d.get("microservices"), d) if isinstance(d, dict) else ():
        if isinstance(cand, dict) and cand and all(
                isinstance(v, list) and all(isinstance(x, str) for x in v) for v in cand.values()):
            return cand
    return None

def load_partition(path):
    if not path:
        return REFERENCE
    d = json.load(open(path))
    lst = _service_list(d)
    if lst is not None:
        part = {}
        for s in lst:
            name = s.get("name") or s.get("service") or s.get("serviceName") or f"Service{len(part)+1}"
            classes = s.get("classes") or s.get("members") or s.get("classNames") or []
            part[name] = [_strip(c) for c in classes]
        return part
    nmap = _name_to_classes(d)
    if nmap is not None:
        return {k: [_strip(c) for c in v] for k, v in nmap.items()}
    raise ValueError("could not locate services in the JSON; please share the file so the parser can be adjusted")

def metrics(part, edges):
    c2s = {c: s for s, cl in part.items() for c in cl}
    tot = sum(w for _, _, w in edges)
    inter_w = sum(w for a, b, w in edges if c2s.get(a) != c2s.get(b))
    inter_e = sum(1 for a, b, w in edges if c2s.get(a) != c2s.get(b))
    k = len(part)
    sizes = [len(v) for v in part.values()]
    mean = sum(sizes) / len(sizes)
    cv = statistics.pstdev(sizes) / mean if mean else 0
    bcps = []
    for cl in part.values():
        labs = [CAP.get(c) for c in cl if CAP.get(c) != "shared"]
        bcps.append(1.0 if not labs else Counter(labs).most_common(1)[0][1] / len(labs))
    return dict(k=k, ICP=round(inter_w / tot, 3), ACS=round(2 * inter_e / k, 3),
                BCP=round(sum(bcps) / len(bcps), 3), CHI=round((tot - inter_w) / tot, 3),
                NED=round(1 - cv, 3), sizes=sizes)

def gs_jaccard(part):
    js = []
    for gcl in GOLD.values():
        g = set(gcl)
        js.append(max((len(g & set(p)) / len(g | set(p)) for p in part.values()), default=0))
    return round(sum(js) / len(js), 3)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--partition", default="")
    ap.add_argument("--graph", default=DEFAULT_GRAPH)
    a = ap.parse_args()
    part = load_partition(a.partition)
    d = json.load(open(a.graph))
    edges = [(S(e["source"]), S(e["target"]), e.get("weight", 1)) for e in d["edges"]]
    m = metrics(part, edges); gj = gs_jaccard(part)
    print(f"Decomposition ({'built-in reference' if not a.partition else a.partition}), k={m['k']}:")
    for s, cl in part.items():
        print(f"  {s} ({len(cl)}): {', '.join(cl)}")
    print(f"\nMetrics: ICP={m['ICP']}  ACS={m['ACS']}  BCP={m['BCP']}  CHI={m['CHI']}  NED={m['NED']}")
    print(f"sizes={m['sizes']}   GS Jaccard (vs Sellami class-level) = {gj}")

if __name__ == "__main__":
    main()
