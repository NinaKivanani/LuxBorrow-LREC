#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, sys, os, yaml
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt

def load_config():
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    return yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))

cfg = load_config()
paths = cfg["paths"]
LOAN_JSON = Path(paths["out_root"]) / "metrics" / "monthly_loan_counts.json"
SYN_JSON = Path(paths["out_root"]) / "metrics" / "monthly_synonym_counts.json"
OUT_DIR = Path(paths["figures"]); OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_series(target_pairs):
    """Load time series data for target loan-synonym pairs from JSON files."""
    
    if not LOAN_JSON.exists() or not SYN_JSON.exists():
        print(f"Required data files not found: {LOAN_JSON}, {SYN_JSON}")
        return {}
    
    # Load loan and synonym counts by month
    with LOAN_JSON.open("r", encoding="utf-8") as f:
        loan_data = json.load(f)
    
    with SYN_JSON.open("r", encoding="utf-8") as f:
        syn_data = json.load(f)
    
    # target_pairs is a set of (loan, syn) tuples
    series = { (l,s): [] for (l,s) in target_pairs }
    
    # Get all months that have data
    all_months = set(loan_data.keys()) | set(syn_data.keys())
    
    for month in sorted(all_months):
        if month == "unknown":
            continue
        try:
            dt = datetime.strptime(month, "%Y-%m")
        except Exception:
            continue
            
        loan_counts = loan_data.get(month, {})
        syn_counts = syn_data.get(month, {})
        
        for loan, syn in target_pairs:
            lc = loan_counts.get(loan, 0)
            sc = syn_counts.get(syn, 0)
            
            if lc > 0 or sc > 0:  # Only include months with some data
                total = lc + sc
                pref = lc / total if total > 0 else 0.0
                series[(loan, syn)].append((dt, lc, sc, pref))
    
    return series

def movavg(vals, k=3):
    if k<=1: return vals
    out=[]; n=len(vals); h=k//2
    for i in range(n):
        a=max(0,i-h); b=min(n,i+h+1)
        out.append(sum(vals[a:b])/len(vals[a:b]))
    return out

def discover_synonym_pairs_from_borrowing_index(top_n=5):
    """Discover loan-synonym pairs from the actual borrowing index data."""
    
    borrowing_index = Path(paths["borrowing_index"])
    if not borrowing_index.exists():
        return []
    
    # Load the actual loan-synonym pairs
    pairs_usage = {}
    
    try:
        with borrowing_index.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    # Use the actual structure: {"loan": "word", "syn": "synonym", ...}
                    loan = entry.get("loan", "").lower().strip()
                    syn = entry.get("syn", "").lower().strip()
                    if loan and syn and loan != syn:
                        pair_key = (loan, syn)
                        pairs_usage[pair_key] = pairs_usage.get(pair_key, 0) + 1
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Could not read borrowing index: {e}")
        return []
    
    # Sort by usage and return top pairs
    if pairs_usage:
        sorted_pairs = sorted(pairs_usage.items(), key=lambda x: x[1], reverse=True)
        return [pair for pair, _ in sorted_pairs[:top_n]]
    
    return []

def discover_synonym_pairs(loan_data, syn_data, top_n=5):
    """Automatically discover the most active loan-synonym pairs from data."""
    
    # First try to get real pairs from borrowing index
    borrowing_pairs = discover_synonym_pairs_from_borrowing_index(top_n)
    if borrowing_pairs:
        return borrowing_pairs
    
    # Fallback: Find loan words and synonyms that have significant usage
    loan_totals = {}
    syn_totals = {}
    
    for month_data in loan_data.values():
        for word, count in month_data.items():
            loan_totals[word] = loan_totals.get(word, 0) + count
            
    for month_data in syn_data.values():
        for word, count in month_data.items():
            syn_totals[word] = syn_totals.get(word, 0) + count
    
    # Get top loans and top synonyms, pair them up as potential relationships
    top_loans = sorted(loan_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_syns = sorted(syn_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    pairs = []
    for i, (loan, _) in enumerate(top_loans):
        if i < len(top_syns):
            syn, _ = top_syns[i]
            pairs.append((loan, syn))
    
    return pairs

def main():
    # If arguments provided, use them directly
    if len(sys.argv) >= 3:
        args = sys.argv[1:]
        if len(args) % 2 != 0:
            print("Provide pairs as: loan syn [loan syn] ...")
            sys.exit(1)
        pairs = set()
        for i in range(0, len(args), 2):
            pairs.add((args[i].lower(), args[i+1].lower()))
    else:
        # Auto-discover pairs from data
        if not LOAN_JSON.exists() or not SYN_JSON.exists():
            print(f"Required data files not found: {LOAN_JSON}, {SYN_JSON}")
            print("Usage: python scripts/13_plot_synonym_trends.py loan1 syn1 [loan2 syn2 ...]")
            sys.exit(1)
            
        # Load data to discover pairs
        with LOAN_JSON.open("r", encoding="utf-8") as f:
            loan_data = json.load(f)
        with SYN_JSON.open("r", encoding="utf-8") as f:
            syn_data = json.load(f)
            
        discovered_pairs = discover_synonym_pairs(loan_data, syn_data)
        if not discovered_pairs:
            print("No suitable synonym pairs found in data.")
            print("Usage: python scripts/13_plot_synonym_trends.py loan1 syn1 [loan2 syn2 ...]")
            sys.exit(1)
            
        pairs = set(discovered_pairs)
        print(f"Auto-discovered {len(pairs)} synonym pairs: {pairs}")

    series = load_series(pairs)
    if not series:
        print("No data available for plotting.")
        sys.exit(1)
        
    plots_created = 0
    pairs_with_data = 0
    
    for (loan, syn), rows in series.items():
        if not rows:
            print(f"No temporal data for pair: {loan} vs {syn}")
            continue
            
        # Check if there's meaningful data (minimum threshold)
        total_loan_counts = sum(r[1] for r in rows)
        total_syn_counts = sum(r[2] for r in rows)
        min_threshold = 10  # Minimum total occurrences for meaningful analysis
        
        if total_loan_counts + total_syn_counts < min_threshold:
            print(f"Insufficient data for {loan} vs {syn}: loan={total_loan_counts}, syn={total_syn_counts} (need >{min_threshold} total)")
            continue
            
        pairs_with_data += 1
        print(f"Creating plots for {loan} vs {syn}: loan={total_loan_counts}, syn={total_syn_counts} occurrences")
        
        xs = [r[0] for r in rows]
        loan_counts = [r[1] for r in rows]
        syn_counts  = [r[2] for r in rows]
        prefs = [r[3] if r[3] is not None else 0.0 for r in rows]

        # Plot counts
        plt.figure()
        plt.plot(xs, movavg(loan_counts,3), label=f"{loan} (loan)")
        plt.plot(xs, movavg(syn_counts,3),  label=f"{syn} (syn)")
        plt.legend(); plt.xlabel("Month"); plt.ylabel("Count")
        plt.title(f"Counts over time: {loan} vs {syn}")
        plt.tight_layout(); plt.savefig(OUT_DIR / f"syn_counts_{loan}_{syn}.png", dpi=200); plt.close()
        plots_created += 1

        # Plot preference ratio
        plt.figure()
        plt.plot(xs, movavg(prefs,3))
        plt.ylim(0,1)
        plt.xlabel("Month"); plt.ylabel("Preference = loan/(loan+syn)")
        plt.title(f"Preference over time: {loan} vs {syn}")
        plt.tight_layout(); plt.savefig(OUT_DIR / f"syn_pref_{loan}_{syn}.png", dpi=200); plt.close()
        plots_created += 1

    if plots_created > 0:
        print(f"Created {plots_created} meaningful figures for {pairs_with_data} pairs in {OUT_DIR}")
    else:
        print("No plots could be created - no pairs had sufficient data for meaningful analysis.")

if __name__ == "__main__":
    main()
