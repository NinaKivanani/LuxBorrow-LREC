#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
python scripts/00b_convert_pairs_csv_to_json.py \
  /project/.../resources/loanword_synonym_pairs.csv \
  resources/loanword_synonyms_unique.json
'''

import csv, json, sys
from pathlib import Path

def main(inp, outp):
    inp = Path(inp); outp = Path(outp)
    outp.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with inp.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            loan = (row.get("loanword") or "").strip()
            syn  = (row.get("synonym")  or "").strip()
            pos  = (row.get("part_of_speech") or "").strip()
            donor= (row.get("loan_language")  or "").strip().upper() or None
            if not loan or not syn or loan.lower()==syn.lower():
                continue
            rows.append({
                "loan": loan,
                "syn": syn,
                "meaning_id": "",     # unknown here (fine)
                "part_of_speech": pos,
                "loan_language": donor
            })
    outp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", outp, f"(pairs={len(rows)})")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/00b_convert_pairs_csv_to_json.py IN.csv OUT.json")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
