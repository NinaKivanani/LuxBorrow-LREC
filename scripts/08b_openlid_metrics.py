#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate OpenLID-based code-switching statistics to complement pattern-based borrowing analysis.
This provides the ACTUAL language distribution detected by OpenLID (15.35% code-switching)
vs the limited pattern-based borrowing patterns (0.67%).
"""

import json, yaml, os, csv
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

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
    met_dir = Path(paths["out_root"]) / "metrics"; met_dir.mkdir(parents=True, exist_ok=True)

    # OpenLID-based statistics
    openlid_overall = Counter()
    openlid_by_section = defaultdict(Counter)
    openlid_by_period = defaultdict(Counter)
    openlid_month_counts = defaultdict(lambda: Counter())

    docs = tokens = 0

    for src in sorted(raw_dir.glob("*_LU.jsonl")):
        with src.open("r", encoding="utf-8") as f:
            for line in f:
                ex = json.loads(line)
                section = ex.get("section","unknown") or "unknown"
                date = ex.get("public_date") or ex.get("date") or ex.get("published_at") or ""
                period = year_bucket(date)
                month_key = (date or "unknown")[:7] if date else "unknown"

                counted_doc = False

                # Prefer rich loanword_tags if available
                loanword_tags = ex.get("loanword_tags", [])
                if loanword_tags:
                    for sentence_tags in loanword_tags:
                        for token_tag in sentence_tags:
                            if not isinstance(token_tag, dict) or "tag" not in token_tag:
                                continue
                            # Determine language based on the tag and evidence
                            tag = "LU"  # default to Luxembourgish
                            if token_tag["tag"] == "BORROWED" and token_tag.get("evidence"):
                                evidence = token_tag["evidence"]
                                loan_languages = evidence.get("loan_languages", [])
                                if "DE" in loan_languages:
                                    tag = "DE"
                                elif "FR" in loan_languages:
                                    tag = "FR"
                                elif "EN" in loan_languages:
                                    tag = "EN"
                            tokens += 1
                            openlid_overall[tag] += 1
                            openlid_by_section[section][tag] += 1
                            openlid_by_period[period][tag] += 1
                            openlid_month_counts[month_key][tag] += 1
                            counted_doc = True
                else:
                    # Fallback to OpenLID token labels from lid_sentences
                    lid_sentences = ex.get("lid_sentences", [])
                    for lids in lid_sentences:
                        for L in lids:
                            if L in {"LU","DE","FR","EN"}:
                                tokens += 1
                                openlid_overall[L] += 1
                                openlid_by_section[section][L] += 1
                                openlid_by_period[period][L] += 1
                                openlid_month_counts[month_key][L] += 1
                                counted_doc = True

                if counted_doc:
                    docs += 1

    # Write OpenLID overall statistics
    with open(met_dir/"openlid_overall.csv", "w", newline="", encoding="utf-8") as g:
        w = csv.writer(g); w.writerow(["language","count","share"])
        total = sum(openlid_overall.values()) or 1
        for lang, count in openlid_overall.most_common():
            w.writerow([lang, count, f"{count/total:.4f}"])

    # Write OpenLID by section
    with open(met_dir/"openlid_by_section.csv", "w", newline="", encoding="utf-8") as g:
        w = csv.writer(g); w.writerow(["section","language","count","share"])
        for section, lang_counts in openlid_by_section.items():
            total = sum(lang_counts.values()) or 1
            for lang, count in lang_counts.most_common():
                w.writerow([section, lang, count, f"{count/total:.4f}"])

    # Write OpenLID by period
    with open(met_dir/"openlid_by_period.csv", "w", newline="", encoding="utf-8") as g:
        w = csv.writer(g); w.writerow(["period","language","count","share"])
        for period, lang_counts in openlid_by_period.items():
            total = sum(lang_counts.values()) or 1
            for lang, count in lang_counts.most_common():
                w.writerow([period, lang, count, f"{count/total:.4f}"])

    # Write OpenLID diachronic data
    with open(met_dir/"openlid_diachrony.csv", "w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["month","total_tokens","LU","DE","FR","EN","cs_rate","de_rate","fr_rate","en_rate"])
        for month in sorted(openlid_month_counts.keys()):
            counts = openlid_month_counts[month]
            total = sum(counts.values()) or 1
            lu = counts.get("LU", 0)
            de = counts.get("DE", 0)
            fr = counts.get("FR", 0)
            en = counts.get("EN", 0)
            if total > 0:
                cs_rate = (de + fr + en) / total
                w.writerow([month, total, lu, de, fr, en, 
                           f"{cs_rate:.4f}", f"{de/total:.4f}", f"{fr/total:.4f}", f"{en/total:.4f}"])
            else:
                w.writerow([month, total, lu, de, fr, en, "0.0000", "0.0000", "0.0000", "0.0000"])

    # Write summary
    with open(met_dir/"openlid_summary.txt", "w", encoding="utf-8") as g:
        g.write(f"Documents processed: {docs}\n")
        g.write(f"Total tokens: {tokens}\n")
        g.write(f"Language distribution (OpenLID):\n")
        total = sum(openlid_overall.values())
        
        if total > 0:
            for lang, count in openlid_overall.most_common():
                percentage = (count / total) * 100
                g.write(f"  {lang}: {count:,} tokens ({percentage:.2f}%)\n")
            
            non_lu = total - openlid_overall.get("LU", 0)
            cs_percentage = (non_lu / total) * 100
            g.write(f"\nCode-switching tokens (non-LU): {non_lu:,} ({cs_percentage:.2f}%)\n")
        else:
            g.write("  No tokens found for language distribution.\n")
            cs_percentage = 0.0

    print("OpenLID metrics written to", met_dir)
    print(f"Processed {docs:,} documents with {tokens:,} tokens")
    
    if total > 0:
        print(f"Code-switching rate: {cs_percentage:.2f}% (vs {(openlid_overall.get('LU',0)/total)*100:.2f}% LU)")
    else:
        print("Code-switching rate: N/A (no tokens processed)")

if __name__ == "__main__":
    main()
