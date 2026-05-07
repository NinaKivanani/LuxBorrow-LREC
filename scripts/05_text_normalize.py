#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, yaml
from pathlib import Path

def main():
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    paths = cfg["paths"]

    src_dir = Path(paths["out_raw"])
    dst_dir = Path(paths["out_tn"]); dst_dir.mkdir(parents=True, exist_ok=True)

    # Only process Luxembourgish sentences (after OpenLID filtering)
    for src in sorted(src_dir.glob("*_LU.jsonl")):
        dst = dst_dir / src.name
        with src.open("r", encoding="utf-8") as f, dst.open("w", encoding="utf-8") as g:
            for line in f:
                if not line.strip():
                    continue
                try:
                    ex = json.loads(line)
                except json.JSONDecodeError:
                    # Skip malformed JSON lines
                    continue
                sentences = ex.get("sentences", [])
                ex["tn_changelog"] = [[] for _ in sentences]  # no changes
                g.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"TN view written to {dst_dir}")

if __name__ == "__main__":
    main()
