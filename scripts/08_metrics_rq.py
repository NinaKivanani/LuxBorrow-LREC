#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, yaml, os, math, csv
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

LANGS = ("LU","DE","FR","EN")

def cmi(lang_counts):
    tot = sum(lang_counts.values())
    if tot == 0: return 0.0
    maxl = max((lang_counts.get(l,0) for l in LANGS), default=0)
    return 100.0 * (1.0 - (maxl / tot))

def entropy(lang_counts):
    tot = sum(lang_counts.values())
    if tot == 0: return 0.0
    H = 0.0
    for v in lang_counts.values():
        if v == 0: continue
        p = v / tot
        H += -p * math.log(p + 1e-12)
    return H

def m_index(lang_counts):
    tot = sum(lang_counts.values())
    if tot == 0: return 0.0
    ps = [v/tot for v in lang_counts.values() if v>0]
    pairs = 0; acc = 0.0
    for i in range(len(ps)):
        for j in range(i+1, len(ps)):
            pairs += 1; acc += min(ps[i], ps[j])
    return (acc / pairs) if pairs else 0.0

def year_bucket(date_str):
    if not date_str: return "unknown"
    try:
        y = int(date_str[:4])
    except Exception:
        try: y = datetime.fromisoformat(date_str).year
        except Exception: return "unknown"
    if 1999 <= y <= 2007: return "1999–2007"
    if 2008 <= y <= 2011: return "2008–2011"
    if 2012 <= y <= 2019: return "2012–2019"
    if y == 2020: return "2020"
    if y == 2021: return "2021"
    if 2022 <= y <= 2025: return "2022–2025"
    return "unknown"

def main():
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    paths = cfg["paths"]

    raw_dir = Path(paths["out_raw"])
    lab_path = Path(paths["out_root"]) / "labels" / "borrowing_switch.jsonl"
    met_dir = Path(paths["out_root"]) / "metrics"; met_dir.mkdir(parents=True, exist_ok=True)

    labels_by_id = {}
    if lab_path.exists():
        with lab_path.open("r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                labels_by_id[row["id"]] = row

    by_section = defaultdict(lambda: {"cmi": [], "entropy": [], "m": []})
    by_period  = defaultdict(lambda: {"cmi": [], "entropy": [], "m": []})
    dia_month_counts = defaultdict(lambda: {"total":0,"cs":0,"bor":0})
    dia_donor_counts = defaultdict(lambda: Counter())

    for src in sorted(raw_dir.glob("*_LU.jsonl")):
        with src.open("r", encoding="utf-8") as f:
            for line in f:
                ex = json.loads(line)
                did = ex.get("id")
                section = ex.get("section","unknown") or "unknown"
                # prefer public_date from preprocessing; fall back to other common keys
                date = ex.get("public_date") or ex.get("date") or ex.get("published_at") or ""
                period = year_bucket(date)
                month_key = (date or "unknown")[:7] if date else "unknown"

                # Use loanword_tags for more accurate language identification
                loanword_tags = ex.get("loanword_tags", [])
                lid_sentences = ex.get("lid_sentences", [])
                sents = ex.get("sentences", [])
                
                # Prefer loanword_tags if available, fallback to lid_sentences
                if loanword_tags:
                    cnt = Counter(); tot = 0
                    for sentence_tags in loanword_tags:
                        for token_tag in sentence_tags:
                            if isinstance(token_tag, dict) and "tag" in token_tag:
                                tag = "LU"  # Default
                                if token_tag["tag"] == "BORROWED" and token_tag.get("evidence"):
                                    evidence = token_tag["evidence"]
                                    loan_languages = evidence.get("loan_languages", [])
                                    if "DE" in loan_languages:
                                        tag = "DE"
                                    elif "FR" in loan_languages:
                                        tag = "FR"
                                    elif "EN" in loan_languages:
                                        tag = "EN"
                                
                                if tag in LANGS:
                                    cnt[tag] += 1
                                    tot += 1
                elif lid_sentences and len(lid_sentences) == len(sents):
                    # Fallback to simple lid_sentences
                    cnt = Counter(); tot = 0
                    for ls in lid_sentences:
                        for L in ls:
                            if L in LANGS: cnt[L] += 1
                            tot += 1
                else:
                    continue
                    
                if tot == 0: continue

                C, H, M = cmi(cnt), entropy(cnt), m_index(cnt)
                by_section[section]["cmi"].append(C)
                by_section[section]["entropy"].append(H)
                by_section[section]["m"].append(M)
                by_period[period]["cmi"].append(C)
                by_period[period]["entropy"].append(H)
                by_period[period]["m"].append(M)

                non_lu = tot - cnt.get("LU",0)
                dia_month_counts[month_key]["total"] += tot
                dia_month_counts[month_key]["cs"]    += non_lu

                # borrowing analysis using loanword_tags
                bor = 0; dFR=dDE=dEN=0
                
                # Use loanword_tags if available for more accurate borrowing detection
                if loanword_tags:
                    for sentence_tags in loanword_tags:
                        for token_tag in sentence_tags:
                            if (isinstance(token_tag, dict) and 
                                token_tag.get("tag") == "BORROWED" and 
                                token_tag.get("evidence")):
                                
                                evidence = token_tag["evidence"]
                                loan_languages = evidence.get("loan_languages", [])
                                
                                # Count as borrowing
                                bor += 1
                                
                                # Count donor languages
                                if "FR" in loan_languages:
                                    dFR += 1
                                elif "DE" in loan_languages:
                                    dDE += 1
                                elif "EN" in loan_languages:
                                    dEN += 1
                else:
                    # Fallback to borrowing_switch.jsonl labels if loanword_tags not available
                    lab_doc = labels_by_id.get(did)
                    if lab_doc and lid_sentences:
                        labs = lab_doc["labels"]
                        for si, sent in enumerate(sents):
                            if si >= len(lid_sentences): continue
                            lid_sent = lid_sentences[si]
                            lab_sent = labs[si] if si < len(labs) else []
                            for ti, tok in enumerate(sent):
                                L = lid_sent[ti] if ti < len(lid_sent) else "UNK"
                                if L == "LU": continue
                                ann = lab_sent[ti] if ti < len(lab_sent) else {}
                                if ann.get("label") == "Borrowing":
                                    bor += 1
                                    donor = (ann.get("evidence") or {}).get("donor")
                                    if donor == "FR": dFR += 1
                                    elif donor == "DE": dDE += 1
                                    elif donor == "EN": dEN += 1
                dia_month_counts[month_key]["bor"] += bor
                dia_donor_counts[month_key]["FR"]  += dFR
                dia_donor_counts[month_key]["DE"]  += dDE
                dia_donor_counts[month_key]["EN"]  += dEN

    # write RQ1 tables
    def write_stats(rows, out_csv):
        with open(out_csv, "w", newline="", encoding="utf-8") as g:
            w = csv.writer(g); w.writerow(["group","metric","mean","n"])
            for k, d in rows.items():
                for m in ("cmi","entropy","m"):
                    arr = d.get(m, [])
                    if not arr: continue
                    w.writerow([k, m, sum(arr)/len(arr), len(arr)])

    write_stats(by_section, Path(met_dir/"rq1_by_section.csv"))
    write_stats(by_period,  Path(met_dir/"rq1_by_period.csv"))

    # write RQ4 diachrony
    with open(met_dir/"rq4_diachrony.csv", "w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["month","cs_rate","borrow_share","donor_FR","donor_DE","donor_EN"])
        for m in sorted(dia_month_counts.keys()):
            totals = dia_month_counts[m]
            tot = totals["total"] or 1
            cs_rate = totals["cs"]/tot
            borrow_share = (totals["bor"]/totals["cs"]) if totals["cs"] else 0.0
            donors = dia_donor_counts[m]
            w.writerow([m, cs_rate, borrow_share, donors["FR"], donors["DE"], donors["EN"]])

    print("Wrote metrics to", met_dir)

if __name__ == "__main__":
    main()
