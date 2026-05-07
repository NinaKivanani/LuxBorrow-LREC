#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced LID (LU/DE/FR/EN) with hybrid approach:

SENTENCE-LEVEL: OpenLID FastText (works well for full sentences)
- Uses OpenLID for sentence-level language identification
- Higher confidence thresholds for short sentences and LU to reduce bias
- No default fallback to LU

WORD-LEVEL: Adaptive n-gram context with lexicon fallback
- Token classification using adaptive OpenLID context (2→5)
- If uncertain, falls back to light lexicon-based cues (no LU default)
- Borrowing detection handled later (script 07)
"""

import json, re, os, yaml, time, argparse
from pathlib import Path
from collections import Counter

# langdetect (optional local helper)
try:
    from langdetect import detect
    from langdetect.lang_detect_exception import LangDetectException
    HAVE_LANGDETECT = True
except Exception:
    HAVE_LANGDETECT = False

# Optional OpenAI client for batched LLM-based sentence LID
try:
    from openai import OpenAI
    HAVE_OPENAI = True
except Exception:
    HAVE_OPENAI = False

# HuggingFace transformers (unused here but kept for future)
try:
    from transformers import pipeline
    HAVE_TRANSFORMERS = True
except Exception:
    HAVE_TRANSFORMERS = False

# FastText and HuggingFace Hub for OpenLID
try:
    import fasttext
    from huggingface_hub import hf_hub_download
    HAVE_FASTTEXT = True
except Exception:
    HAVE_FASTTEXT = False

LLM_CACHE = {}

# ----------- Lexicons (precision-first; extend if needed) -----------

FR_FUN = {
    "le","la","les","des","du","un","une","au","aux","et","est","ou",
    "pour","avec","sans","sur","chez","dans","l'","l’","qu'","qu’","c'","c’","ne","pas","il","elle","nous","vous","ils","elles"
}
DE_FUN = {
    "die","das","des","ein","eine","eines","einem","einer",
    "und","nicht","auch","schon","noch","nur","mit","ohne","für","von","im","beim","vom","zum","zur","auf","aus","bei","über","unter","vor",
    "ist","sind","war","waren","wird","werden","hat","haben","wurde"
}
LU_FUN = {
    "déi","dës","dësen","deen","datt","net","mat","ouni","vum","op","fir","vun","ëm","ëmmer","hien","si",
    "wat","wou","wéi","huet","ass","sinn","gëtt","ginn","kënnen","wëssen","wëllen","mussen","dierfen","maachen","schonn","awer","mä","sou","esou","vu"
}

# apostrophe cues
FR_APOS = re.compile(r"^(l'|qu'|c'|n'|s'|t'|j'|m')", re.I)

# character-level cues (conservative)
FR_CHR = re.compile(r"[àâçôùûœ]", re.I)
DE_CHR = re.compile(r"[äöß]", re.I)
LU_CHR = re.compile(r"[ë]", re.I)

WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+")

# ----------- Sentence-level helpers -----------

def sentence_evidence(sent: str) -> Counter:
    """Return evidence votes for languages based on lexicons and patterns."""
    votes = Counter()
    toks = [t.lower() for t in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ']+", sent)]
    for t in toks:
        if t in LU_FUN or LU_CHR.search(t):
            votes["LU"] += 1
        if t in DE_FUN or DE_CHR.search(t):
            votes["DE"] += 1
        if t in FR_FUN or FR_APOS.match(t) or FR_CHR.search(t):
            votes["FR"] += 1
    return votes


def detect_sentence_language_local(sentence_text: str) -> str:
    """Hybrid local: lexicon/pattern votes + langdetect fallback."""
    s = (sentence_text or "").strip()
    if not s:
        return "UNKNOWN"
    votes = sentence_evidence(s)
    if HAVE_LANGDETECT:
        try:
            ld = detect(s)
            if ld == "de": votes["DE"] += 2
            elif ld == "fr": votes["FR"] += 2
            elif ld == "en": votes["EN"] += 2
        except LangDetectException:
            pass
    if not votes:
        return "UNKNOWN"
    lang, _ = votes.most_common(1)[0]
    return lang


# ----------- Token-level OpenLID (adaptive) -----------

def adaptive_ngram_classification(tokens, index, min_context=2, max_context=5):
    """
    Adaptive n-gram classification: start small, expand if uncertain.
    Returns best result with confidence or None if all attempts fail.
    """
    if not tokens or index >= len(tokens) or not HAVE_FASTTEXT:
        return None

    try:
        if not hasattr(adaptive_ngram_classification, '_model'):
            model_path = hf_hub_download(repo_id="facebook/fasttext-language-identification", filename="model.bin")
            adaptive_ngram_classification._model = fasttext.load_model(model_path)

        model = adaptive_ngram_classification._model

        # Try different context sizes, prefer smaller contexts if confident
        for context_size in range(min_context, max_context + 1):
            start_idx = max(0, index - context_size // 2)
            end_idx = min(len(tokens), index + context_size // 2 + 1)
            context_tokens = tokens[start_idx:end_idx]

            if len(context_tokens) < 2:
                continue

            context_text = " ".join(context_tokens)

            try:
                predictions = model.predict(context_text.replace('\n', ' '), k=1)
                if predictions and len(predictions[0]) > 0 and len(predictions[1]) > 0:
                    lang_code = predictions[0][0].replace('__label__', '').upper()
                    confidence = float(predictions[1][0])

                    lang_map = {'LTZ': 'LU', 'DEU': 'DE', 'FRA': 'FR', 'ENG': 'EN'}
                    mapped_lang = lang_map.get(lang_code, lang_code)

                    # Confidence threshold based on context size
                    min_conf = 0.6 if context_size <= 3 else 0.5

                    if mapped_lang in ['LU', 'DE', 'FR', 'EN'] and confidence >= min_conf:
                        return {'lang': mapped_lang, 'conf': confidence, 'context_size': context_size}
            except Exception:
                continue

        return None

    except Exception:
        return None


# ----------- Simple lexicon-based fallback -----------

def classify_token_simple(token: str) -> str:
    """
    Simple lexicon-based token classification.
    Returns language code or "UNKNOWN".
    """
    t = token.strip()
    if not t or len(t) < 2:
        return "UNKNOWN"

    low = t.lower()

    # Function words (highest priority)
    if low in LU_FUN: return "LU"
    if low in DE_FUN: return "DE"
    if low in FR_FUN: return "FR"

    # French apostrophe patterns
    if FR_APOS.match(low): return "FR"

    # Character patterns
    if DE_CHR.search(t): return "DE"
    if LU_CHR.search(t): return "LU"
    if re.search(r"[àâçôùûœ]", t, re.I): return "FR"

    return "UNKNOWN"


# ----------- Sentence-level OpenLID -----------

def batch_detect_with_openlid(sentences, batch_size=50):
    """
    OpenLID fastText sentence-level identification.
    Confidence thresholds depend on sentence length and language to reduce LU bias.
    Returns dict idx -> {'lang': code, 'conf': float} or idx -> None.
    """
    if not HAVE_FASTTEXT:
        print("FastText not available, skipping OpenLID")
        return {i: None for i in range(len(sentences))}
    try:
        if not hasattr(batch_detect_with_openlid, '_model'):
            print("Loading OpenLID fastText model...")
            model_path = hf_hub_download("laurievb/OpenLID", "model.bin")
            batch_detect_with_openlid._model = fasttext.load_model(model_path)
            print("OpenLID model loaded successfully")
        model = batch_detect_with_openlid._model
        results = {}
        for i, sentence in enumerate(sentences):
            # Skip very short sentences (often unreliable)
            if len(sentence.split()) < 3:
                results[i] = None
                continue
            try:
                labels, confidences = model.predict(sentence, k=1)
                if labels and confidences:
                    label = labels[0].replace('__label__', '').lower()
                    confidence = float(confidences[0])
                    lang = None
                    if label in ('de', 'deu', 'german') or label.startswith('deu_'): lang = "DE"
                    elif label in ('fr', 'fra', 'french') or label.startswith('fra_'): lang = "FR"
                    elif label in ('en', 'eng', 'english') or label.startswith('eng_'): lang = "EN"
                    elif label in ('lb', 'ltz', 'luxembourgish') or label.startswith('ltz_'): lang = "LU"

                    # Improved confidence thresholds based on sentence length and language
                    sentence_words = len(sentence.split())
                    min_confidence = 0.5  # Base threshold

                    # Adjust confidence based on sentence length
                    if sentence_words < 5:  # Very short sentences need higher confidence
                        min_confidence = 0.75
                    elif sentence_words < 10:  # Short sentences need moderate confidence
                        min_confidence = 0.65

                    # Special handling for LU (reduce bias)
                    if lang == "LU" and sentence_words < 8:
                        min_confidence = 0.8  # Higher threshold for short LU sentences

                    if lang and confidence >= min_confidence:
                        results[i] = {"lang": lang, "conf": confidence}
                    else:
                        results[i] = None
                else:
                    results[i] = None
            except Exception:
                results[i] = None
        return results
    except Exception as e:
        print(f"OpenLID model error: {e}")
        return {i: None for i in range(len(sentences))}


def batch_detect_with_llm(sentences, batch_size=20):
    """
    Optional OpenAI sentence LID.
    Returns dict idx -> {'lang': code, 'conf': 1.0} or idx -> None.
    """
    if not HAVE_OPENAI or not os.environ.get("OPENAI_API_KEY"):
        return {i: None for i in range(len(sentences))}
    client = OpenAI()
    model = os.environ.get("LID_LLM_MODEL", "gpt-4o-mini")
    results = {}
    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i+batch_size]
        idxs = list(range(i, min(i+batch_size, len(sentences))))
        uncached = [s for s in batch if s not in LLM_CACHE]
        if uncached:
            try:
                system_msg = "Return a JSON array of language codes (LU, DE, FR, EN) for each input sentence."
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role":"system","content":system_msg},
                        {"role":"user","content":json.dumps(uncached, ensure_ascii=False)}
                    ],
                    temperature=0.0
                )
                content = resp.choices[0].message.content
                try:
                    arr = json.loads(content)
                except Exception:
                    arr = []
                for s, lang in zip(uncached, arr):
                    if lang in ("LU","DE","FR","EN"):
                        LLM_CACHE[s] = lang
            except Exception as e:
                print("LLM error:", e)
        for j, s in zip(idxs, batch):
            if s in LLM_CACHE:
                results[j] = {"lang": LLM_CACHE[s], "conf": 1.0}
            else:
                results[j] = None
    return results


# ----------- Token classification (context-only fallback retained) -----------

def classify_token(token: str, sent_lang: str, prev_lang="UNKNOWN") -> str:
    """
    Token classification without heuristics beyond sentence context.
    Returns the sentence language only (OpenLID token result preferred elsewhere).
    """
    t = token.strip()
    if not t or not WORD.search(t):
        return prev_lang

    # Fall back to sentence context only (no LU default)
    if sent_lang in ("LU","DE","FR","EN"):
        return sent_lang
    return prev_lang if prev_lang in ("LU","DE","FR","EN") else "UNKNOWN"


# ----------- Comparison tool (optional) -----------

def compare_lid_approaches(docs, output_comparison_file=None, ngram_size=3):
    """
    Compare two approaches:
    1. SENTENCE-level: OpenLID FastText
    2. WORD-level: Adaptive OpenLID context (+ lexicon fallback)
    Returns comparison statistics and (optionally) saves detailed results.
    """
    print("🔬 Comparing sentence-level OpenLID vs word-level adaptive LID...")

    all_sentences = []
    all_tokens = []
    doc_sent_mapping = []  # (doc_idx, sent_idx, token_start_idx, token_end_idx)

    for doc_idx, doc in enumerate(docs):
        tokenized_sents = doc.get("tokenized_sentences", [])
        if not tokenized_sents:
            continue

        for sent_idx, sent in enumerate(tokenized_sents):
            sent_tokens = []
            token_start = len(all_tokens)

            for tok in sent:
                text = tok
                sent_tokens.append(text)
                all_tokens.append(text)

            token_end = len(all_tokens)
            sentence_text = " ".join(sent_tokens)
            all_sentences.append(sentence_text)
            doc_sent_mapping.append((doc_idx, sent_idx, token_start, token_end, sentence_text))

    print(f"Processing {len(all_sentences)} sentences with {len(all_tokens)} tokens...")

    # Sentence-level predictions
    print("📝 Running sentence-level OpenLID...")
    sentence_results = batch_detect_with_openlid(all_sentences)

    # Word-level predictions (adaptive)
    print("🔤 Running adaptive word-level LID...")
    token_results = {}
    for idx in range(len(all_tokens)):
        token_results[idx] = adaptive_ngram_classification(all_tokens, idx)

    # Compare results
    comparison_data = []
    agreement_stats = {"agree": 0, "disagree": 0, "partial_agree": 0}

    for i, (doc_idx, sent_idx, tok_start, tok_end, sent_text) in enumerate(doc_sent_mapping):
        # Sentence-level result
        sent_result = sentence_results.get(i)
        sent_lang = sent_result["lang"] if sent_result else "UNKNOWN"
        sent_conf = sent_result["conf"] if sent_result else 0.0

        # N-gram-level results for this sentence
        word_langs = []
        word_confs = []
        tokens_in_sent = all_tokens[tok_start:tok_end]

        for tok_idx in range(tok_start, tok_end):
            tok_result = token_results.get(tok_idx)
            if tok_result:
                word_langs.append(tok_result["lang"])
                word_confs.append(tok_result.get("conf", 0.0))
            else:
                word_langs.append("UNKNOWN")
                word_confs.append(0.0)

        # Aggregate word predictions
        word_lang_counts = Counter(word_langs)
        majority_word_lang = word_lang_counts.most_common(1)[0][0] if word_lang_counts else "UNKNOWN"
        avg_word_conf = sum(word_confs) / len(word_confs) if word_confs else 0.0

        # Compare approaches
        if sent_lang == majority_word_lang and sent_lang != "UNKNOWN":
            agreement = "AGREE"
            agreement_stats["agree"] += 1
        elif sent_lang != "UNKNOWN" and majority_word_lang != "UNKNOWN":
            if sent_lang in word_langs:
                agreement = "PARTIAL"
                agreement_stats["partial_agree"] += 1
            else:
                agreement = "DISAGREE"
                agreement_stats["disagree"] += 1
        else:
            agreement = "UNKNOWN"

        comparison_entry = {
            "doc_idx": doc_idx,
            "sent_idx": sent_idx,
            "sentence": sent_text,
            "tokens": tokens_in_sent,
            "sentence_level": {
                "lang": sent_lang,
                "confidence": sent_conf
            },
            "word_level": {
                "majority_lang": majority_word_lang,
                "avg_confidence": avg_word_conf,
                "word_predictions": list(zip(tokens_in_sent, word_langs, word_confs)),
                "lang_distribution": dict(word_lang_counts)
            },
            "agreement": agreement
        }
        comparison_data.append(comparison_entry)

    # Print statistics
    total = len(comparison_data)
    print(f"\n📊 LID Approach Comparison Results:")
    print(f"Total sentences: {total}")
    if total:
        print(f"Agreement: {agreement_stats['agree']} ({agreement_stats['agree']/total*100:.1f}%)")
        print(f"Partial agreement: {agreement_stats['partial_agree']} ({agreement_stats['partial_agree']/total*100:.1f}%)")
        print(f"Disagreement: {agreement_stats['disagree']} ({agreement_stats['disagree']/total*100:.1f}%)")

    # Save detailed comparison if requested
    if output_comparison_file:
        with open(output_comparison_file, 'w', encoding='utf-8') as f:
            json.dump({
                "statistics": agreement_stats,
                "total_sentences": total,
                "detailed_results": comparison_data
            }, f, ensure_ascii=False, indent=2)
        print(f"💾 Detailed comparison saved to: {output_comparison_file}")

    return comparison_data, agreement_stats


# ----------- Sentence filtering and processing -----------

def filter_sentences_by_language(docs, use_llm=False, batch_size=50):
    """
    Improved sentence-level filtering with better confidence handling:
    - Keep sentences detected as LU with sufficient confidence
    - Route confident non-LU sentences to non-LU
    - Route uncertain sentences to non-LU (prevents LU bias)
    Returns (lu_docs, non_lu_docs).
    """
    lu_docs, non_lu_docs = [], []

    # Statistics for monitoring improvements
    stats = {"LU": 0, "DE": 0, "FR": 0, "EN": 0, "UNCERTAIN": 0}

    for doc in docs:
        text = doc.get("text", "")
        if not text.strip():
            continue

        # Simple sentence splitting on text field
        sentences = re.split(r'[.!?]+\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            continue

        # OpenLID sentence-level detection
        results = batch_detect_with_openlid(sentences, batch_size=min(batch_size, 200))

        lu_sentences, non_lu_sentences = [], []
        lu_idxs, non_lu_idxs = [], []
        for i, s in enumerate(sentences):
            r = results.get(i)
            if r and r.get("lang") == "LU":
                # LU sentences go to LU file (confidence already checked in batch_detect_with_openlid)
                lu_sentences.append(s)
                lu_idxs.append(i)
                stats["LU"] += 1
            elif r and r.get("lang") in ["DE", "FR", "EN"]:
                # Non-LU sentences with confident detection go to non-LU file
                non_lu_sentences.append(s)
                non_lu_idxs.append(i)
                stats[r.get("lang")] += 1
            else:
                # Uncertain sentences (no confident detection) go to non-LU file
                # This prevents defaulting everything to LU
                non_lu_sentences.append(s)
                non_lu_idxs.append(i)
                stats["UNCERTAIN"] += 1

        if lu_sentences:
            lu_doc = doc.copy()
            lu_doc["sentences"] = lu_sentences
            lu_doc["original_sentence_indices"] = lu_idxs
            lu_doc["language_filter"] = "LU"
            lu_docs.append(lu_doc)

        if non_lu_sentences:
            non_lu_doc = doc.copy()
            non_lu_doc["sentences"] = non_lu_sentences
            non_lu_doc["original_sentence_indices"] = non_lu_idxs
            non_lu_doc["language_filter"] = "non-LU"
            non_lu_docs.append(non_lu_doc)

    # Print statistics to monitor improvements
    total_sentences = sum(stats.values())
    if total_sentences > 0:
        print(f"    Language distribution: LU={stats['LU']} ({stats['LU']/total_sentences*100:.1f}%), "
              f"DE={stats['DE']} ({stats['DE']/total_sentences*100:.1f}%), "
              f"FR={stats['FR']} ({stats['FR']/total_sentences*100:.1f}%), "
              f"EN={stats['EN']} ({stats['EN']/total_sentences*100:.1f}%), "
              f"UNCERTAIN={stats['UNCERTAIN']} ({stats['UNCERTAIN']/total_sentences*100:.1f}%)")

    return lu_docs, non_lu_docs


def process_lu_batch_for_token_lid(docs):
    """Apply token-level LID only to Luxembourgish sentences (using LU as prior)."""
    for doc in docs:
        doc["lid_sentences"] = []
        doc["tokenized_sentences"] = []

        for sent_text in doc["sentences"]:
            # Tokenize the sentence text
            tokens = re.findall(r'\w+|[^\w\s]', sent_text)
            doc["tokenized_sentences"].append(tokens)

            # Apply adaptive token-level LID
            lids = []
            for i, token in enumerate(tokens):
                # Try adaptive n-gram classification first
                adaptive_result = adaptive_ngram_classification(tokens, i)
                if adaptive_result:
                    lids.append(adaptive_result["lang"])
                else:
                    # Fallback to lexicon-based classification (no LU bias)
                    lexical_result = classify_token_simple(token)
                    lids.append(lexical_result)

            doc["lid_sentences"].append(lids)
    return docs


def process_file(src_path, use_llm=False, batch_size=1000, max_docs=None):
    print(f"Processing {src_path.name} - only using 'text' field...")
    start = time.time()

    lu_path = src_path.parent / f"{src_path.stem}_LU.jsonl"
    non_lu_path = src_path.parent / f"{src_path.stem}_non_LU.jsonl"

    batch, total = [], 0
    total_lu_docs = total_non_lu_docs = 0

    with (src_path.open("r", encoding="utf-8") as f,
          lu_path.open("w", encoding="utf-8") as lu_file,
          non_lu_path.open("w", encoding="utf-8") as non_lu_file):

        for ln, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
                text = doc.get("text", "").strip()
                if not text:
                    continue
                # Only keep the text field and basic metadata
                simplified_doc = {
                    "id": doc.get("id", ""),
                    "section": doc.get("section", ""),
                    "text": text,
                    "public_date": doc.get("public_date", ""),
                    "lang": doc.get("lang", "ltz_Latn"),
                    "title": doc.get("title", "")
                }
                batch.append(simplified_doc)

                if len(batch) >= batch_size:
                    try:
                        lu_docs, non_lu_docs = filter_sentences_by_language(batch, use_llm, batch_size=min(batch_size, 200))
                        if lu_docs:
                            lu_docs = process_lu_batch_for_token_lid(lu_docs)
                            for d in lu_docs:
                                lu_file.write(json.dumps(d, ensure_ascii=False) + "\n")
                            total_lu_docs += len(lu_docs)
                        if non_lu_docs:
                            for d in non_lu_docs:
                                non_lu_file.write(json.dumps(d, ensure_ascii=False) + "\n")
                            total_non_lu_docs += len(non_lu_docs)
                        total += len(batch)
                        batch = []
                        elapsed = time.time() - start
                        print(f"  {total} docs processed ... LU: {total_lu_docs}, non-LU: {total_non_lu_docs} ({total/max(elapsed,1):.1f}/s)")
                    except Exception as batch_error:
                        print(f"Batch processing error at line {ln}: {batch_error}")
                        batch = []
                        continue

                if max_docs and total >= max_docs:
                    break

            except Exception as e:
                print(f"Line {ln} error: {e}")
                continue

        # Remaining
        if batch:
            try:
                lu_docs, non_lu_docs = filter_sentences_by_language(batch, use_llm, batch_size=min(batch_size, 200))
                if lu_docs:
                    lu_docs = process_lu_batch_for_token_lid(lu_docs)
                    for d in lu_docs:
                        lu_file.write(json.dumps(d, ensure_ascii=False) + "\n")
                    total_lu_docs += len(lu_docs)
                if non_lu_docs:
                    for d in non_lu_docs:
                        non_lu_file.write(json.dumps(d, ensure_ascii=False) + "\n")
                    total_non_lu_docs += len(non_lu_docs)
                total += len(batch)
            except Exception as final_batch_error:
                print(f"Final batch processing error: {final_batch_error}")
                print(f"Skipped {len(batch)} documents in final batch")

    elapsed = time.time() - start
    print(f"  Done {src_path.name}: {total} total docs in {elapsed:.1f}s ({total/max(elapsed,1):.1f}/s)")
    print(f"    -> {total_lu_docs} LU docs written to {lu_path.name}")
    print(f"    -> {total_non_lu_docs} non-LU docs written to {non_lu_path.name}")
    print(f"    -> Original file {src_path.name} preserved")

    return total_lu_docs + total_non_lu_docs


def main():
    ap = argparse.ArgumentParser("OpenLID sentence filtering with LU token-level LID (improved)")
    ap.add_argument("--use-llm", action="store_true", help="Use LLM backup for uncertain sentences")
    ap.add_argument("--batch-size", type=int, default=1000, help="Batch size for I/O and detector calls")
    ap.add_argument("--max-docs", type=int)
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--compare-lid", action="store_true", help="Compare sentence-level vs word-level LID approaches")
    ap.add_argument("--comparison-output", default="lid_comparison_results.json", help="Output file for LID comparison")
    args = ap.parse_args()

    cfg_path = Path(os.environ.get("CONFIG_PATH", args.config))
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    paths = cfg["paths"]

    src_dir = Path(paths["out_raw"])
    files = list(sorted(src_dir.glob("*.jsonl")))
    # Only process files that don't have _LU or _non_LU suffixes (avoid recursive processing)
    files = [f for f in files if not f.stem.endswith(('_LU', '_non_LU'))]
    if not files:
        print(f"No files in {src_dir}")
        return

    # Load documents for comparison if requested
    if args.compare_lid:
        print("🔍 Loading documents for LID approach comparison...")
        all_docs = []
        for src in files[:1]:  # Test on first file only for comparison
            with open(src, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    if args.max_docs and len(all_docs) >= args.max_docs:
                        break
                    try:
                        doc = json.loads(line.strip())
                        all_docs.append(doc)
                    except json.JSONDecodeError as e:
                        print(f"Skipping malformed JSON at {src}:{line_num}: {e}")
                        continue

        print(f"📊 Loaded {len(all_docs)} documents for comparison")
        comparison_data, stats = compare_lid_approaches(all_docs, args.comparison_output)
        return

    # Regular processing
    total = 0
    for src in files:
        total += process_file(src, args.use_llm, args.batch_size, args.max_docs)

    print("Processing complete. Total docs processed:", total)
    print("Files processed: *_LU.jsonl (with token-level LID) and *_non_LU.jsonl")


if __name__ == "__main__":
    import time
    main()


