#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create plots based on OpenLID code-switching statistics vs pattern-based borrowing patterns.
Percentages are calculated dynamically from actual data.
"""

import csv, os, yaml
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# Set up matplotlib for better plots
plt.rcParams.update({
    'font.size': 12,
    'font.family': 'sans-serif',
    'figure.figsize': (10, 6),
    'axes.grid': True,
    'grid.alpha': 0.3
})

def load_config():
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    return yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))

cfg = load_config()
paths = cfg["paths"]
OUT_DIR = Path(paths["figures"]); OUT_DIR.mkdir(parents=True, exist_ok=True)
OPENLID_CSV = Path(paths["out_root"]) / "metrics" / "openlid_diachrony.csv"
MORPHO_CSV = Path(paths["out_root"]) / "metrics" / "rq4_diachrony.csv"

def parse_openlid_rows(path):
    """Parse OpenLID diachrony data"""
    rows = []
    if not path.exists():
        print(f"Warning: {path} not found, skipping OpenLID plots")
        return rows
        
    with open(path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            m = row["month"]
            if not m or m == "unknown": continue
            try: dt = datetime.strptime(m, "%Y-%m")
            except Exception: continue
            rows.append({
                "dt": dt,
                "cs_rate": float(row["cs_rate"]),
                "de_rate": float(row["de_rate"]),
                "fr_rate": float(row["fr_rate"]),
                "en_rate": float(row["en_rate"]),
                "total_tokens": int(row["total_tokens"]),
                "DE": int(row["DE"]),
                "FR": int(row["FR"]),
                "EN": int(row["EN"])
            })
    rows.sort(key=lambda x: x["dt"])
    return rows

def parse_morpho_rows(path):
    """Parse pattern-based borrowing data"""
    rows = []
    if not path.exists():
        print(f"Warning: {path} not found, skipping morphological plots")
        return rows
        
    with open(path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            m = row["month"]
            if not m or m == "unknown": continue
            try: dt = datetime.strptime(m, "%Y-%m")
            except Exception: continue
            rows.append({
                "dt": dt,
                "cs_rate": float(row["cs_rate"]),
                "borrow_share": float(row["borrow_share"]),
                "FR": float(row["donor_FR"]),
                "DE": float(row["donor_DE"]),
                "EN": float(row["donor_EN"]),
            })
    rows.sort(key=lambda x: x["dt"])
    return rows

def movavg(seq, k=3):
    """Moving average smoothing"""
    if k<=1: return seq
    out=[]; n=len(seq); h=k//2
    for i in range(n):
        a=max(0,i-h); b=min(n,i+h+1)
        out.append(sum(seq[a:b])/len(seq[a:b]))
    return out

def plot_comparison(openlid_rows, morpho_rows):
    """Compare OpenLID code-switching vs morphological borrowing rates"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot 1: OpenLID Code-switching rates
    if openlid_rows:
        xs = [r["dt"] for r in openlid_rows]
        cs_rates = movavg([r["cs_rate"] * 100 for r in openlid_rows], 3)
        de_rates = movavg([r["de_rate"] * 100 for r in openlid_rows], 3)
        fr_rates = movavg([r["fr_rate"] * 100 for r in openlid_rows], 3)
        
        ax1.plot(xs, cs_rates, 'b-', linewidth=2, label='Total Code-switching')
        ax1.plot(xs, fr_rates, 'r-', alpha=0.7, label='French')
        ax1.plot(xs, de_rates, 'g-', alpha=0.7, label='German')
        ax1.set_title('OpenLID Code-switching Rates (Actual Language Distribution)')
        ax1.set_ylabel('Percentage (%)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
    
    # Plot 2: Morphological borrowing rates
    if morpho_rows:
        xs2 = [r["dt"] for r in morpho_rows]
        morpho_rates = movavg([r["cs_rate"] * 100 for r in morpho_rows], 3)
        borrow_rates = movavg([r["borrow_share"] * 100 for r in morpho_rows], 3)
        
        ax2.plot(xs2, morpho_rates, 'b-', linewidth=2, label='Code-switching (OpenLID)')
        ax2.plot(xs2, borrow_rates, 'orange', linewidth=2, label='Morphological Borrowing')
        ax2.set_title('Pattern-based Borrowing vs Code-switching')
        ax2.set_ylabel('Percentage (%)')
        ax2.set_xlabel('Time')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUT_DIR/"openlid_vs_morphological_comparison.png", dpi=200, bbox_inches='tight')
    plt.close()

def plot_openlid_donor_mix(rows):
    """Plot OpenLID donor language distribution over time"""
    if not rows:
        return
        
    xs = [r["dt"] for r in rows]
    
    # Calculate proportions of code-switching languages (excluding LU)
    fr_props = []
    de_props = []
    en_props = []
    
    for r in rows:
        total_cs = r["DE"] + r["FR"] + r["EN"]
        if total_cs > 0:
            fr_props.append(r["FR"] / total_cs)
            de_props.append(r["DE"] / total_cs)
            en_props.append(r["EN"] / total_cs)
        else:
            fr_props.append(0)
            de_props.append(0)
            en_props.append(0)
    
    # Smooth the data
    fr_smooth = movavg(fr_props, 3)
    de_smooth = movavg(de_props, 3)
    en_smooth = movavg(en_props, 3)
    
    plt.figure(figsize=(12, 6))
    plt.stackplot(xs, fr_smooth, de_smooth, en_smooth, 
                  labels=["French", "German", "English"],
                  colors=['#ff6b6b', '#4ecdc4', '#45b7d1'],
                  alpha=0.8)
    
    # Compute overall OpenLID code-switching percentage from data
    cs_total = sum((r["DE"] + r["FR"] + r["EN"]) for r in rows)
    total_tokens = sum(r["total_tokens"] for r in rows) or 1
    cs_pct = (cs_total / total_tokens) * 100

    plt.title(f"OpenLID Code-switching Language Distribution Over Time\n(Actual {cs_pct:.2f}% code-switching)")
    plt.xlabel("Time")
    plt.ylabel("Proportion of Code-switching")
    plt.legend(loc="upper right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR/"openlid_donor_mix.png", dpi=200, bbox_inches='tight')
    plt.close()

def plot_openlid_overview():
    """Create overview plot of OpenLID statistics"""
    # Read overall statistics
    overall_file = Path(paths["out_root"]) / "metrics" / "openlid_overall.csv"
    if not overall_file.exists():
        print(f"Warning: {overall_file} not found")
        return
    
    languages = []
    counts = []
    shares = []
    
    with open(overall_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            languages.append(row['language'])
            counts.append(int(row['count']))
            shares.append(float(row['share']) * 100)
    
    # Create pie chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Pie chart
    colors = ['#66b3ff', '#ff6b6b', '#4ecdc4', '#45b7d1']
    ax1.pie(shares, labels=[f"{lang}\n{share:.1f}%" for lang, share in zip(languages, shares)], 
            colors=colors[:len(languages)], autopct='', startangle=90)
    ax1.set_title("OpenLID Language Distribution\n(All Tokens)")
    
    # Bar chart
    bars = ax2.bar(languages, shares, color=colors[:len(languages)])
    ax2.set_title("OpenLID Language Percentages")
    ax2.set_ylabel("Percentage (%)")
    ax2.set_xlabel("Language")
    
    # Add value labels on bars
    for bar, share in zip(bars, shares):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{share:.1f}%', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(OUT_DIR/"openlid_language_overview.png", dpi=200, bbox_inches='tight')
    plt.close()

def main():
    print("Creating OpenLID-based plots...")
    
    # Parse data
    openlid_rows = parse_openlid_rows(OPENLID_CSV)
    morpho_rows = parse_morpho_rows(MORPHO_CSV)
    
    # Create plots
    plot_comparison(openlid_rows, morpho_rows)
    plot_openlid_donor_mix(openlid_rows)
    plot_openlid_overview()
    
    print(f"OpenLID plots saved to {OUT_DIR}")
    print(f"Created {len(list(OUT_DIR.glob('openlid_*.png')))} OpenLID plots")

if __name__ == "__main__":
    main()

