#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def morph_gate(surface: str, rule_key: str) -> bool:
    s = (surface or "").lower()

    # -itéit → -ité (allow plurals -itéiten)
    if rule_key == "éit→é":
        return s.endswith("itéit") or s.endswith("itéiten")

    # -éiert → -é (participial adjectives)
    if rule_key == "éiert→é":
        return s.endswith("éiert")

    # -éieren → -er (FR verbs integrated in LU spelling)
    if rule_key == "éieren→er":
        return s.endswith("éieren")

    # -éieren → -ieren (DE verbs)
    if rule_key == "éieren→ieren":
        return s.endswith("éieren")

    # -ioun/-oun → -ion/-on
    if rule_key in {"ioun→ion", "oun→on", "oun→on + k→c"}:
        return s.endswith("ioun") or s.endswith("tioun") or s.endswith("oun")

    return True
