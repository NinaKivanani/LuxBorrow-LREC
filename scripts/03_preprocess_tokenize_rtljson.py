#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple passthrough script for RTL JSONL format.
- Input: articles_clean.jsonl 
- Output: Same data, just moved to the processed directory for pipeline compatibility
- Only processes the "text" field, passes everything else through unchanged
"""

import json, os, argparse
from pathlib import Path
import yaml

def process_item(item: dict) -> dict:
    """Process an article item - just pass through with text field."""
    return {
        "id": str(item.get("article_id", "")),
        "section": item.get("category_name", ""),
        "text": item.get("text", ""),
        "public_date": item.get("public_date", ""),
        "lang": item.get("lang", "ltz_Latn"),
        "title": item.get("title", ""),
        "category_id": item.get("category_id", ""),
        "type": item.get("type", ""),
        "header": item.get("header", ""),
        "tags": item.get("tags")
    }

def main():
    ap = argparse.ArgumentParser(description="Process RTL news articles for pipeline.")
    ap.add_argument("--config", default="config/config.yaml", help="Path to YAML config")
    ap.add_argument("--require-blingfire", action="store_true", help="Ignored - for compatibility")
    args = ap.parse_args()

    cfg_path = Path(os.environ.get("CONFIG_PATH", args.config))
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    paths = cfg["paths"]

    src_dir = Path(paths["raw_dir"])
    out_dir = Path(paths["out_raw"]); out_dir.mkdir(parents=True, exist_ok=True)
    logs = Path(paths["logs"]); logs.mkdir(parents=True, exist_ok=True)

    # Look for the articles_clean.jsonl file
    src_file = src_dir / "articles_clean.jsonl"
    if not src_file.exists():
        # Fall back to any JSONL files if specific file not found
        for src in sorted(src_dir.glob("*.jsonl")):
            src_file = src
            break
    
    if not src_file.exists():
        print(f"No JSONL files found in {src_dir}")
        return
        
    dst = out_dir / src_file.name
    print(f"Processing {src_file} → {dst}")
    processed_count = 0
    
    with src_file.open("r", encoding="utf-8") as f, dst.open("w", encoding="utf-8") as g:
        for line_num, line in enumerate(f):
            if not line.strip(): 
                continue
            try:
                ex = json.loads(line)
                g.write(json.dumps(process_item(ex), ensure_ascii=False) + "\n")
                processed_count += 1
                
                if processed_count % 10000 == 0:
                    print(f"Processed {processed_count} articles...")
            except json.JSONDecodeError as e:
                print(f"Skipping malformed JSON at line {line_num + 1}: {e}")
                continue
            except Exception as e:
                print(f"Error processing line {line_num + 1}: {e}")
                continue
                
    print(f"Processed {processed_count} articles")
    (logs / f"{src_file.stem}.tokenize.done").write_text(f"Processed {processed_count} articles", encoding="utf-8")

    print(f"Articles processed → {out_dir}")

if __name__ == "__main__":
    main()