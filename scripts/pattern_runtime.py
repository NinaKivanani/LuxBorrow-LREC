#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, re
from pathlib import Path
from morph_gates import morph_gate

def load_compiled_index(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def apply_patterns(surface: str, index: dict) -> list[dict]:
    s = surface or ""
    out = []
    for key, meta in index.items():
        kind = meta.get("kind")
        donor = meta.get("donor")
        steps = meta.get("steps", [])
        examples = meta.get("examples", [])
        # Use ALL patterns - morphological, orthographic, AND lexicon!
        # No exclusions whatsoever!
        if not steps:
            continue

        # SPECIAL CASE: "exact" must only match known example forms, not everything
        if key == "exact":
            valid_forms = set()
            for ex in examples:
                if isinstance(ex, (list, tuple)) and len(ex) >= 1:
                    valid_forms.add(ex[0].lower())  # First element is the borrowed form
            if s.lower() not in valid_forms:
                continue

        last = steps[-1]
        rx = last.get("regex")
        tmpl = last.get("template", "{stem}")
        if not rx:
            continue
        m = re.compile(rx).match(s)
        if not m:
            continue
        if not morph_gate(s, key):
            continue
        stem = m.groupdict().get("stem", s)
        cand = tmpl.replace("{stem}", stem)
        out.append({
            "pattern": key,
            "kind": kind or "morph",
            "donor": donor,
            "candidate": cand
        })
    return out
