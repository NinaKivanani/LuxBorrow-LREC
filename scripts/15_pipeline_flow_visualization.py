#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Pipeline Flow Visualization
Shows the flow from OpenLID language detection → Research Questions analysis.
Creates a dashboard-style plot with hierarchical information flow.
"""

import os, csv, json, yaml
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for headless environment
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Professional styling
plt.style.use('default')
plt.rcParams.update({
    'font.size': 11,
    'font.family': 'sans-serif',
    'axes.linewidth': 1.2,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight'
})

def load_config():
    """Load configuration."""
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    with open(cfg_path, 'r') as f:
        return yaml.safe_load(f)

def load_openlid_data():
    """Load OpenLID language distribution data."""
    cfg = load_config()
    paths = cfg["paths"]
    overall_file = Path(paths["out_root"]) / "metrics" / "openlid_overall.csv"
    
    if not overall_file.exists():
        print(f"Warning: {overall_file} not found")
        return None
    
    languages = []
    counts = []
    shares = []
    
    with open(overall_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            languages.append(row['language'])
            counts.append(int(row['count']))
            shares.append(float(row['share']) * 100)
    
    return {
        'languages': languages,
        'counts': counts,
        'shares': shares,
        'total_tokens': sum(counts)
    }

def load_rq_metrics():
    """Load research question metrics."""
    cfg = load_config()
    paths = cfg["paths"]
    metrics = {}
    
    # RQ1 - Code-switching by section (different data structure)
    rq1_section = Path(paths["out_root"]) / "metrics" / "rq1_by_section.csv"
    if rq1_section.exists():
        rq1_data = pd.read_csv(rq1_section)
        # Get unique sections/groups
        sections = rq1_data['group'].unique() if 'group' in rq1_data.columns else []
        # Calculate average metric (could be cmi, entropy, etc.)
        avg_metric = rq1_data['mean'].mean() if 'mean' in rq1_data.columns else 0
        metrics['rq1'] = {
            'avg_metric': avg_metric,
            'sections': len(sections),
            'metric_name': 'Code-mixing Index',
            'total_observations': rq1_data['n'].sum() if 'n' in rq1_data.columns else 0
        }
    
    # RQ3 - Borrowing patterns
    rq3_patterns = Path(paths["out_root"]) / "metrics" / "rq3_borrowing_patterns.csv"
    if rq3_patterns.exists():
        rq3_data = pd.read_csv(rq3_patterns)
        metrics['rq3'] = {
            'total_patterns': len(rq3_data),
            'top_pattern': rq3_data.iloc[0]['pattern'] if len(rq3_data) > 0 else 'N/A',
            'top_count': rq3_data.iloc[0]['count'] if len(rq3_data) > 0 else 0,
            'total_borrowings': rq3_data['count'].sum()
        }
    
    # RQ3 - Donor languages
    rq3_donors = Path(paths["out_root"]) / "metrics" / "rq3_donor_split_overall.csv"
    if rq3_donors.exists():
        donor_data = pd.read_csv(rq3_donors)
        metrics['rq3_donors'] = {}
        for _, row in donor_data.iterrows():
            metrics['rq3_donors'][row['donor']] = row['share'] * 100
    
    # RQ4 - Diachronic analysis
    rq4_diach = Path(paths["out_root"]) / "metrics" / "rq4_diachrony.csv"
    if rq4_diach.exists():
        rq4_data = pd.read_csv(rq4_diach)
        rq4_data = rq4_data[rq4_data['month'] != 'unknown']
        if len(rq4_data) > 0:
            metrics['rq4'] = {
                'time_periods': len(rq4_data),
                'avg_borrow_rate': rq4_data['borrow_share'].mean() * 100,
                'trend': 'increasing' if rq4_data['borrow_share'].iloc[-1] > rq4_data['borrow_share'].iloc[0] else 'decreasing'
            }
    
    return metrics

def create_pipeline_flow_dashboard():
    """Create comprehensive pipeline flow visualization."""
    
    # Load data
    openlid_data = load_openlid_data()
    rq_metrics = load_rq_metrics()
    
    if not openlid_data:
        print("Cannot create visualization without OpenLID data")
        return
    
    # Create figure with custom layout
    fig = plt.figure(figsize=(16, 12))
    
    # Define layout areas
    # Top: OpenLID Language Distribution
    ax_main = plt.subplot2grid((4, 4), (0, 0), colspan=4, rowspan=1)
    ax_pie = plt.subplot2grid((4, 4), (1, 0), colspan=1, rowspan=1)
    
    # Middle: Flow arrows and pipeline info
    ax_flow = plt.subplot2grid((4, 4), (1, 1), colspan=3, rowspan=1)
    
    # Bottom: Research Questions breakdown
    ax_rq1 = plt.subplot2grid((4, 4), (2, 0), colspan=1, rowspan=1)
    ax_rq3 = plt.subplot2grid((4, 4), (2, 1), colspan=1, rowspan=1)
    ax_rq3_donors = plt.subplot2grid((4, 4), (2, 2), colspan=1, rowspan=1)
    ax_rq4 = plt.subplot2grid((4, 4), (2, 3), colspan=1, rowspan=1)
    
    # Summary statistics at bottom
    ax_summary = plt.subplot2grid((4, 4), (3, 0), colspan=4, rowspan=1)
    
    # === TOP SECTION: Main Title and Overview ===
    ax_main.text(0.5, 0.5, 'Luxembourgish Code-Switching Pipeline: OpenLID → Research Questions', 
                ha='center', va='center', fontsize=18, fontweight='bold',
                transform=ax_main.transAxes)
    ax_main.text(0.5, 0.1, f"Total Tokens Analyzed: {openlid_data['total_tokens']:,}", 
                ha='center', va='center', fontsize=12, style='italic',
                transform=ax_main.transAxes)
    ax_main.axis('off')
    
    # === LANGUAGE DISTRIBUTION PIE CHART ===
    colors = ['#66b3ff', '#ff9999', '#99ff99', '#ffcc99']
    wedges, texts, autotexts = ax_pie.pie(
        openlid_data['shares'], 
        labels=[f"{lang}\n{share:.1f}%" for lang, share in zip(openlid_data['languages'], openlid_data['shares'])],
        colors=colors[:len(openlid_data['languages'])],
        autopct='',
        startangle=90,
        textprops={'fontsize': 10}
    )
    ax_pie.set_title('OpenLID Language\nDistribution', fontsize=12, fontweight='bold', pad=20)
    
    # === FLOW DIAGRAM ===
    ax_flow.set_xlim(0, 10)
    ax_flow.set_ylim(0, 6)
    ax_flow.axis('off')
    
    # Pipeline steps
    steps = [
        (1, 3, "Raw RTL\nNews Data"),
        (3, 3, "OpenLID\nLanguage ID"),
        (5, 4.5, "Luxembourgish\nSentences"),
        (5, 1.5, "Other Languages\n(FR/DE/EN)"),
        (7.5, 4.5, "Research\nQuestions"),
    ]
    
    # Draw boxes and arrows
    for i, (x, y, text) in enumerate(steps):
        if i < 2:  # First two boxes (preprocessing)
            color = '#e6f3ff'
        elif i == 2:  # LU sentences
            color = '#66b3ff'
        elif i == 3:  # Other languages  
            color = '#ffcc99'
        else:  # Research questions
            color = '#99ff99'
            
        bbox = FancyBboxPatch((x-0.6, y-0.4), 1.2, 0.8, 
                             boxstyle="round,pad=0.1", 
                             facecolor=color, edgecolor='black', linewidth=1)
        ax_flow.add_patch(bbox)
        ax_flow.text(x, y, text, ha='center', va='center', fontsize=9, fontweight='bold')
    
    # Draw arrows
    arrows = [
        ((1.6, 3), (2.4, 3)),      # Raw data → OpenLID
        ((3.6, 3.2), (4.4, 4.3)),  # OpenLID → LU
        ((3.6, 2.8), (4.4, 1.7)),  # OpenLID → Others
        ((5.6, 4.5), (6.9, 4.5)),  # LU → RQ
    ]
    
    for (x1, y1), (x2, y2) in arrows:
        ax_flow.annotate('', xy=(x2, y2), xytext=(x1, y1),
                        arrowprops=dict(arrowstyle='->', lw=2, color='black'))
    
    # Add percentage labels on arrows
    if len(openlid_data['shares']) >= 3:
        lu_pct = openlid_data['shares'][0]  # Assuming LU is first
        other_pct = 100 - lu_pct
        ax_flow.text(4, 4.8, f'{lu_pct:.1f}%', ha='center', fontsize=9, fontweight='bold', color='blue')
        ax_flow.text(4, 1.2, f'{other_pct:.1f}%', ha='center', fontsize=9, fontweight='bold', color='orange')
    
    # === RESEARCH QUESTIONS BREAKDOWN ===
    
    # RQ1: Code-switching by section
    if 'rq1' in rq_metrics:
        rq1_data = rq_metrics['rq1']
        ax_rq1.bar(['Avg CMI'], [rq1_data['avg_metric']], color='#ff9999', alpha=0.7)
        ax_rq1.set_title('RQ1: Code-switching\nby News Section', fontsize=10, fontweight='bold')
        ax_rq1.set_ylabel('Code-mixing Index', fontsize=9)
        ax_rq1.text(0, rq1_data['avg_metric']/2, f"{rq1_data['avg_metric']:.1f}", 
                   ha='center', va='center', fontweight='bold')
        ax_rq1.set_ylim(0, max(rq1_data['avg_metric'] * 1.2, 1))
    else:
        ax_rq1.text(0.5, 0.5, 'RQ1\nNo Data', ha='center', va='center', transform=ax_rq1.transAxes)
        ax_rq1.set_title('RQ1: Code-switching\nby News Section', fontsize=10, fontweight='bold')
    
    # RQ3: Borrowing patterns
    if 'rq3' in rq_metrics:
        rq3_data = rq_metrics['rq3']
        ax_rq3.bar(['Patterns', 'Borrowings'], 
                  [rq3_data['total_patterns'], rq3_data['total_borrowings']], 
                  color=['#99ff99', '#ffcc99'], alpha=0.7)
        ax_rq3.set_title('RQ3: Pattern-based\nBorrowing Patterns', fontsize=10, fontweight='bold')
        ax_rq3.set_ylabel('Count', fontsize=9)
        for i, v in enumerate([rq3_data['total_patterns'], rq3_data['total_borrowings']]):
            ax_rq3.text(i, v/2, str(v), ha='center', va='center', fontweight='bold')
    else:
        ax_rq3.text(0.5, 0.5, 'RQ3\nNo Data', ha='center', va='center', transform=ax_rq3.transAxes)
        ax_rq3.set_title('RQ3: Pattern-based\nBorrowing Patterns', fontsize=10, fontweight='bold')
    
    # RQ3: Donor language distribution
    if 'rq3_donors' in rq_metrics:
        donors = list(rq_metrics['rq3_donors'].keys())[:3]  # Top 3
        values = [rq_metrics['rq3_donors'][d] for d in donors]
        colors_donors = ['#ff6b6b', '#4ecdc4', '#45b7d1']
        ax_rq3_donors.pie(values, labels=donors, colors=colors_donors, autopct='%1.1f%%', startangle=90)
        ax_rq3_donors.set_title('RQ3: Donor Languages\nfor Borrowing', fontsize=10, fontweight='bold')
    else:
        ax_rq3_donors.text(0.5, 0.5, 'RQ3 Donors\nNo Data', ha='center', va='center', transform=ax_rq3_donors.transAxes)
        ax_rq3_donors.set_title('RQ3: Donor Languages\nfor Borrowing', fontsize=10, fontweight='bold')
    
    # RQ4: Diachronic trends
    if 'rq4' in rq_metrics:
        rq4_data = rq_metrics['rq4']
        trend_color = '#99ff99' if rq4_data['trend'] == 'increasing' else '#ff9999'
        ax_rq4.bar(['Avg Borrow\nRate'], [rq4_data['avg_borrow_rate']], color=trend_color, alpha=0.7)
        ax_rq4.set_title('RQ4: Diachronic\nBorrowing Trends', fontsize=10, fontweight='bold')
        ax_rq4.set_ylabel('Borrow Rate (%)', fontsize=9)
        ax_rq4.text(0, rq4_data['avg_borrow_rate']/2, f"{rq4_data['avg_borrow_rate']:.2f}%", 
                   ha='center', va='center', fontweight='bold')
        # Add trend arrow
        arrow_y = rq4_data['avg_borrow_rate'] * 1.1
        if rq4_data['trend'] == 'increasing':
            ax_rq4.annotate('↗', xy=(0, arrow_y), ha='center', fontsize=16, color='green')
        else:
            ax_rq4.annotate('↘', xy=(0, arrow_y), ha='center', fontsize=16, color='red')
    else:
        ax_rq4.text(0.5, 0.5, 'RQ4\nNo Data', ha='center', va='center', transform=ax_rq4.transAxes)
        ax_rq4.set_title('RQ4: Diachronic\nBorrowing Trends', fontsize=10, fontweight='bold')
    
    # === SUMMARY STATISTICS ===
    ax_summary.axis('off')
    
    summary_text = "Pipeline Summary: "
    if openlid_data:
        lu_tokens = int(openlid_data['counts'][0]) if openlid_data['counts'] else 0
        summary_text += f"OpenLID identified {lu_tokens:,} Luxembourgish tokens ({openlid_data['shares'][0]:.1f}%) • "
    
    if 'rq1' in rq_metrics:
        summary_text += f"RQ1: {rq_metrics['rq1']['sections']} news sections analyzed • "
    
    if 'rq3' in rq_metrics:
        summary_text += f"RQ3: {rq_metrics['rq3']['total_patterns']} pattern-based patterns, {rq_metrics['rq3']['total_borrowings']} total borrowings • "
    
    if 'rq4' in rq_metrics:
        summary_text += f"RQ4: {rq_metrics['rq4']['time_periods']} time periods, borrowing trend: {rq_metrics['rq4']['trend']}"
    
    ax_summary.text(0.5, 0.5, summary_text, ha='center', va='center', 
                   transform=ax_summary.transAxes, fontsize=11, style='italic',
                   bbox=dict(boxstyle="round,pad=0.5", facecolor='#f0f0f0', alpha=0.8))
    
    plt.tight_layout()
    
    # Save the plot
    cfg = load_config()
    paths = cfg["paths"]
    output_dir = Path(paths["figures"])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    plt.savefig(output_dir / "pipeline_flow_dashboard.png", dpi=300, bbox_inches='tight')
    print(f"Pipeline flow dashboard saved to {output_dir / 'pipeline_flow_dashboard.png'}")
    
    plt.close()

def main():
    """Main function to create comprehensive pipeline visualization."""
    print("Creating comprehensive pipeline flow visualization...")
    create_pipeline_flow_dashboard()
    print("Pipeline flow visualization completed!")

if __name__ == "__main__":
    main()
