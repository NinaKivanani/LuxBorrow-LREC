# LuxBorrow: From Pompier to Pompjee, Tracing Borrowing in Luxembourgish

**LREC 2026** — Nina Hosseini-Kivanani & Fred Philippy  
University of Luxembourg / Radio Télévision Luxembourg (RTL)

> Code for preprocessing, language identification, and borrowing detection.  
> Dataset access: `ai@rtl.lu` · GitHub: [github.com/NinaKivanani/LuxBorrow-LREC](https://github.com/NinaKivanani/LuxBorrow-LREC)

---

## Overview

**LuxBorrow** is a borrowing-first analysis of Luxembourgish (LB) news (1999–2025) built on  
259,305 RTL articles and 43.7 million tokens. The pipeline combines:

1. **Loanword detection** using the LOD dictionary, morphological/orthographic adaptation patterns, and human annotation
2. **Sentence-level LID** (OpenLID / FastText) as a context gate
3. **Token-level borrowing detection** using lemmatization, a curated loanword registry, and compiled rules
4. **Code-mixing metrics** (CMI, Shannon entropy, M-Index) with diachronic analysis

Key findings: LB remains the matrix language throughout, 77.1% of articles contain at least  
one donor language, morphological adaptation dominates (63.8%), and French is the overwhelming  
donor for adapted borrowings (~97–99% per period).

---

## Repository Structure

```
LuxBorrow-LREC/
├── loanwords/                           # Loanword detection pipeline
│   ├── find_loanwords.py                ← main loanword detection script
│   ├── utils.py                         ← helper functions
│   └── data/                            ← input data for loanword detection
│       ├── new_lod-art.xml              ← LOD dictionary export
│       ├── loans_fr_to_de.txt           ← cross-language borrowing lists
│       ├── loans_fr_to_en.txt
│       ├── loans_en_to_de.txt
│       ├── loans_en_to_fr.txt
│       ├── german_terms_from_high_german.txt
│       ├── german_terms_from_middle_high_german.txt
│       ├── manual_adds.txt              ← human annotation additions
│       └── manual_removals.txt          ← human annotation removals
├── scripts/                             # Corpus analysis pipeline
│   ├── 00_create_clean_json.py          ← data cleaning and deduplication
│   ├── 00b_convert_pairs_csv_to_json.py ← convert synonym pairs CSV → JSON
│   ├── 01_freeze_manifest.py            ← freeze data manifest with hashes
│   ├── 02_compile_patterns.py           ← compile morphological patterns
│   ├── 03_preprocess_tokenize_rtljson.py← tokenize RTL JSON articles
│   ├── 03_preprocess_clean_jsonl.py     ← clean JSONL preprocessing
│   ├── 04_lid_tokenlevel_llm_optimized.py ← sentence + token-level LID
│   ├── 05_text_normalize.py             ← text normalization
│   ├── 06_validate_freeze.py            ← validate against frozen manifest
│   ├── 07_label_borrowing.py            ← token borrowing labeling (RQ3)
│   ├── 08_metrics_rq.py                 ← CMI/entropy/M-index (RQ1 + RQ4)
│   ├── 08b_openlid_metrics.py           ← OpenLID code-switching metrics (RQ1 + RQ2)
│   ├── 11_rq3_borrowing_stats.py        ← borrowing stats by donor/pattern (RQ3)
│   ├── 12_synonym_preference_timeseries.py ← loan–native synonym competition (RQ4)
│   ├── morph_gates.py                   ← morphological gate utilities
│   ├── pattern_runtime.py               ← compiled pattern index lookup
│   └── run_all.py                       ← master pipeline runner
├── config/
│   └── config.yaml                      ← all paths and plot settings
├── resources/
│   ├── lux_loanwords.ud.json            ← loanword registry (7,796 entries)
│   ├── patterns_with_examples.json      ← compiled morphological patterns
│   ├── loanword_synonyms_unique.json    ← loanword–native synonym pairs
│   └── loanword_synonym_pairs.csv
├── env.yaml                             ← conda environment
├── requirements.txt                     ← pip dependencies
└── LICENSE                              ← Apache-2.0
```

---

## Pipeline Scripts — Mapped to Paper Sections & RQs

### Loanword Detection (`loanwords/`)

| Script | Section | Description |
|--------|---------|-------------|
| `find_loanwords.py` | §3.3 | Detects loanwords from LOD dictionary using morphological/orthographic patterns, parallel borrowing resolution, shared inheritance filtering, and manual annotation |
| `utils.py` | §3.3 | Helper functions for loanword detection |

### Corpus Analysis (`scripts/`)

| Script | Section / RQ | Description |
|--------|-------------|-------------|
| `00_create_clean_json.py` | §3.1 | Raw RTL JSON cleaning and deduplication |
| `00b_convert_pairs_csv_to_json.py` | §3.3 | One-time conversion of synonym pairs CSV to JSON (output already in `resources/`) |
| `01_freeze_manifest.py` | Reproducibility | Freeze data manifest with checksums |
| `02_compile_patterns.py` | §3.3 | Compile morphological/orthographic adaptation patterns from loanword registry |
| `03_preprocess_tokenize_rtljson.py` | §3.2 | Tokenize RTL JSON articles |
| `03_preprocess_clean_jsonl.py` | §3.2 | Clean JSONL format preprocessing |
| `04_lid_tokenlevel_llm_optimized.py` | §3.2 | Sentence-level LID gate (OpenLID, length-adaptive threshold) + token-level borrowing detection |
| `05_text_normalize.py` | §3.2 | Text normalization for orthographic variants |
| `06_validate_freeze.py` | Reproducibility | Validate pipeline outputs against frozen manifest |
| `07_label_borrowing.py` | §3.3 / **RQ3** | Label tokens as Native / FR_LOAN / DE_LOAN / EN_LOAN |
| `08_metrics_rq.py` | **RQ1 + RQ4** | Compute CMI, Shannon entropy, M-Index by domain and temporal period |
| `08b_openlid_metrics.py` | **RQ1 + RQ2** | OpenLID-based code-switching metrics |
| `11_rq3_borrowing_stats.py` | **RQ3** | Borrowing frequency by donor language and adaptation pattern |
| `12_synonym_preference_timeseries.py` | **RQ4** | Diachronic loan–native synonym competition time series |
| `morph_gates.py` | §3.3 | Morphological gate helper (utility) |
| `pattern_runtime.py` | §3.3 | Compiled pattern index for constant-time lookup (utility) |
| `run_all.py` | — | Master runner; execute all or selected steps |

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
| `pyyaml` | `>=6.0` | Config parsing |
| `pandas` | `>=2.0` | Data manipulation and metrics aggregation |
| `matplotlib` | `>=3.8` | Visualization |
| `numpy` | `>=1.26` | Numerical operations |
| `tqdm` | `>=4.66` | Progress bars |

### Optional Dependencies

| Package | Purpose |
|---------|---------|
| `blingfire>=0.1.8` | Fast tokenization on HPC/SLURM (falls back to Python if missing) |
| `langdetect>=1.0.9` | LLM-assisted LID for uncertain cases |
| `openai>=1.40.0` | LLM backup LID (`USE_LID_LLM=1` only; requires `OPENAI_API_KEY`) |

---

## Quick Start

### 1. Set up environment

```bash
conda env create -f env.yaml
conda activate all_project
```

### 2. Place your data

Put RTL JSON articles in `data/rtl_raw/` (access via `ai@rtl.lu`).  
Edit `config/config.yaml` if your paths differ.

### 3. Run the full pipeline

```bash
python scripts/run_all.py
```

### 4. Run selectively

```bash
# Only preprocessing + LID
python scripts/run_all.py --only freeze,compile,prep,lid

# From borrowing labeling onwards
python scripts/run_all.py --from label

# Skip synonym steps
python scripts/run_all.py --skip syn
```

### 5. Available step names

| Step | Script |
|------|--------|
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

### 6. Environment variables

| Variable | Default | Effect |
|----------|---------|--------|
| `CONFIG_PATH` | `config/config.yaml` | Path to config file |
| `USE_LID_LLM` | `0` | `1` to enable OpenAI LLM backup for uncertain LID cases |

---

## Resources

| File | Description |
|------|-------------|
| `resources/lux_loanwords.ud.json` | Loanword registry: ~7,796 entries with donor tags (FR/DE/EN) and adaptation patterns, derived from LOD |
| `resources/patterns_with_examples.json` | Compiled morphological/orthographic rules (e.g., `-er → -éieren`, `on → oun`, `eur → er`) |
| `resources/loanword_synonyms_unique.json` | Loanword–native LB synonym pairs for RQ4 |
| `loanwords/output/lux_loanwords.json` | Raw loanword detection output (input to `resources/lux_loanwords.ud.json`) |

---

## Data Availability

The full RTL news corpus (259,305 articles, 1999–2025) **cannot be redistributed** due to  
copyright and database rights of RTL Luxembourg. We release:

- All pipeline scripts and loanword detection code
- Pattern lists and loanword registry (derived artefacts)
- Cross-language borrowing lists used for parallel borrowing resolution

To request access to the underlying RTL corpus, contact **ai@rtl.lu**.

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
