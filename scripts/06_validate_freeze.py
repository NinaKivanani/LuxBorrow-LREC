#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, yaml, os
from pathlib import Path
from collections import Counter

def main():
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    paths = cfg["paths"]

    raw_dir = Path(paths["out_raw"])
    tn_dir  = Path(paths["out_tn"])

    docs = tok_raw = tok_tn = tn_changes = 0
    lid_counts = Counter()

    for src in sorted(raw_dir.glob("*_LU.jsonl")):
        print(f"[DEBUG] Processing raw file: {src}")
        with src.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    ex = json.loads(line); docs += 1
                except json.JSONDecodeError as e:
                    print(f"[ERROR] JSON error in {src} at line {line_num}: {e}")
                    print(f"[ERROR] Line content: {repr(line[:100])}")
                    raise
                for sent in ex["sentences"]:
                    tok_raw += len(sent)
                for lids in ex.get("lid_sentences", []):
                    for L in lids: lid_counts[L] += 1

    for src in sorted(tn_dir.glob("*_LU.jsonl")):
        with src.open("r", encoding="utf-8") as f:
            for line in f:
                ex = json.loads(line)
                for sent, log in zip(ex["sentences"], ex.get("tn_changelog", [[]]*len(ex["sentences"]))):
                    tok_tn += len(sent); tn_changes += len(log)

    print("=== Freeze validation ===")
    print("Docs:", docs)
    print("Tokens RAW:", tok_raw)
    print("Tokens TN :", tok_tn)
    print("TN changes:", tn_changes)
    if lid_counts:
        print("LID counts:", dict(lid_counts))

if __name__ == "__main__":
    main()
