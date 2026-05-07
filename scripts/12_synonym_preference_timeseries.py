#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Synonym preference timeseries analysis.
Tracks loanword vs synonym usage over time.
Updated to work with direct JSONL text (no form_tn needed).
"""

import json, os, sys
from pathlib import Path
from collections import defaultdict, Counter
import yaml

def norm_token(s):
    """Normalize token for matching."""
    if not s:
        return ""
    return s.strip().lower()

def month_key(date_str):
    """Extract YYYY-MM from date string."""
    if not date_str or len(date_str) < 7:
        return "unknown"
    return date_str[:7]  # YYYY-MM

def main():
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    paths = cfg["paths"]
    
    # Load synonym pairs for tracking
    syn_pairs_path = Path(paths["loan_syn_pairs"])
    if not syn_pairs_path.exists():
        print(f"Synonym pairs file not found: {syn_pairs_path}")
        sys.exit(1)
        
    print(f"Loading synonym pairs from {syn_pairs_path}")
    with syn_pairs_path.open("r", encoding="utf-8") as f:
        synonym_pairs = json.load(f)
    
    # Build lookup for valid loan-synonym pairs
    valid_pairs = set()
    for pair in synonym_pairs:
        loan = norm_token(pair.get("loan", ""))
        syn = norm_token(pair.get("syn", ""))
        if loan and syn:
            valid_pairs.add((loan, syn))
    
    print(f"Loaded {len(valid_pairs)} valid loan-synonym pairs")
    
    # Instead of using borrowing_switch.jsonl (which has a different format),
    # we'll directly use the synonym pairs from the resources file
    print(f"Using synonym pairs directly from resources file rather than borrowing index")
    
    # Build lookup index directly from the synonym pairs  
    index_by_form = defaultdict(list)
    for pair in synonym_pairs:
        loan_form = norm_token(pair.get("loan", ""))
        syn_form = norm_token(pair.get("syn", ""))
        loan_mid = pair.get("meaning_id", "") or ""
        syn_mid = loan_mid  # Same meaning_id for both
        loan_lang = pair.get("loan_language", "")
        
        # Only use valid pairs with both parts
        if loan_form and syn_form:
            # Add to lookup index
            index_by_form[loan_form].append(("loan", loan_form, syn_form, loan_mid))
            index_by_form[syn_form].append(("synonym", loan_form, syn_form, syn_mid))
    
    print(f"Built index with {len(index_by_form)} unique forms")
    
    # Initialize counters
    month_counts_loan = defaultdict(Counter)
    month_counts_syn = defaultdict(Counter)
    sec_month_loan = defaultdict(lambda: defaultdict(Counter))
    sec_month_syn = defaultdict(lambda: defaultdict(Counter))
    pairs_seen = set()
    
    # Process all documents
    data_dir = Path(paths["out_raw"])
    print(f"Processing documents from {data_dir}")
    
    # Prefer tokenized LU outputs for consistent token-level analysis
    files = list(sorted(data_dir.glob("*_LU.jsonl")))
    if not files:
        files = list(sorted(data_dir.glob("*.jsonl")))
    
    for jsonl_file in files:
        print(f"Processing {jsonl_file.name}")
        
        with jsonl_file.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                    
                try:
                    ex = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                section = ex.get("section", "unknown")
                date = ex.get("public_date", "")
                mk = month_key(date)

                # Prefer rich annotations, fallback to tokenized sentences if absent
                loanword_tags = ex.get("loanword_tags", [])
                tokenized = ex.get("tokenized_sentences", [])

                if loanword_tags:
                    for si, sentence_tags in enumerate(loanword_tags):
                        for token_tag in sentence_tags:
                            if not isinstance(token_tag, dict) or "word" not in token_tag:
                                continue
                            word = token_tag["word"]
                            form_tn = norm_token(word)
                            if not form_tn:
                                continue
                            # Count pairs from BORROWED evidence
                            if (token_tag.get("tag") == "BORROWED" and 
                                token_tag.get("evidence") and 
                                "lux_synonyms" in token_tag["evidence"]):
                                evidence = token_tag["evidence"]
                                lux_synonyms = evidence.get("lux_synonyms", [])
                                for synonym in lux_synonyms:
                                    syn_norm = norm_token(synonym)
                                    if syn_norm and (form_tn, syn_norm) in valid_pairs:
                                        key = f"{form_tn}|||{syn_norm}|||"
                                        pairs_seen.add(key)
                                        month_counts_loan[mk][form_tn] += 1
                                        sec_month_loan[section][mk][form_tn] += 1
                            # Also check direct membership in index
                            if form_tn in index_by_form:
                                for role, loan, syn, mid in index_by_form[form_tn]:
                                    key = f"{loan}|||{syn}|||{mid}"
                                    pairs_seen.add(key)
                                    if role == "loan":
                                        month_counts_loan[mk][loan] += 1
                                        sec_month_loan[section][mk][loan] += 1
                                    else:
                                        month_counts_syn[mk][syn] += 1
                                        sec_month_syn[section][mk][syn] += 1
                elif tokenized:
                    # Simple lexical count from tokenized sentences using pairs index
                    for sent in tokenized:
                        for tok in sent:
                            form_tn = norm_token(tok)
                            if not form_tn:
                                continue
                            if form_tn in index_by_form:
                                for role, loan, syn, mid in index_by_form[form_tn]:
                                    key = f"{loan}|||{syn}|||{mid}"
                                    pairs_seen.add(key)
                                    if role == "loan":
                                        month_counts_loan[mk][loan] += 1
                                        sec_month_loan[section][mk][loan] += 1
                                    else:
                                        month_counts_syn[mk][syn] += 1
                                        sec_month_syn[section][mk][syn] += 1
    
    print(f"Found {len(pairs_seen)} unique loan-synonym pairs")
    
    # Save results
    out_dir = Path(paths["out_metrics"])
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Save monthly counts
    loan_output = {mk: dict(counts) for mk, counts in month_counts_loan.items()}
    syn_output = {mk: dict(counts) for mk, counts in month_counts_syn.items()}
    
    with (out_dir / "monthly_loan_counts.json").open("w", encoding="utf-8") as f:
        json.dump(loan_output, f, ensure_ascii=False, indent=2)
    
    with (out_dir / "monthly_synonym_counts.json").open("w", encoding="utf-8") as f:
        json.dump(syn_output, f, ensure_ascii=False, indent=2)
    
    # Save section-specific counts
    sec_loan_output = {
        sec: {mk: dict(counts) for mk, counts in month_data.items()}
        for sec, month_data in sec_month_loan.items()
    }
    sec_syn_output = {
        sec: {mk: dict(counts) for mk, counts in month_data.items()}
        for sec, month_data in sec_month_syn.items()
    }
    
    with (out_dir / "section_monthly_loan_counts.json").open("w", encoding="utf-8") as f:
        json.dump(sec_loan_output, f, ensure_ascii=False, indent=2)
    
    with (out_dir / "section_monthly_synonym_counts.json").open("w", encoding="utf-8") as f:
        json.dump(sec_syn_output, f, ensure_ascii=False, indent=2)
    
    print(f"Results saved to {out_dir}")

if __name__ == "__main__":
    main()
