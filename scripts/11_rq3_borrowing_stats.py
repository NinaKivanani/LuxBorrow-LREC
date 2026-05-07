#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, csv, re, os, yaml
from pathlib import Path
from collections import Counter, defaultdict

PUNCT_RX = re.compile(r"^[\W_]+|[\W_]+$")

def norm_surface(s: str) -> str:
    if not s: return ""
    s = s.lower()
    s = PUNCT_RX.sub("", s)
    return s.replace("'","'").replace("´","'").replace("`","'")

def light_stem(s: str) -> str:
    if len(s) <= 4: return s
    for suf in ("en","er","e","s"):
        if s.endswith(suf) and len(s)-len(suf) >= 4:
            return s[:-len(suf)]
    return s

def main():
    cfg_path = os.environ.get("CONFIG_PATH","config/config.yaml")
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    paths = cfg["paths"]

    raw_dir = Path(paths["out_raw"])
    out_dir  = Path(paths["out_root"])/"metrics"; out_dir.mkdir(parents=True, exist_ok=True)

    # Optional borrowing labels produced by script 07
    lab_path = Path(paths["out_root"]) / "labels" / "borrowing_switch.jsonl"
    labels_by_id = {}
    if lab_path.exists():
        with lab_path.open("r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                labels_by_id[row.get("id")] = row.get("labels", [])

    donor_overall = Counter()
    donor_by_section = defaultdict(Counter)
    pattern_overall = Counter()
    borrowed_forms = Counter()
    borrowed_stems = Counter()

    docs = tokens = bor_tokens = 0

    for src in sorted(raw_dir.glob("*_LU.jsonl")):
        with src.open("r", encoding="utf-8") as f:
            for line in f:
                ex = json.loads(line)
                did = ex.get("id"); section = ex.get("section") or "unknown"
                counted_doc = False

                # Preferred: use rich in-document loanword_tags if present
                loanword_tags = ex.get("loanword_tags", [])
                if loanword_tags:
                    docs += 1; counted_doc = True
                    for sentence_tags in loanword_tags:
                        for token_tag in sentence_tags:
                            if not isinstance(token_tag, dict) or "word" not in token_tag:
                                continue
                            tokens += 1
                            word = token_tag.get("word", "")
                            if (token_tag.get("tag") == "BORROWED" and token_tag.get("evidence")):
                                evidence = token_tag["evidence"]
                                bor_tokens += 1
                                loan_languages = evidence.get("loan_languages", [])
                                if "FR" in loan_languages:
                                    donor = "FR"
                                elif "DE" in loan_languages:
                                    donor = "DE"
                                elif "EN" in loan_languages:
                                    donor = "EN"
                                else:
                                    donor = "UNK"
                                details = evidence.get("details", [])
                                pattern = details[0].get("pattern", "UNK") if details else "UNK"
                                donor_overall[donor] += 1
                                donor_by_section[section][donor] += 1
                                pattern_overall[pattern] += 1
                                nn = norm_surface(word); ss = light_stem(nn)
                                if nn: borrowed_forms[nn] += 1
                                if ss: borrowed_stems[ss] += 1

                # Fallback: use labels from borrowing_switch.jsonl (script 07)
                elif did in labels_by_id:
                    labs = labels_by_id[did] or []
                    tokenized = ex.get("tokenized_sentences", [])
                    sentences = tokenized if tokenized else []
                    if sentences:
                        docs += 1; counted_doc = True
                    for si, sent in enumerate(sentences):
                        lab_sent = labs[si] if si < len(labs) else []
                        tokens += len(sent)
                        for ti, tok in enumerate(sent):
                            ann = lab_sent[ti] if ti < len(lab_sent) else {}
                            if ann.get("label") == "Borrowing":
                                bor_tokens += 1
                                ev = ann.get("evidence") or {}
                                donor = ev.get("donor", "UNK") or "UNK"
                                pattern = ev.get("pattern", "UNK") or "UNK"
                                donor_overall[donor] += 1
                                donor_by_section[section][donor] += 1
                                pattern_overall[pattern] += 1
                                nn = norm_surface(tok); ss = light_stem(nn)
                                if nn: borrowed_forms[nn] += 1
                                if ss: borrowed_stems[ss] += 1

    # write outputs
    def write_kv(counter, header, path):
        with open(path, "w", newline="", encoding="utf-8") as g:
            w = csv.writer(g); w.writerow(header)
            for k,v in counter.most_common():
                if len(header)==2:
                    w.writerow([k,v])
                else:
                    total = sum(counter.values()) or 1
                    w.writerow([k,v,f"{v/total:.4f}"])

    write_kv(donor_overall, ["donor","count","share"], out_dir/"rq3_donor_split_overall.csv")
    with open(out_dir/"rq3_donor_split_by_section.csv","w",newline="",encoding="utf-8") as g:
        w = csv.writer(g); w.writerow(["section","donor","count"])
        for sec, cnts in donor_by_section.items():
            for d,c in cnts.most_common():
                w.writerow([sec,d,c])

    write_kv(pattern_overall, ["pattern","count"], out_dir/"rq3_borrowing_patterns.csv")
    write_kv(borrowed_forms, ["form_norm","count"], out_dir/"rq3_top_borrowed_forms.csv")
    write_kv(borrowed_stems, ["stem_light","count"], out_dir/"rq3_top_borrowed_stems.csv")

    with open(out_dir/"rq3_summary.txt","w",encoding="utf-8") as g:
        g.write(f"Docs scanned: {docs}\n")
        g.write(f"Tokens seen: {tokens}\n")
        g.write(f"Borrowed tokens: {bor_tokens}\n")
        g.write(f"Donor overall: {dict(donor_overall)}\n")

    print("RQ3 outputs written to", out_dir)

if __name__ == "__main__":
    main()
