#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd, os, yaml
from pathlib import Path

def load_config():
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    return yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))

cfg = load_config()
paths = cfg["paths"]
root = Path(paths["out_root"]) / "metrics"
out = Path(paths["tables"]); out.mkdir(parents=True, exist_ok=True)

def pivot(csv_path, group_label):
    df = pd.read_csv(csv_path)
    tbl = (df.pivot(index="group", columns="metric", values="mean")
             .reindex(columns=["cmi","entropy","m"]))
    n = df.groupby("group")["n"].max()
    tbl.insert(0,"n", n)
    tbl.index.name = group_label
    return tbl.round({"cmi":1, "entropy":3, "m":3})

sec = pivot(root/"rq1_by_section.csv", "Section")
per = pivot(root/"rq1_by_period.csv",  "Period")

sec.to_csv(out/"rq1_by_section_table.csv")
per.to_csv(out/"rq1_by_period_table.csv")

sec_tex = sec.to_latex(escape=True, column_format="lrrrr", bold_rows=False)
per_tex = per.to_latex(escape=True, column_format="lrrrr", bold_rows=False)

(out/"rq1_by_section_table.tex").write_text(sec_tex, encoding="utf-8")
(out/"rq1_by_period_table.tex").write_text(per_tex, encoding="utf-8")

print("Wrote tables to", out)
