#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, subprocess, argparse
from pathlib import Path
import yaml

# Optional toggles (you can also use --only/--skip CLI flags)
RUN_PLOTS   = os.environ.get("RUN_PLOTS", "1") == "1"   # figures for RQ4
RUN_TABLES  = os.environ.get("RUN_TABLES","1") == "1"   # LaTeX tables for RQ1
USE_LID_LLM = os.environ.get("USE_LID_LLM","0") == "1"  # enable LLM backup for uncertain OpenLID cases
CONFIG_PATH = os.environ.get("CONFIG_PATH", "config/config.yaml")

PY = sys.executable  # ensure we use the active interpreter
PYU = [PY, "-u"]     # unbuffered logs

# If you want BlingFire to be mandatory even outside SLURM, set this to True
FORCE_BLINGFIRE_CLI = False

prep_cmd = [*PYU, "scripts/03_preprocess_tokenize_rtljson.py", "--config", CONFIG_PATH]
if FORCE_BLINGFIRE_CLI:
    prep_cmd.append("--require-blingfire")

lid_cmd = [*PYU, "scripts/04_lid_tokenlevel_llm_optimized.py", "--batch-size", "1000"]
if USE_LID_LLM:
    lid_cmd.insert(3, "--use-llm")  # after script path

def _syn_trend_pairs_args(config_path: str):
    cfg = None
    try:
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    except Exception:
        return []
    if not cfg or "paths" not in cfg:
        # config is minimal; still try to read pairs at top-level
        pairs = cfg.get("syn_trend_pairs", []) if isinstance(cfg, dict) else []
    else:
        pairs = cfg.get("syn_trend_pairs", [])
    args = []
    for item in pairs:
        loan = str(item.get("loan", "")).strip()
        syn  = str(item.get("syn", "")).strip()
        if loan and syn:
            args.extend([loan, syn])
    return args

STEPS = [
    ("freeze",   [*PYU, "scripts/01_freeze_manifest.py"]),
    ("compile",  [*PYU, "scripts/02_compile_patterns.py"]),
    ("prep",      prep_cmd),
    ("lid",       lid_cmd),
    ("tn",       [*PYU, "scripts/05_text_normalize.py"]),
    ("validate", [*PYU, "scripts/06_validate_freeze.py"]),
    ("label",    [*PYU, "scripts/07_label_borrowing.py"]),
    ("metrics",  [*PYU, "scripts/08_metrics_rq.py"]),           # RQ1 + RQ4 CSVs
    ("openlid",  [*PYU, "scripts/08b_openlid_metrics.py"]),     # OpenLID code-switching metrics
    ("rq3",      [*PYU, "scripts/11_rq3_borrowing_stats.py"]),  # RQ3 donor/top-forms
    ("syn",      [*PYU, "scripts/12_synonym_preference_timeseries.py"]),  # loan vs synonym
]

if RUN_TABLES:
    STEPS.append(("tables", [*PYU, "scripts/10_make_rq1_tables.py"]))  # optional LaTeX tables
if RUN_PLOTS:
    STEPS.append(("plots",  [*PYU, "scripts/09_make_plots.py"]))       # optional figures
    STEPS.append(("openlid_plots", [*PYU, "scripts/09b_openlid_plots.py"]))  # OpenLID code-switching plots
    # Skip syn_trends - only include if pairs are automatically discovered from data
    STEPS.append(("pub_plots", [*PYU, "scripts/14_publication_plots.py"]))     # publication figures

def run(cmd):
    env = os.environ.copy()
    env.setdefault("CONFIG_PATH", CONFIG_PATH)  # ensure every sub-step sees it
    print(">>", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, env=env)
    if r.returncode != 0:
        print(f"[ERROR] ({r.returncode}) {' '.join(cmd)}", file=sys.stderr, flush=True)
        sys.exit(r.returncode)

def main():
    names = [n for n,_ in STEPS]
    ap = argparse.ArgumentParser("Run LU CS pipeline selectively")
    ap.add_argument("--only", help=f"comma-separated subset of: {','.join(names)}")
    ap.add_argument("--skip", help="comma-separated steps to skip")
    ap.add_argument("--from", dest="from_step", help="start from this step")
    args = ap.parse_args()

    selected = STEPS[:]
    if args.from_step:
        if args.from_step not in names:
            ap.error(f"--from must be one of: {', '.join(names)}")
        selected = selected[names.index(args.from_step):]
    if args.only:
        only = [s.strip() for s in args.only.split(",") if s.strip()]
        bad = [s for s in only if s not in names]
        if bad: ap.error(f"--only has unknown steps: {', '.join(bad)}")
        selected = [st for st in STEPS if st[0] in only]
    if args.skip:
        skip = [s.strip() for s in args.skip.split(",") if s.strip()]
        bad = [s for s in skip if s not in names]
        if bad: ap.error(f"--skip has unknown steps: {', '.join(bad)}")
        selected = [st for st in selected if st[0] not in skip]
    if not selected:
        ap.error("no steps selected")

    print("Running:", ", ".join(n for n,_ in selected))
    for _, cmd in selected:
        run(cmd)
    print("All selected steps completed.")

if __name__ == "__main__":
    main()
