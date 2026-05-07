#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, re
from pathlib import Path
import yaml
from collections import Counter, defaultdict

def mk_arrow(x, y):
    rx = rf"(?P<stem>.+?){re.escape(x)}$"
    tmpl = "{stem}" + y
    return rx, tmpl

def mk_add(add):
    rx = r"(?P<stem>.+)$"
    tmpl = "{stem}" + add
    return rx, tmpl

def compile_one(pattern: str):
    p = pattern.strip()
    if "→" in p:
        x, y = p.split("→", 1)
        x, y = x.strip(), y.strip()
        rx, tmpl = mk_arrow(x, y)
        return [{"regex": rx, "template": tmpl}]
    if p.startswith("+"):
        add = p[1:].strip()
        rx, tmpl = mk_add(add)
        return [{"regex": rx, "template": tmpl}]
    if p == "exact":
        return [{"regex": r"(?P<stem>.+)$", "template": "{stem}"}]
    return [{"regex": r"(?P<stem>.+)$", "template": "{stem}"}]

def guess_kind(patt: str) -> str:
    if patt == "exact": return "lexicon"
    if "→" in patt or patt.startswith("+"): return "morph"
    return "orth"

def infer_type_from_lexicon(loanwords_path: Path):
    """Return map pattern -> type from lux_loanwords.ud.json (GOLD STANDARD)."""
    type_map = {}
    if not loanwords_path.exists():
        return type_map
    try:
        arr = json.loads(loanwords_path.read_text(encoding="utf-8"))
    except Exception:
        return type_map
    votes = defaultdict(Counter)
    for entry in arr:
        for d in entry.get("details", []):
            patt = d.get("pattern")
            ptype = d.get("type")
            if patt and ptype:
                votes[patt][ptype] += 1
    for patt, cnt in votes.items():
        ptype, _ = cnt.most_common(1)[0]
        type_map[patt] = ptype
    return type_map

def infer_donor_from_lexicon(loanwords_path: Path):
    """Return map pattern -> donor via majority vote from lux_loanwords.ud.json."""
    donor_map = {}
    if not loanwords_path.exists():
        return donor_map
    try:
        arr = json.loads(loanwords_path.read_text(encoding="utf-8"))
    except Exception:
        return donor_map
    votes = defaultdict(Counter)
    for entry in arr:
        for d in entry.get("details", []):
            patt = d.get("pattern")
            lang = (d.get("language") or "").upper()
            if patt and lang in {"FR","DE","EN"}:
                votes[patt][lang] += 1
    for patt, cnt in votes.items():
        donor, _ = cnt.most_common(1)[0]
        donor_map[patt] = donor
    return donor_map

def load_patterns_any(path: Path):
    """Accept either array-of-objects or dict-of-examples."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        # already in array-of-objects
        return raw
    if isinstance(raw, dict):
        # dict: key = pattern, val = list of example pairs
        out = []
        for patt, exs in raw.items():
            out.append({
                "pattern": patt,
                "type": guess_kind(patt),
                "donor": None,          # to be inferred
                "examples": exs[:10] if isinstance(exs, list) else []
            })
        return out
    raise ValueError("patterns_with_examples.* must be JSON list or dict")

def main():
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    paths = cfg["paths"]

    patt_path = Path(paths["pattern_file"])
    loan_path = Path(paths.get("loanwords_json",""))

    dst_dir = Path(paths["manifests"]); dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "compiled_patterns.json"

    # Load patterns (any format) and GOLD STANDARD mappings from loanwords database
    items = load_patterns_any(patt_path)
    type_gold_standard = infer_type_from_lexicon(loan_path)    # AUTHORITATIVE
    donor_guess = infer_donor_from_lexicon(loan_path)

    index = {}
    for rec in items:
        patt = rec.get("pattern") or rec.get("patt") or rec.get("rule")
        if not patt: continue
        # PRIORITIZE GOLD STANDARD: loanwords database > explicit type > guess_kind fallback
        kind = (type_gold_standard.get(patt) or rec.get("type") or guess_kind(patt)).lower()
        donor = rec.get("donor") or donor_guess.get(patt)
        steps = compile_one(patt)

        index[patt] = {
            "kind": kind,
            "donor": donor,                 # may be None if unknown (OK)
            "steps": steps,
            "examples": rec.get("examples", [])[:10]
        }

    dst.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", dst, f"(patterns={len(index)})")

if __name__ == "__main__":
    main()
