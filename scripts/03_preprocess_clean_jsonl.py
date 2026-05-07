#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple passthrough script for clean JSONL format.
- Input: articles_clean.jsonl with "text", "lang", and metadata fields
- Output: Same data, just moved to the processed directory for pipeline compatibility
- No tokenization or form_tn processing needed
"""

import json, os, argparse
from pathlib import Path
import yaml

def process_item(item: dict) -> dict:
    """Process an article item from the clean JSONL format - just pass through."""
    return {
        "id": str(item.get("article_id", "")),
        "section": item.get("category_name", ""),
        "text": item.get("text", ""),  # Keep raw text as-is
        "public_date": item.get("public_date", ""),
        "lang": item.get("lang", "ltz_Latn"),
        "title": item.get("title", ""),
        "category_id": item.get("category_id", ""),
        "type": item.get("type", ""),
        "header": item.get("header", ""),
        "tags": item.get("tags")
    }

def main():
    ap = argparse.ArgumentParser(description="Process clean JSONL articles for pipeline.")
    ap.add_argument("--config", default="config/config.yaml", help="Path to YAML config")
    ap.add_argument("--input", help="Input JSONL file (default: articles_clean.jsonl)")
    ap.add_argument("--output", help="Output directory (default: from config)")
    args = ap.parse_args()

    cfg_path = Path(os.environ.get("CONFIG_PATH", args.config))
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        paths = cfg.get("paths", {})
    else:
        paths = {}

    # Determine input file
    if args.input:
        input_file = Path(args.input)
    else:
        input_file = Path("data/rtl_raw/articles_clean.jsonl")
        if not input_file.exists():
            print(f"Error: Input file {input_file} not found")
            return 1

    # Determine output directory
    if args.output:
        out_dir = Path(args.output)
    else:
        out_dir = Path(paths.get("out_raw", "data/processed/v1/raw_jsonl"))
    
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = Path(paths.get("logs", "logs"))
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Process the input file
    output_file = out_dir / input_file.name
    processed_count = 0
    
    print(f"Processing {input_file} → {output_file}")
    
    with input_file.open("r", encoding="utf-8") as f, output_file.open("w", encoding="utf-8") as g:
        for line_num, line in enumerate(f):
            if not line.strip(): 
                continue
            try:
                item = json.loads(line.strip())
                processed_item = process_item(item)
                g.write(json.dumps(processed_item, ensure_ascii=False) + "\n")
                processed_count += 1
                
                if processed_count % 10000 == 0:
                    print(f"Processed {processed_count} articles...")
                    
            except json.JSONDecodeError as e:
                print(f"Skipping malformed JSON at line {line_num + 1}: {e}")
                continue
            except Exception as e:
                print(f"Error processing line {line_num + 1}: {e}")
                continue

    # Create completion log
    log_file = logs_dir / f"{input_file.stem}.preprocess.done"
    log_file.write_text(f"Processed {processed_count} articles", encoding="utf-8")

    print(f"✅ Processing complete: {processed_count} articles processed")
    print(f"   Output: {output_file}")
    print(f"   Log: {log_file}")

if __name__ == "__main__":
    main()
