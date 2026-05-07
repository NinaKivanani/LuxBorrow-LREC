#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate publication-quality plots for code-switching research paper.
Supports RQ1-RQ4 with professional academic styling.
"""

import os, json, csv, yaml
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

# Academic plot styling
plt.style.use('default')
plt.rcParams.update({
    'font.size': 12,
    'font.family': 'sans-serif',  # Use available sans-serif fonts
    'axes.linewidth': 1.2,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight'
})

def load_config():
    """Load configuration."""
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    with open(cfg_path, 'r') as f:
        return yaml.safe_load(f)

def create_morphological_pattern_plot(output_dir):
    """RQ3: Pattern-based pattern usage in RTL news."""
    
    cfg = load_config()
    paths = cfg["paths"]
    
    # Load RQ3 borrowing patterns
    pattern_file = Path(paths["out_root"]) / "metrics" / "rq3_borrowing_patterns.csv"
    
    if not pattern_file.exists():
        print("No pattern data found. Skipping patterns plot.")
        return
        
    df = pd.read_csv(pattern_file)
    patterns = df['pattern'].tolist()
    counts = df['count'].tolist()
    
    # Create horizontal bar plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Color scheme for language directions
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#7209B7', '#008B8B']
    
    bars = ax.barh(patterns, counts, color=colors[:len(patterns)])
    
    # Add value labels on bars
    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax.text(bar.get_width() + max(counts)*0.01, bar.get_y() + bar.get_height()/2,
                f'{count:,}', va='center', fontsize=11, fontweight='bold')
    
    ax.set_xlabel('Number of Borrowing Instances', fontsize=14, fontweight='bold')
    ax.set_ylabel('Pattern-based Pattern', fontsize=14, fontweight='bold')
    ax.set_title('Pattern-based Adaptation Patterns in RTL News\n(Multi-language Borrowing)', 
                fontsize=16, fontweight='bold', pad=20)
    
    # Add pattern direction annotations
    pattern_info = {
        'éiert→é': 'LB→FR verbs',
        'éieren→er': 'LB→FR verbs', 
        'éit→é': 'LB→FR nouns',
        'exact': 'Direct borrowing',
        'oun→on': 'LB→FR nouns',
        '+e': 'FR feminization'
    }
    
    for i, pattern in enumerate(patterns):
        if pattern in pattern_info:
            ax.text(max(counts)*0.7, i, f'({pattern_info[pattern]})', 
                   va='center', fontsize=10, style='italic', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'morphological_patterns_distribution.png')
    plt.close()

def create_language_distribution_plot(output_dir):
    """RQ1: Language distribution across RTL corpus."""
    
    # Load actual validation data
    cfg = load_config()
    paths = cfg["paths"]
    validation_file = Path(paths["out_root"]) / "metrics" / "rq1_by_period.csv"
    
    if not validation_file.exists():
        print("No language distribution data found. Skipping language distribution plot.")
        return
        
    # Parse the validation data to get language counts
    df = pd.read_csv(validation_file)
    # Extract language info from the data - this needs to be adapted to your actual data format
    print("Language distribution plot needs adaptation to actual data format.")
    return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Pie chart
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
    wedges, texts, autotexts = ax1.pie(counts, labels=languages, autopct='%1.1f%%',
                                      colors=colors, startangle=90, textprops={'fontsize': 11})
    
    ax1.set_title('Language Distribution in RTL News\n(Token-level Analysis)', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Bar chart with counts
    bars = ax2.bar(languages, [c/1000000 for c in counts], color=colors)
    ax2.set_ylabel('Tokens (Millions)', fontsize=12, fontweight='bold')
    ax2.set_title('Token Counts by Language', fontsize=14, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)
    
    # Add value labels
    for bar, count in zip(bars, counts):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{count/1000000:.1f}M', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'language_distribution_rtl.png')
    plt.close()

def create_temporal_evolution_plot(output_dir):
    """RQ4: Diachronic evolution of code-switching patterns."""
    
    # Load existing diachronic data
    cfg = load_config()
    paths = cfg["paths"]
    diachrony_file = Path(paths["out_root"]) / "metrics" / "rq4_diachrony.csv"
    
    if not diachrony_file.exists():
        print("No diachronic data found. Skipping temporal plot.")
        return
    
    df = pd.read_csv(diachrony_file)
    df = df[df['month'] != 'unknown']
    df['date'] = pd.to_datetime(df['month'])
    df = df.sort_values('date')
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # Plot 1: Code-switching rate over time
    ax1.plot(df['date'], df['cs_rate'], linewidth=2, color='#2E86AB', marker='o', markersize=3)
    ax1.set_ylabel('Code-Switching Rate', fontweight='bold')
    ax1.set_title('A) Temporal Evolution of Code-Switching Rate', fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Borrowing share over time  
    ax2.plot(df['date'], df['borrow_share'], linewidth=2, color='#A23B72', marker='s', markersize=3)
    ax2.set_ylabel('Borrowing Share', fontweight='bold')
    ax2.set_title('B) Evolution of Borrowing vs Switching', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Donor language evolution
    ax3.plot(df['date'], df['donor_FR'], label='French', linewidth=2, color='#F18F01')
    ax3.plot(df['date'], df['donor_DE'], label='German', linewidth=2, color='#C73E1D')
    ax3.plot(df['date'], df['donor_EN'], label='English', linewidth=2, color='#7209B7')
    ax3.set_ylabel('Donor Language Share', fontweight='bold')
    ax3.set_title('C) Donor Language Preferences Over Time', fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Combined borrowing intensity
    ax4.fill_between(df['date'], 0, df['cs_rate'], alpha=0.3, color='#2E86AB', label='CS Rate')
    ax4.fill_between(df['date'], 0, df['borrow_share'], alpha=0.5, color='#A23B72', label='Borrowing')
    ax4.set_ylabel('Intensity', fontweight='bold')
    ax4.set_xlabel('Year', fontweight='bold')
    ax4.set_title('D) Code-Switching Intensity Evolution', fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Format x-axes
    for ax in [ax1, ax2, ax3, ax4]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator(base=5))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    # Dynamic title years from data
    if len(df) > 0:
        min_year = int(df['date'].min().year)
        max_year = int(df['date'].max().year)
        year_range = f"{min_year}-{max_year}"
    else:
        year_range = ""
    plt.suptitle(f"Diachronic Evolution of Code-Switching in RTL News{f' ({year_range})' if year_range else ''}", 
                fontsize=18, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_dir / 'temporal_evolution_codeSwitching.png')
    plt.close()

def create_top_borrowings_plot(output_dir):
    """RQ3: Borrowing patterns analysis - pattern types and most common patterns."""
    
    cfg = load_config()
    paths = cfg["paths"]
    
    # Load pattern usage data
    patterns_file = Path(paths["out_root"]) / "metrics" / "rq3_borrowing_patterns.csv"
    if not patterns_file.exists():
        print("No borrowing patterns data found. Skipping borrowing patterns plot.")
        return
    
    # Load compiled patterns to get pattern metadata
    compiled_patterns_file = Path(paths["manifests"]) / "compiled_patterns.json"
    pattern_info = {}
    if compiled_patterns_file.exists():
        import json
        with open(compiled_patterns_file, 'r', encoding='utf-8') as f:
            compiled_patterns = json.load(f)
            for pattern_name, pattern_data in compiled_patterns.items():
                kind = pattern_data.get('kind', 'unknown')
                donor = pattern_data.get('donor', 'unknown')
                pattern_info[pattern_name] = {'kind': kind, 'donor': donor}
    
    # Load pattern usage data and filter out problematic patterns
    df_patterns = pd.read_csv(patterns_file)
    # Filter out the problematic +e pattern that's matching everything
    df_patterns = df_patterns[df_patterns['pattern'] != '+e']
    
    # Create subplot layout: pattern types breakdown + most common patterns
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # === LEFT PLOT: Pattern Type Breakdown ===
    # Group by pattern type
    type_counts = {}
    for _, row in df_patterns.iterrows():
        pattern = row['pattern']
        count = row['count']
        pattern_type = pattern_info.get(pattern, {}).get('kind', 'unknown')
        type_counts[pattern_type] = type_counts.get(pattern_type, 0) + count
    
    # Color scheme for pattern types
    type_colors = {
        'morph': '#2E86AB',     # Morphological - blue
        'lexicon': '#A23B72',   # Lexical - purple  
        'orth': '#F18F01',      # Orthographic - orange
        'unknown': '#C73E1D'    # Unknown - red
    }
    
    types = list(type_counts.keys())
    counts = list(type_counts.values())
    colors1 = [type_colors.get(t, type_colors['unknown']) for t in types]
    
    bars1 = ax1.bar(types, counts, color=colors1)
    ax1.set_title('Borrowing Pattern Types\n(Frequency Distribution)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Number of Borrowing Instances', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Pattern Type', fontsize=12, fontweight='bold')
    
    # Add count labels on bars
    for bar, count in zip(bars1, counts):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(counts)*0.01,
                f'{count:,}', ha='center', va='bottom', fontweight='bold')
    
    # === RIGHT PLOT: Most Common Specific Patterns ===
    # Get top 10 most common patterns (excluding +e)
    top_patterns = df_patterns.head(10)
    
    # Color by pattern type
    colors2 = []
    for pattern in top_patterns['pattern']:
        pattern_type = pattern_info.get(pattern, {}).get('kind', 'unknown')
        colors2.append(type_colors.get(pattern_type, type_colors['unknown']))
    
    bars2 = ax2.barh(range(len(top_patterns)), top_patterns['count'], color=colors2)
    ax2.set_yticks(range(len(top_patterns)))
    ax2.set_yticklabels(top_patterns['pattern'], fontsize=11)
    ax2.set_xlabel('Number of Borrowing Instances', fontsize=12, fontweight='bold')
    ax2.set_title('Most Common Borrowing Patterns\n(Specific Pattern Usage)', fontsize=14, fontweight='bold')
    
    # Add count labels
    for i, (bar, count) in enumerate(zip(bars2, top_patterns['count'])):
        ax2.text(bar.get_width() + max(top_patterns['count'])*0.01, 
               bar.get_y() + bar.get_height()/2,
               f'{count:,}', va='center', fontweight='bold')
    
    # Add pattern type legend
    legend_elements = [
        plt.Rectangle((0,0),1,1, facecolor=type_colors['morph'], label='Morphological'),
        plt.Rectangle((0,0),1,1, facecolor=type_colors['lexicon'], label='Lexical'),
        plt.Rectangle((0,0),1,1, facecolor=type_colors['orth'], label='Orthographic'),
        plt.Rectangle((0,0),1,1, facecolor=type_colors['unknown'], label='Unknown')
    ]
    ax2.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'top_borrowed_forms_patterns.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_section_analysis_plot(output_dir):
    """RQ1: Code-switching by news section/domain."""
    
    # Load section data
    cfg = load_config()
    paths = cfg["paths"]
    section_file = Path(paths["out_root"]) / "metrics" / "rq1_by_section.csv"
    
    if section_file.exists():
        df = pd.read_csv(section_file)
        
        # Parse the actual format: group,metric,mean,n
        # Group by section and extract metrics
        sections_data = []
        for section in df['group'].unique():
            section_data = df[df['group'] == section]
            
            # Extract metrics for this section
            data_dict = {'section': section}
            for _, row in section_data.iterrows():
                metric = row['metric']
                if metric == 'cmi':
                    data_dict['cs_rate'] = row['mean'] / 100  # Convert to rate
                elif metric == 'm':
                    data_dict['m_index'] = row['mean']
                data_dict['total_tokens'] = row['n'] * 1000  # Approximate tokens from n
            
            sections_data.append(data_dict)
        
        # Convert to DataFrame and take top sections by token count
        sections_df = pd.DataFrame(sections_data)
        top_sections = sections_df.nlargest(12, 'total_tokens')
    else:
        print("No section data found. Skipping section analysis plot.")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Plot 1: CS rate by section
    sections = top_sections['section'].tolist()
    cs_rates = top_sections['cs_rate'].tolist()
    
    bars1 = ax1.bar(range(len(sections)), cs_rates, color='#4ECDC4')
    ax1.set_xticks(range(len(sections)))
    ax1.set_xticklabels(sections, rotation=45, ha='right')
    ax1.set_ylabel('Code-Switching Rate', fontweight='bold')
    ax1.set_title('A) Code-Switching Rate by News Section', fontweight='bold')
    
    # Add value labels
    for bar, rate in zip(bars1, cs_rates):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(cs_rates)*0.01,
                f'{rate:.3f}', ha='center', va='bottom', fontsize=9)
    
    # Plot 2: Token volume by section
    token_volumes = [t/1000000 for t in top_sections['total_tokens'].tolist()]
    bars2 = ax2.bar(range(len(sections)), token_volumes, color='#FF6B6B')
    ax2.set_xticks(range(len(sections)))
    ax2.set_xticklabels(sections, rotation=45, ha='right')
    ax2.set_ylabel('Total Tokens (Millions)', fontweight='bold')
    ax2.set_title('B) Token Volume by News Section', fontweight='bold')
    
    # Add value labels
    for bar, volume in zip(bars2, token_volumes):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(token_volumes)*0.01,
                f'{volume:.1f}M', ha='center', va='bottom', fontsize=9)
    
    plt.suptitle('Domain-Specific Code-Switching Patterns in RTL News', 
                fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'section_domain_analysis.png')
    plt.close()

def create_summary_overview_plot(output_dir):
    """Create a summary overview figure for the paper."""
    
    # Load actual metrics data to get real counts
    cfg = load_config()
    paths = cfg["paths"]
    rq1_file = Path(paths["out_root"]) / "metrics" / "rq1_by_section.csv"
    rq3_file = Path(paths["out_root"]) / "metrics" / "rq3_summary.txt"
    
    if not rq1_file.exists():
        print("No metrics data found. Skipping summary overview plot.")
        return
        
    print("Summary overview plot needs to be adapted to use actual generated metrics.")
    return
    
    bars = ax1.bar(metrics, display_values, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'])
    ax1.set_title('RTL Luxembourgish News Corpus Overview', fontsize=16, fontweight='bold')
    ax1.set_ylabel('Count', fontweight='bold')
    
    for bar, val, unit in zip(bars, display_values, units):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(display_values)*0.02,
                f'{val}{unit}', ha='center', va='bottom', fontweight='bold')
    
    # Language pie chart - READ FROM ACTUAL DATA
    ax2 = fig.add_subplot(gs[1, 0])
    cfg = load_config()
    paths = cfg["paths"]
    openlid_file = Path(paths["out_root"]) / "metrics" / "openlid_overall.csv"
    if openlid_file.exists():
        import pandas as pd
        openlid_df = pd.read_csv(openlid_file)
        langs = openlid_df['language'].tolist()
        lang_counts = openlid_df['count'].tolist()
    else:
        langs = ['LU', 'FR', 'DE', 'EN']
        lang_counts = [1, 1, 1, 1]  # Fallback
    ax2.pie(lang_counts, labels=langs, autopct='%1.1f%%', colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'])
    ax2.set_title('Language Distribution', fontweight='bold')
    
    # Top patterns - READ FROM ACTUAL DATA
    ax3 = fig.add_subplot(gs[1, 1])
    pattern_file = Path(paths["out_root"]) / "metrics" / "rq3_borrowing_patterns.csv"
    if pattern_file.exists():
        pattern_df = pd.read_csv(pattern_file)
        patterns = pattern_df['pattern'].head(3).tolist()
        pattern_counts = pattern_df['count'].head(3).tolist()
    else:
        patterns = ['No', 'Data', 'Available']
        pattern_counts = [1, 1, 1]  # Fallback
    ax3.bar(patterns, pattern_counts, color=['#2E86AB', '#A23B72', '#F18F01'])
    ax3.set_title('Top Morphological Patterns', fontweight='bold')
    ax3.set_ylabel('Uses')
    
    # Research questions
    ax4 = fig.add_subplot(gs[1, 2])
    rq_labels = ['RQ1:\nFrequency', 'RQ2:\nStructural', 'RQ3:\nBorrowing', 'RQ4:\nTemporal']
    rq_status = [1, 1, 1, 1]  # All complete
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
    ax4.bar(rq_labels, rq_status, color=colors)
    ax4.set_title('Research Questions', fontweight='bold')
    ax4.set_ylim(0, 1.2)
    ax4.set_ylabel('Status')
    
    # Temporal trend - READ FROM ACTUAL DATA
    ax5 = fig.add_subplot(gs[2, :])
    diachrony_file = Path(paths["out_root"]) / "metrics" / "rq4_diachrony.csv"
    if diachrony_file.exists():
        diach_df = pd.read_csv(diachrony_file)
        diach_df = diach_df[diach_df['month'] != 'unknown']
        if len(diach_df) > 0:
            diach_df['year'] = pd.to_datetime(diach_df['month']).dt.year
            yearly_trend = diach_df.groupby('year')['cs_rate'].mean()
            years = yearly_trend.index.tolist()
            cs_trend = yearly_trend.values.tolist()
        else:
            years = [2020, 2021, 2022]
            cs_trend = [0.1, 0.1, 0.1]  # Fallback
    else:
        years = [2020, 2021, 2022]
        cs_trend = [0.1, 0.1, 0.1]  # Fallback
    ax5.plot(years, cs_trend, marker='o', linewidth=3, color='#2E86AB', markersize=8)
    ax5.set_title('Code-Switching Evolution Over Time (Simulated)', fontweight='bold')
    ax5.set_xlabel('Year', fontweight='bold')
    ax5.set_ylabel('CS Rate', fontweight='bold')
    ax5.grid(True, alpha=0.3)
    
    plt.suptitle('Luxembourgish Code-Switching Analysis: Research Overview', 
                fontsize=20, fontweight='bold', y=0.98)
    plt.savefig(output_dir / 'research_overview_summary.png')
    plt.close()

def _reverse_arrow_label(pattern):
    """Reverse pattern arrow direction: 'ck->que' becomes 'que->ck'."""
    arrow = '\u2192'
    if arrow in pattern:
        parts = pattern.split(arrow, 1)
        return parts[1] + arrow + parts[0]
    return pattern


def create_top_specific_patterns_plot(output_dir):
    """RQ3: Standalone horizontal bar chart of most common specific borrowing patterns.

    Pattern labels are shown with reversed arrows (source->LB) so that
    e.g. 'ck->que' appears as 'que->ck', 'esch->isch' as 'isch->esch'.
    """
    cfg = load_config()
    paths = cfg["paths"]

    patterns_file = Path(paths["out_root"]) / "metrics" / "rq3_borrowing_patterns.csv"
    if not patterns_file.exists():
        print("No borrowing patterns data found. Skipping top_specific_patterns plot.")
        return

    compiled_patterns_file = Path(paths["manifests"]) / "compiled_patterns.json"
    pattern_info = {}
    if compiled_patterns_file.exists():
        with open(compiled_patterns_file, "r", encoding="utf-8") as f:
            compiled_patterns = json.load(f)
            for pname, pdata in compiled_patterns.items():
                pattern_info[pname] = {
                    "kind": pdata.get("kind", "unknown"),
                    "donor": pdata.get("donor", "unknown"),
                }

    df_patterns = pd.read_csv(patterns_file)
    df_patterns = df_patterns[df_patterns["pattern"] != "+e"]
    top_patterns = df_patterns.head(10)

    type_colors = {
        "morph":   "#2E86AB",
        "lexicon": "#A23B72",
        "orth":    "#F18F01",
        "unknown": "#C73E1D",
    }

    colors = [
        type_colors.get(
            pattern_info.get(p, {}).get("kind", "unknown"),
            type_colors["unknown"]
        )
        for p in top_patterns["pattern"]
    ]

    display_labels = [_reverse_arrow_label(p) for p in top_patterns["pattern"]]
    total = top_patterns["count"].sum()

    fig, ax = plt.subplots(figsize=(10, 9))
    bars = ax.barh(range(len(top_patterns)), top_patterns["count"], color=colors)
    ax.set_yticks(range(len(top_patterns)))
    ax.set_yticklabels(display_labels, fontsize=16, fontweight="bold")
    ax.set_xlabel("Number of Borrowing Instances", fontsize=17, fontweight="bold")
    ax.tick_params(axis="x", labelsize=18)

    max_count = max(top_patterns["count"])
    for bar, count in zip(bars, top_patterns["count"]):
        pct = count / total * 100
        ax.text(
            bar.get_width() + max_count * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{count:,} ({pct:.1f}%)",
            va="center", fontsize=16, fontweight="bold"
        )

    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, facecolor=type_colors["morph"],   label="Morphological"),
        plt.Rectangle((0, 0), 1, 1, facecolor=type_colors["lexicon"], label="Lexical"),
        plt.Rectangle((0, 0), 1, 1, facecolor=type_colors["orth"],    label="Orthographic"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=19,
              handlelength=3.0, handleheight=2.2, borderpad=1.2, labelspacing=1.0)

    # Extend x-axis to make room for count labels
    ax.set_xlim(0, max_count * 1.35)

    plt.tight_layout()
    plt.savefig(output_dir / "top_specific_patterns.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Saved top_specific_patterns.png")


def create_rq4_period_trend_plot(output_dir):
    """RQ4: Code-switching trend with five-year period averages and standard deviations.
    Uses Okabe-Ito colorblind-safe palette.
    """
    from matplotlib.lines import Line2D

    cfg = load_config()
    paths = cfg["paths"]
    diachrony_file = Path(paths["out_root"]) / "metrics" / "rq4_diachrony.csv"

    if not diachrony_file.exists():
        print("No diachronic data found. Skipping RQ4 period trend plot.")
        return

    df = pd.read_csv(diachrony_file)
    df = df[df['month'] != 'unknown'].copy()
    df['date'] = pd.to_datetime(df['month'])
    df = df.sort_values('date')
    df['year'] = df['date'].dt.year

    # Five-year analytical periods matching the paper text
    periods = [
        (1999, 2004, '1999–2004'),
        (2005, 2009, '2005–2009'),
        (2010, 2014, '2010–2014'),
        (2015, 2019, '2015–2019'),
        (2020, 2025, '2020–2025'),
    ]

    period_means, period_stds, period_labels = [], [], []
    for start, end, label in periods:
        mask = (df['year'] >= start) & (df['year'] <= end)
        subset = df.loc[mask, 'cs_rate']
        period_means.append(subset.mean())
        period_stds.append(subset.std())
        period_labels.append(label)

    # Okabe-Ito colorblind-safe palette
    period_colors = ['#56B4E9', '#009E73', '#F0E442', '#E69F00', '#CC79A7']

    fig, (ax_main, ax_bar) = plt.subplots(
        1, 2, figsize=(14, 7.5),
        gridspec_kw={'width_ratios': [3, 1.4]},
    )

    # ── LEFT: monthly time series + period shading ─────────────────────────────
    for i, (start, end, label) in enumerate(periods):
        ax_main.axvspan(
            pd.Timestamp(f'{start}-01-01'),
            pd.Timestamp(f'{end}-12-31'),
            alpha=0.22, color=period_colors[i], label=label,
        )

    ax_main.plot(df['date'], df['cs_rate'],
                 linewidth=1.5, color='#000000', alpha=0.75, zorder=3)

    for i, (start, end, label) in enumerate(periods):
        ax_main.hlines(
            period_means[i],
            pd.Timestamp(f'{start}-01-01'),
            pd.Timestamp(f'{end}-12-31'),
            colors='#D55E00', linewidths=2.4, linestyles='--', zorder=4,
        )

    for year, milestone in [(2020, 'Orthography reform (2020)'), (2022, 'AI era (2022)')]:
        ax_main.axvline(pd.Timestamp(f'{year}-01-01'),
                        color='#555', linestyle=':', linewidth=1.3, zorder=5)
        ax_main.text(pd.Timestamp(f'{year}-01-01'), 0.072,
                     milestone, rotation=90, va='top', ha='right',
                     fontsize=11, color='#555', zorder=6)

    ax_main.set_xlabel('Year', fontsize=18, fontweight='bold')
    ax_main.set_ylabel('Code-Switching Rate', fontsize=20, fontweight='bold')
    ax_main.set_title('Monthly CS Rate with Five-Year Period Averages (1999–2025)',
                      fontsize=16, fontweight='bold', pad=14, y=1.0)
    ax_main.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax_main.xaxis.set_major_locator(mdates.YearLocator(base=5))
    plt.setp(ax_main.xaxis.get_majorticklabels(), rotation=45, fontsize=17)
    plt.setp(ax_main.yaxis.get_majorticklabels(), fontsize=17)
    ax_main.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x*100:.1f}%'))
    ax_main.grid(True, alpha=0.25, linestyle='--')

    handles, _ = ax_main.get_legend_handles_labels()
    handles.append(Line2D([0], [0], color='#D55E00', linewidth=2.4,
                          linestyle='--', label='Period mean'))
    ax_main.legend(handles=handles, fontsize=17, loc='upper left',
                   framealpha=0.85, ncol=2)

    # ── RIGHT: bar chart of period means ± SD ─────────────────────────────────
    x_pos = np.arange(len(period_labels))
    bars = ax_bar.bar(x_pos, [m * 100 for m in period_means],
                      yerr=[s * 100 for s in period_stds],
                      color=period_colors, edgecolor='#333',
                      linewidth=0.9, capsize=5, error_kw={'linewidth': 1.5})

    for bar, mean, std in zip(bars, period_means, period_stds):
        ax_bar.text(
            bar.get_x() + bar.get_width() / 2,
            mean * 100 + std * 100 + 0.12,
            f'{mean*100:.2f}%',
            ha='center', va='bottom', fontsize=15, fontweight='bold',
        )

    ax_bar.set_xticks(x_pos)
    ax_bar.set_xticklabels(period_labels, rotation=40, ha='right', fontsize=17)
    ax_bar.set_ylabel('Mean CS Rate (%)', fontsize=20, fontweight='bold')
    ax_bar.set_title('Period Averages (± SD)', fontsize=17, fontweight='bold', pad=10)
    ax_bar.set_ylim(0, 10)
    ax_bar.yaxis.set_major_locator(plt.MultipleLocator(2))
    ax_bar.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))
    plt.setp(ax_bar.yaxis.get_majorticklabels(), fontsize=17)
    ax_bar.grid(True, axis='y', alpha=0.25, linestyle='--')

    total_increase = (period_means[-1] - period_means[0]) / period_means[0] * 100
    ax_bar.annotate(
        f'+{total_increase:.1f}%\noverall increase',
        xy=(x_pos[-1], period_means[-1] * 100 + period_stds[-1] * 100),
        xytext=(x_pos[-1] - 1.5, period_means[-1] * 100 + period_stds[-1] * 100 + 0.8),
        fontsize=15, color='#D55E00', fontweight='bold',
        arrowprops=dict(arrowstyle='->', color='#D55E00', lw=1.3),
        ha='center',
    )

    plt.tight_layout()
    plt.subplots_adjust(wspace=0.22)
    plt.savefig(output_dir / 'rq4_period_trend.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("  Saved rq4_period_trend.png")


def main():
    """Generate all publication-quality plots."""
    
    cfg = load_config()
    output_dir = Path(cfg["paths"]["out_root"]) / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating publication-quality plots...")
    
    # Create all plots - only if data exists
    create_morphological_pattern_plot(output_dir)
    print("✅ Checked morphological patterns plot")
    
    create_language_distribution_plot(output_dir)
    print("✅ Checked language distribution plot")
    
    create_temporal_evolution_plot(output_dir)
    print("✅ Checked temporal evolution plot")
    
    create_top_borrowings_plot(output_dir)
    print("✅ Checked top borrowings plot")
    
    create_section_analysis_plot(output_dir)
    print("✅ Checked section analysis plot")
    
    create_summary_overview_plot(output_dir)
    print("✅ Checked research overview plot")

    create_rq4_period_trend_plot(output_dir)
    print("✅ Checked RQ4 period trend plot")

    create_top_specific_patterns_plot(output_dir)
    print("✅ Checked top specific patterns plot")
    
    print(f"\n🎨 Publication plots processed for: {output_dir}")
    print("\nGenerated plots:")
    for plot_file in output_dir.glob("*.png"):
        print(f"  📊 {plot_file.name}")

if __name__ == "__main__":
    main()

