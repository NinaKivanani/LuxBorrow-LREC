#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv, os, yaml
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt

def load_config():
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    return yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))

cfg = load_config()
paths = cfg["paths"]
plot_cfg = (cfg.get("plots") or {})
ref_lines = plot_cfg.get("reference_lines", [])
IN_CSV = Path(paths["out_root"]) / "metrics" / "rq4_diachrony.csv"
OUT_DIR = Path(paths["figures"]); OUT_DIR.mkdir(parents=True, exist_ok=True)
REFLINES = [(item.get("month"), item.get("label")) for item in ref_lines]

def parse_rows(path):
    rows = []
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
    if k<=1: return seq
    out=[]; n=len(seq); h=k//2
    for i in range(n):
        a=max(0,i-h); b=min(n,i+h+1)
        out.append(sum(seq[a:b])/len(seq[a:b]))
    return out

def add_refs(ax):
    for m,label in REFLINES:
        try:
            x=datetime.strptime(m,"%Y-%m")
        except Exception:
            continue
        ax.axvline(x=x, linestyle="--", linewidth=1)
        ax.text(x, ax.get_ylim()[1], " "+(label or m), rotation=90, va="top")

def plot_lines(xs, ys, title, ylabel, out):
    plt.figure()
    plt.plot(xs, ys)
    add_refs(plt.gca())
    plt.title(title); plt.xlabel("Month"); plt.ylabel(ylabel)
    plt.tight_layout(); plt.savefig(out, dpi=200); plt.close()

def plot_donors(xs, fr, de, en, out):
    tot = [max(1.0, fr[i]+de[i]+en[i]) for i in range(len(xs))]
    frp = [fr[i]/tot[i] for i in range(len(xs))]
    dep = [de[i]/tot[i] for i in range(len(xs))]
    enp = [en[i]/tot[i] for i in range(len(xs))]
    frp,dep,enp = movavg(frp,3), movavg(dep,3), movavg(enp,3)
    plt.figure()
    plt.stackplot(xs, frp, dep, enp, labels=["FR","DE","EN"])
    add_refs(plt.gca()); plt.legend(loc="upper right")
    plt.title("Borrowing donor mix over time"); plt.xlabel("Month"); plt.ylabel("Proportion")
    plt.tight_layout(); plt.savefig(out, dpi=200); plt.close()

def main():
    rows = parse_rows(IN_CSV)
    xs = [r["dt"] for r in rows]
    plot_lines(xs, movavg([r["cs_rate"] for r in rows],3), "Code-switching rate over time", "CS rate", OUT_DIR/"rq4_cs_rate.png")
    plot_lines(xs, movavg([r["borrow_share"] for r in rows],3), "Borrowing share among non-LU", "Borrowing share", OUT_DIR/"rq4_borrow_share.png")
    plot_donors(xs, [r["FR"] for r in rows], [r["DE"] for r in rows], [r["EN"] for r in rows], OUT_DIR/"rq4_donor_mix.png")
    print("Figures in", OUT_DIR)

if __name__ == "__main__":
    main()
