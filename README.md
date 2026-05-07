# LuxBorrow: From Pompier to Pompjee, Tracing Borrowing in Luxembourgish

**LREC-COLING 2026** — Nina Hosseini-Kivanani & Fred Philippy  
University of Luxembourg / Radio Télévision Luxembourg (RTL)

> Code for preprocessing, language identification, borrowing detection, and reproduction  
> of all figures and tables in the paper.  
> Dataset access: `ai@rtl.lu` · GitHub: [github.com/NinaKivanani/LuxBorrow-LREC](https://github.com/NinaKivanani/LuxBorrow-LREC)

---

## Overview

**LuxBorrow** is a borrowing-first analysis of Luxembourgish (LB) news (1999–2025) built on  
259,305 RTL articles and 43.7 million tokens. The pipeline combines:

1. **Sentence-level LID** (OpenLID / FastText) as a context gate  
2. **Token-level borrowing detection** using lemmatization, a curated loanword registry, and  
   compiled morphological/orthographic rules  
3. **Code-mixing metrics** (CMI, Shannon entropy, M-Index) with diachronic analysis

Key findings: LB remains the matrix language throughout, 77.1% of articles contain at least  
one donor language, morphological adaptation dominates (63.8%), and French is the overwhelming  
donor for adapted borrowings (~97–99% per period).

---

## Repository Structure

```
LuxBorrow_LREC2026/
├── scripts/                   # Full analysis pipeline (23 scripts)
│   ├── 00_create_clean_json.py
│   ├── 00b_convert_pairs_csv_to_json.py
│   ├── 01_freeze_manifest.py
│   ├── 02_compile_patterns.py
│   ├── 03_preprocess_tokenize_rtljson.py
│   ├── 03_preprocess_clean_jsonl.py
│   ├── 04_lid_tokenlevel_llm_optimized.py
│   ├── 05_text_normalize.py
│   ├── 06_validate_freeze.py
│   ├── 07_label_borrowing.py
│   ├── 08_metrics_rq.py
│   ├── 08b_openlid_metrics.py
│   ├── 09_make_plots.py
│   ├── 09b_openlid_plots.py
│   ├── 10_make_rq1_tables.py
│   ├── 11_rq3_borrowing_stats.py
│   ├── 12_synonym_preference_timeseries.py
│   ├── 13_plot_synonym_trends.py
│   ├── 14_publication_plots.py          ← paper figures (Fig 1, 4)
│   ├── 15_pipeline_flow_visualization.py ← Fig 2 (Methodology diagram)
│   ├── morph_gates.py                   ← morphological gate utilities
│   ├── pattern_runtime.py               ← compiled pattern lookup
│   └── run_all.py                       ← master runner
├── config/
│   └── config.yaml                      ← all paths and plot settings
├── resources/
│   ├── lux_loanwords.ud.json            ← loanword registry (7,796 entries)
│   ├── patterns_with_examples.json      ← compiled morphological patterns
│   ├── loanword_synonyms_unique.json    ← loanword–native synonym pairs
│   └── loanword_synonym_pairs.csv
├── Figures/                             ← output: paper figures (PDF/PNG)
├── Tables/                              ← output: LaTeX tables
├── data/
│   ├── rtl_raw/                         ← (not distributed) RTL article JSON
│   └── processed/v1/                    ← pipeline outputs
└── README.md
```

---

## Pipeline Scripts — Mapped to Paper Sections & RQs

| Script | Section / RQ | Description |
|--------|-------------|-------------|
| `00_create_clean_json.py` | §3.1 Dataset | Initial JSON cleaning and deduplication |
| `00b_convert_pairs_csv_to_json.py` | §3.3 Loanword | Convert loanword–synonym CSV pairs to JSON |
| `01_freeze_manifest.py` | Reproducibility | Freeze data manifest with hashes |
| `02_compile_patterns.py` | §3.3 Loanword | Compile morphological/orthographic adaptation patterns from loanword registry |
| `03_preprocess_tokenize_rtljson.py` | §3.2 LID | Tokenize RTL JSON articles |
| `03_preprocess_clean_jsonl.py` | §3.2 LID | Clean JSONL format preprocessing |
| `04_lid_tokenlevel_llm_optimized.py` | §3.2 LID | Sentence-level LID gate + token-level borrowing detection (OpenLID + length-adaptive threshold) |
| `05_text_normalize.py` | §3.2 LID | Text normalization (orthographic variants) |
| `06_validate_freeze.py` | Reproducibility | Validate outputs against frozen manifest |
| `07_label_borrowing.py` | §3.3 / **RQ3** | Label tokens as Native / FR_LOAN / DE_LOAN / EN_LOAN using lexicon + morphological rules |
| `08_metrics_rq.py` | **RQ1 + RQ4** | Compute CMI, Shannon entropy, M-Index by domain and temporal period → Table 1, Fig 4 |
| `08b_openlid_metrics.py` | **RQ1 + RQ2** | OpenLID-based code-switching metrics → Table 2 |
| `09_make_plots.py` | **RQ1–RQ4** | Core visualization: domain/period comparisons |
| `09b_openlid_plots.py` | **RQ1 + RQ2** | OpenLID diachrony and language distribution plots |
| `10_make_rq1_tables.py` | **RQ1** | Generate LaTeX Table 1 (CMI/entropy/M-index by domain+period) |
| `11_rq3_borrowing_stats.py` | **RQ3** | Borrowing frequency by donor language, top patterns, adaptation type distribution → Fig 3 |
| `12_synonym_preference_timeseries.py` | **RQ4** | Diachronic loan–native synonym competition time series |
| `13_plot_synonym_trends.py` | **RQ4** | Visualize synonym competition trends |
| `14_publication_plots.py` | **All RQs** | Publication-quality figures: Fig 1 (temporal distribution), Fig 4 (diachronic CS evolution) |
| `15_pipeline_flow_visualization.py` | §3 | Pipeline flow diagram → Fig 2 (Methodology.pdf) |
| `morph_gates.py` | §3.3 | Morphological gate helper (utility) |
| `pattern_runtime.py` | §3.3 | Compiled pattern index for constant-time lookup (utility) |
| `run_all.py` | — | Master runner; execute all or selected steps |

---

## Paper Figures

| Figure | File (in `Figures/`) | Generating Script |
|--------|----------------------|-------------------|
| Fig 1 — Temporal distribution of RTL articles | `temporal_distribution_main.png` | `14_publication_plots.py` |
| Fig 2 — Methodology pipeline | `Methodology.pdf` | `15_pipeline_flow_visualization.py` |
| Fig 3 — Borrowing pattern distribution | `top_specific_patterns.png` | `11_rq3_borrowing_stats.py` + `09_make_plots.py` |
| Fig 4 — Diachronic CS evolution (RQ4) | `rq4_period_trend.png` | `14_publication_plots.py` |

---

## Requirements

### Python

**Python 3.10–3.11** (3.12 not tested)

Install via conda (recommended):

```bash
conda env create -f env.yaml
conda activate all_project
```

Or via pip:

```bash
pip install -r requirements.txt
```

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `python` | `>=3.10, <3.12` | Runtime |
| `pyyaml` | `>=6.0` | Config parsing |
| `pandas` | `>=2.0` | Data manipulation, metrics aggregation |
| `matplotlib` | `>=3.8` | All visualizations (300 DPI publication figures) |
| `numpy` | `>=1.26` | Numerical operations |
| `tqdm` | `>=4.66` | Progress bars |

### Optional Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `blingfire` | `>=0.1.8` | Fast tokenization on SLURM/HPC (fallback to Python if missing) |
| `langdetect` | `>=1.0.9` | LLM-assisted LID for uncertain cases |
| `openai` | `>=1.40.0` | LLM backup LID (`USE_LID_LLM=1` only; requires `OPENAI_API_KEY`) |

---

## Quick Start

### 1. Set up environment

```bash
cd LuxBorrow_LREC2026/
conda env create -f env.yaml   # or: pip install -r requirements.txt
conda activate all_project
```

### 2. Place your data

Put your RTL JSON articles in `data/rtl_raw/` (access via `ai@rtl.lu`).  
Edit `config/config.yaml` if your paths differ.

### 3. Run the full pipeline

```bash
python scripts/run_all.py
```

### 4. Run selectively (by step name)

```bash
# Only preprocessing + LID
python scripts/run_all.py --only freeze,compile,prep,lid

# From borrowing labeling onwards
python scripts/run_all.py --from label

# Skip synonym steps
python scripts/run_all.py --skip syn

# Only generate publication figures
python scripts/run_all.py --only pub_plots
```

### 5. Available step names

| Step name | Script |
|-----------|--------|
| `freeze` | `01_freeze_manifest.py` |
| `compile` | `02_compile_patterns.py` |
| `prep` | `03_preprocess_tokenize_rtljson.py` |
| `lid` | `04_lid_tokenlevel_llm_optimized.py` |
| `tn` | `05_text_normalize.py` |
| `validate` | `06_validate_freeze.py` |
| `label` | `07_label_borrowing.py` |
| `metrics` | `08_metrics_rq.py` |
| `openlid` | `08b_openlid_metrics.py` |
| `rq3` | `11_rq3_borrowing_stats.py` |
| `syn` | `12_synonym_preference_timeseries.py` |
| `tables` | `10_make_rq1_tables.py` |
| `plots` | `09_make_plots.py` |
| `openlid_plots` | `09b_openlid_plots.py` |
| `pub_plots` | `14_publication_plots.py` |

### 6. Environment variables

| Variable | Default | Effect |
|----------|---------|--------|
| `CONFIG_PATH` | `config/config.yaml` | Path to config file |
| `RUN_PLOTS` | `1` | `0` to skip all figure generation |
| `RUN_TABLES` | `1` | `0` to skip LaTeX table generation |
| `USE_LID_LLM` | `0` | `1` to enable OpenAI LLM backup for uncertain LID cases |

---

## Configuration (`config/config.yaml`)

All paths and plot settings are centralized in `config/config.yaml`.  
Key entries:

```yaml
paths:
  raw_dir:          "data/rtl_raw"          # Input: raw RTL JSON
  out_root:         "data/processed/v1"     # All pipeline outputs
  borrowing_index:  "data/processed/v1/labels/borrowing_switch.jsonl"
  pattern_file:     "resources/patterns_with_examples.json"
  loanwords_json:   "resources/lux_loanwords.ud.json"
  loan_syn_pairs:   "resources/loanword_synonyms_unique.json"

plots:
  reference_lines:
    - month: "2020-01"
      label: "Orthography reform (2020)"
    - month: "2022-01"
      label: "AI era (2022)"
```

---

## Resources

| File | Description |
|------|-------------|
| `resources/lux_loanwords.ud.json` | Loanword registry: ~7,796 entries with donor tags (FR/DE/EN) and adaptation patterns, derived from LOD (Lëtzebuerger Online Dictionnaire) |
| `resources/patterns_with_examples.json` | Compiled morphological and orthographic adaptation rules (e.g., `-er → -éieren`, `on → oun`, `eur → er`) with corpus examples |
| `resources/loanword_synonyms_unique.json` | Loanword–native LB synonym pairs for RQ4 synonym competition analysis |
| `resources/loanword_synonym_pairs.csv` | Same pairs in CSV format |

---

## Data Availability

The full RTL news corpus (259,305 articles, 1999–2025) **cannot be redistributed** due to  
copyright and database rights of RTL Luxembourg. We release:

- All scripts and pipeline code  
- Pattern lists and loanword registry (derived artefacts)  
- Aggregate statistics and figures from the paper  
- Small illustrative examples

To request access to the underlying RTL corpus, contact **ai@rtl.lu**.

Data were processed on **MeluXina HPC** (EuroHPC, LuxProvide) under a University of Luxembourg  
research allocation, in compliance with GDPR and applicable EU text/data-mining provisions for  
non-commercial scientific research.

---

## Citation

```bibtex
@inproceedings{hosseini-kivanani-philippy-2026-luxborrow,
  title     = {{LuxBorrow}: From Pompier to Pompjee, Tracing Borrowing in {L}uxembourgish},
  author    = {Hosseini-Kivanani, Nina and Philippy, Fred},
  booktitle = {Proceedings of LREC 2026},
  year      = {2026},
  address   = {Palma de Mallorca, Spain},
}
```

---

## Acknowledgements

We thank **RTL Luxembourg** and **Tom Weber** for providing access to the news archive.  
This work was supported by:
- **ENEOLI COST Action (CA22126)** — European Cooperation in Science and Technology  
- **FNR LuxVoice project** (reference 19205922)
