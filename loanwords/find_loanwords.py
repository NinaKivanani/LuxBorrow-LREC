import json
import math
import ast
import unicodedata
import os
from typing import List, Dict, Tuple, Optional, Set
from pathlib import Path

import pandas as pd
from tqdm import tqdm
from loanwords.utils import load_lod_dataset

# -----------------------------
# Configuration & Constants
# -----------------------------
LANG_COLS = {
    "DE": "Translation_DE",
    "FR": "Translation_FR",
    "EN": "Translation_EN",
}

MIN_LEMMA_LENGTH = 4
DATA_DIR = Path("loanwords/data")
OUTPUT_DIR = Path("loanwords/output")
EXCLUDE_CATEGORIES = {
    'PLANTE', 'MUSEKSINSTRUMENT', 'CHEEMESCHT-ELEMENT',
    'MARKENNUMM', 'WARUNG', 'NOM-DE-LIEU', 'MOOSSEENHEET', 'AWUNNER'
}

# -----------------------------
# String & Data Helpers
# -----------------------------

def _coerce_to_list(value) -> List[str]:
    """Handles various cell formats (lists, string-lists, NaNs) into a clean list."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    if isinstance(value, list):
        return [str(i).strip() for i in value if str(i).strip()]
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, list):
                    return [str(i).strip() for i in parsed if str(i).strip()]
            except (ValueError, SyntaxError):
                pass
        return [t.strip() for t in s.split(",") if t.strip()]
    return [str(value).strip()]

def _prep_translations(row: pd.Series) -> Dict[str, List[str]]:
    """Generates variants for each translation (stripped hyphens/diacritics)."""
    HYPHENS = "-‐‑‒–—―"
    TRANS_TABLE = str.maketrans("", "", HYPHENS)

    def strip_diacritics(s: str) -> str:
        nfkd = unicodedata.normalize("NFKD", s)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    out: Dict[str, List[str]] = {}
    for lang, col in LANG_COLS.items():
        originals = _coerce_to_list(row.get(col))
        variants = []

        for t in originals:
            if not t: continue
            candidates = [t]
            
            hy = t.translate(TRANS_TABLE).strip()
            if hy and hy not in candidates: candidates.append(hy)

            dia = strip_diacritics(t)
            if dia and dia not in candidates: candidates.append(dia)

            hy_dia = strip_diacritics(hy)
            if hy_dia and hy_dia not in candidates: candidates.append(hy_dia)

            variants.extend(candidates)

        # Unique items while preserving order
        out[lang] = list(dict.fromkeys(variants))
    return out

def _lower_index(values: List[str]) -> Dict[str, List[str]]:
    """Maps lowercased form to original casing."""
    idx = {}
    for v in values:
        idx.setdefault(v.lower(), []).append(v)
    return idx

# -----------------------------
# Morphological Engine
# -----------------------------

def generate_variants(lemma: str) -> List[Tuple[str, str, str]]:
    """Applies linguistic rules to lemma to find potential source language matches."""
    variants = []
    L, l = lemma, lemma.lower()
    variants.append((L, "exact", "lexicon"))

    # Suffix Rules
    if l.endswith("éieren"):
        variants.append((L[:-6] + "er", "er→éieren", "morph"))
        variants.append((L[:-6] + "ir", "ir→éieren", "morph"))

    if l.endswith("néieren"):
        variants.append((L[:-7] + "nner", "nner→néieren", "morph"))
    
    if l.endswith("éiert"):
        variants.append((L[:-5] + "é", "é→éiert", "morph"))
        variants.append((L[:-5] + "i", "i→éiert", "morph"))

    if l.endswith("néiert"):
        variants.append((L[:-6] + "nné", "nné→néiert", "morph"))

    if "oun" in l:
        variants.append((l.replace("oun", "on"), "on→oun", "orth"))

    if l.endswith("ck"):
        variants.append((L[:-2] + "que", "que→ck", "orth"))

    if l.endswith("éit"):
        variants.append((L[:-3] + "é", "é→éit", "morph"))

        variants.append((L[:-3] + "ät", "ät→éit", "morph"))

    if l.endswith("el"):
        variants.append((L[:-2] + "le", "le→el", "orth"))

    variants.append((L + "e", "-e", "morph"))

    if L.startswith("E"):
        variants.append(("É" + L[1:], "É→E", "orth"))

    if l.endswith("er"):
        variants.append((L[:-2] + "eur", "eur→er", "morph"))

    if "oun" in l and "k" in l:
        variants.append((l.replace("oun", "on").replace("k", "c"), "on→oun + c→k", "orth"))

    # Deduplicate by lowercase surface form
    seen = set()
    deduped = []
    for v, tag, p_type in variants:
        if v.lower() not in seen:
            seen.add(v.lower())
            deduped.append((v, tag, p_type))
    return deduped

# -----------------------------
# Core Processing Logic
# -----------------------------

def match_row(row: pd.Series) -> Optional[Dict]:
    """Matches a single row against cross-lingual variants."""
    lemma = str(row["Lemma"]).strip()
    if len(lemma) < MIN_LEMMA_LENGTH or len(lemma.split()) > 1:
        return None

    translations = _prep_translations(row)
    idx_by_lang = {lang: _lower_index(vals) for lang, vals in translations.items()}
    
    details = []
    for variant, pattern, p_type in generate_variants(lemma):
        key = variant.lower()
        for lang, idx in idx_by_lang.items():
            if key in idx:
                for original in idx[key]:
                    details.append({
                        "language": lang,
                        "translation": original,
                        "pattern": pattern,
                        "type": p_type
                    })

    if not details:
        return None

    return {
        "lemma": lemma,
        "meaning_id": row.get("MeaningID"),
        "attributes": row.get('Attributes'),
        "categories": row.get('Categories'),
        "part_of_speech": row.get('PartOfSpeech'),
        "word_forms": row.get('word_forms'),
        "details": details,
        "loan_languages": sorted(list({d["language"] for d in details}))
    }

def extract_loanword_matches(df: pd.DataFrame) -> List[Dict]:
    """Iterates through DataFrame and filters by Part of Speech."""
    valid_pos = {'SUBST', 'ADJ', 'VRB'}
    matches = []
    for _, row in df.iterrows():
        if row['PartOfSpeech'] in valid_pos:
            payload = match_row(row)
            if payload:
                matches.append(payload)
    return matches

def filter_matches(matches: List[Dict]) -> List[Dict]:
    """Cleans matches using external loanword lists and origin files."""
    
    def load_set(filename: str) -> Set[str]:
        path = DATA_DIR / filename
        if not path.exists(): return set()
        with open(path, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}

    # Load lookup sets
    fr_de = load_set("loans_fr_to_de.txt")
    en_de = load_set("loans_en_to_de.txt")
    fr_en = load_set("loans_fr_to_en.txt")
    en_fr = load_set("loans_en_to_fr.txt")
    ohg_terms = load_set("german_terms_from_high_german.txt")

    updated_list = []
    for m in tqdm(matches, desc="Filtering matches"):
        # Category filter
        if m["categories"] and any(c in EXCLUDE_CATEGORIES for c in m["categories"]):
            continue

        langs = m["loan_languages"]
        get_t = lambda l: next((d["translation"] for d in m["details"] if d["language"] == l), None)
        de_w, fr_w, en_w = get_t("DE"), get_t("FR"), get_t("EN")
        is_friemwuert = "FRIEMWUERT" in (m.get("categories") or [])

        # Three-language case: resolve source via bilingual loan lists.
        if len(langs) == 3:
            # Strong evidence: both other languages borrowed from the same source.
            if de_w in fr_de and en_w in fr_en:
                m["loan_languages"] = ["FR"]
                m["details"] = [d for d in m["details"] if d["language"] == "FR"]
                updated_list.append(m)
            elif de_w in en_de and fr_w in en_fr:
                m["loan_languages"] = ["EN"]
                m["details"] = [d for d in m["details"] if d["language"] == "EN"]
                updated_list.append(m)
            # Weaker evidence: only one bilingual list confirms the source.
            elif de_w in en_de:
                m["loan_languages"] = ["EN"]
                m["details"] = [d for d in m["details"] if d["language"] == "EN"]
                updated_list.append(m)
            elif de_w in fr_de:
                m["loan_languages"] = ["FR"]
                m["details"] = [d for d in m["details"] if d["language"] == "FR"]
                updated_list.append(m)
            elif en_w in fr_en:
                m["loan_languages"] = ["FR"]
                m["details"] = [d for d in m["details"] if d["language"] == "FR"]
                updated_list.append(m)
            elif fr_w in en_fr:
                m["loan_languages"] = ["EN"]
                m["details"] = [d for d in m["details"] if d["language"] == "EN"]
                updated_list.append(m)
            elif is_friemwuert:
                m["loan_languages"] = ["OTHER"]
                updated_list.append(m)
            # else: ambiguous, drop.
            continue

        # Two-language cases: drop the German side if it's a known loan;
        # otherwise drop the match entirely.
        if langs == ["DE", "EN"]:
            if de_w and de_w in en_de:
                m["loan_languages"] = ["EN"]
                m["details"] = [d for d in m["details"] if d["language"] == "EN"]
                updated_list.append(m)
            continue

        if langs == ["DE", "FR"]:
            if de_w and de_w in fr_de:
                m["loan_languages"] = ["FR"]
                m["details"] = [d for d in m["details"] if d["language"] == "FR"]
                updated_list.append(m)
            continue

        if langs == ["EN", "FR"]:
            if en_w and en_w in fr_en:
                m["loan_languages"] = ["FR"]
                m["details"] = [d for d in m["details"] if d["language"] == "FR"]
                updated_list.append(m)
            continue

        # DE-only case: try to reassign to FR/EN, else drop if inherited from OHG.
        if langs == ["DE"]:
            if de_w and de_w in fr_de:
                m["loan_languages"] = ["FR"]
                m["details"] = [{**d, "language": "FR", "pattern": "post-edit"} for d in m["details"]]
                updated_list.append(m)
                continue
            if de_w and de_w in en_de:
                m["loan_languages"] = ["EN"]
                m["details"] = [{**d, "language": "EN", "pattern": "post-edit"} for d in m["details"]]
                updated_list.append(m)
                continue
            if de_w and de_w in ohg_terms:
                continue

        updated_list.append(m)

    return updated_list

# -----------------------------
# Enrichment & Export
# -----------------------------

def add_lux_synonyms(matches: List[Dict], df: pd.DataFrame):
    """Enriches matches with non-loanword synonyms."""
    loans = {m["lemma"] for m in matches}
    synonym_lookup = {}
    for _, row in df.iterrows():
        lemma, mid = str(row["Lemma"]).strip(), row.get("MeaningID")
        syns = [s for s in _coerce_to_list(row.get("Synonyms")) if s and s not in loans]
        if syns:
            synonym_lookup[(lemma, mid)] = syns

    for m in matches:
        m["lux_synonyms"] = synonym_lookup.get((m["lemma"], m["meaning_id"]), [])

def run_manual_ops(matches: List[Dict], df: pd.DataFrame):
    """Handles manual additions and removals from text files."""
    # Removals
    removals_path = DATA_DIR / "manual_removals.txt"
    if removals_path.exists():
        with open(removals_path, "r", encoding="utf-8") as f:
            removals = {line.strip() for line in f if line.strip()}
        matches[:] = [m for m in matches if m["lemma"] not in removals]

    # Additions
    adds_path = DATA_DIR / "manual_adds.txt"
    if adds_path.exists():
        existing_lemmas = {m["lemma"] for m in matches}
        adds_df = pd.read_csv(adds_path, sep=" ", header=None, names=["Word", "Lang"])
        for _, row in adds_df.iterrows():
            word, lang = row["Word"], row["Lang"]
            if word in existing_lemmas: continue
            
            # Try to find in LOD, else dummy entry
            lod_match = df[df['Lemma'] == word]
            if not lod_match.empty:
                for _, meaning in lod_match.iterrows():
                    matches.append({
                        "lemma": word, "meaning_id": meaning['MeaningID'],
                        "attributes": meaning['Attributes'], "categories": meaning['Categories'],
                        "part_of_speech": meaning['PartOfSpeech'], "word_forms": meaning['word_forms'],
                        "details": [{"language": lang, "translation": None, "pattern": "manual", "type": "manual"}],
                        "loan_languages": [lang], "lux_synonyms": []
                    })
            else:
                matches.append({
                    "lemma": word, "meaning_id": None, "details": [{"language": lang, "pattern": "manual"}],
                    "loan_languages": [lang], "lux_synonyms": []
                })

# -----------------------------
# Execution
# -----------------------------

if __name__ == "__main__":
    # Load and Process
    lod_df = load_lod_dataset('loanwords/data/new_lod-art.xml')
    loan_matches = extract_loanword_matches(lod_df)
    loan_matches = filter_matches(loan_matches)
    
    run_manual_ops(loan_matches, lod_df)
    add_lux_synonyms(loan_matches, lod_df)

    # Save Results
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_DIR / "lux_loanwords.json", "w", encoding="utf-8") as f:
        json.dump(loan_matches, f, ensure_ascii=False, indent=4)

