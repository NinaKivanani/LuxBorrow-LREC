#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, yaml, os
from pathlib import Path
from pattern_runtime import load_compiled_index, apply_patterns

def foreign_run_len(lids, i):
    if not lids or lids[i] == "LU": return 0
    lang = lids[i]; n = len(lids); L = 1
    j = i - 1
    while j >= 0 and lids[j] == lang: L += 1; j -= 1
    j = i + 1
    while j < n and lids[j] == lang: L += 1; j += 1
    return L

def lu_ratio_neighborhood(lids, i, k=3):
    n = len(lids); lu = tot = 0
    for j in range(max(0, i-k), min(n, i+k+1)):
        if j == i: continue
        tot += 1; lu += (lids[j] == "LU")
    return (lu / tot) if tot else 0.0

def main():
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    paths = cfg["paths"]

    compiled = Path(paths["manifests"]) / "compiled_patterns.json"
    index = load_compiled_index(compiled)

    src_dir = Path(paths["out_raw"])
    out_dir = Path(paths["out_root"]) / "labels"; out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "borrowing_switch.jsonl"

    with out_path.open("w", encoding="utf-8") as g:
        # Only process Luxembourgish sentences for borrowing detection
        for src in sorted(src_dir.glob("*_LU.jsonl")):
            with src.open("r", encoding="utf-8") as f:
                for line in f:
                    ex = json.loads(line)
                    sents = ex["sentences"]
                    lids  = ex.get("lid_sentences", [])
                    # Use tokenized_sentences instead of sentences for token-level processing
                    tokenized_sents = ex.get("tokenized_sentences", [])
                    if not tokenized_sents:
                        # Fallback: if no tokenized_sentences, skip this document
                        continue
                    
                    if not lids or len(lids) != len(tokenized_sents):
                        lids = [["LU"] * len(s) for s in tokenized_sents]

                    doc_labels = []
                    
                    for si, (sent, lid_sent) in enumerate(zip(tokenized_sents, lids)):
                        sent_labels = []
                        for ti, tok in enumerate(sent):
                            form = tok; L = lid_sent[ti] if ti < len(lid_sent) else "LU"
                            cands = apply_patterns(form, index)
                            frun  = foreign_run_len(lid_sent, ti)
                            lurat = lu_ratio_neighborhood(lid_sent, ti, k=3)

                            if L == "LU":
                                if cands:
                                    label, evidence = "Borrowing", cands[0]
                                else:
                                    label, evidence = "LU", None
                            else:
                                if cands and frun <= 2 and lurat >= 0.6:
                                    label, evidence = "Borrowing", cands[0]
                                elif frun >= 3:
                                    label, evidence = "Switch", None
                                else:
                                    label, evidence = "Ambiguous", None

                            sent_labels.append({"label": label, "evidence": evidence})
                        doc_labels.append(sent_labels)

                    g.write(json.dumps({
                        "id": ex.get("id"),
                        "section": ex.get("section"),
                        "labels": doc_labels
                    }, ensure_ascii=False) + "\n")
    print("Wrote", out_path)

if __name__ == "__main__":
    main()
