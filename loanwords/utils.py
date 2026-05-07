import xml.etree.ElementTree as ET
import pandas as pd
from typing import List, Iterable, Any
from tqdm import tqdm
import pandas as pd


def load_lod_dataset(xml_path: str = 'loanwords/data/new_lod-art.xml'):
    """
    Parse the LOD XML and return entries with translations, clarifiers, and synonyms.
    """
    languages = ['de', 'fr', 'en', 'pt']

    tree = ET.parse(xml_path)
    root = tree.getroot()
    entries = []

    for entry in tqdm(root.findall('entry')):
        lemma = entry.findtext('lemma')
        part_of_speech = entry.findtext('./microStructure/partOfSpeech') or entry.findtext('.//partOfSpeech')
        categories = [c.text for c in entry.findall('./categories/category') if c.text] or None

        # --- START: SPELLING VARIATIONS ---
        spelling_variations = []
        seen = set()

        # 1) normal spelling links
        for il in entry.findall(".//infobox[@label='spelling']//internalLink"):
            if il.text and (t := il.text.strip()):
                if t not in seen:
                    seen.add(t)
                    spelling_variations.append(t)

        # 2) variant(s) links anywhere under an infobox
        for ilist in entry.findall(".//infobox/infoboxList"):
            t_attr = (ilist.get("type") or "").strip().lower()
            if t_attr.startswith("variant"):  # catches 'variant', 'variants', etc.
                for il in ilist.findall(".//internalLink"):
                    if il.text and (t := il.text.strip()):
                        if t not in seen:
                            seen.add(t)
                            spelling_variations.append(t)

        if not spelling_variations:
            spelling_variations = None
        # --- END: SPELLING VARIATIONS ---

        # --- START: WORD FORMS ---
        word_forms_set = set()

        # from <lemma> text and its nRuleForm attribute
        lemma_el = entry.find('lemma')
        if lemma_el is not None:
            if lemma_el.text and lemma_el.text.strip():
                word_forms_set.add(lemma_el.text.strip())
            nrf = lemma_el.attrib.get('nRuleForm')
            if nrf and nrf.strip():
                word_forms_set.add(nrf.strip())

        # from <inflection><form> text and nRuleForm attribute(s)
        for form_el in entry.findall('.//inflection//form'):
            if form_el.text and form_el.text.strip():
                word_forms_set.add(form_el.text.strip())
            nrf = form_el.attrib.get('nRuleForm')
            if nrf and nrf.strip():
                word_forms_set.add(nrf.strip())

        # from <pastParticiple> (can appear multiple times)
        for pp_el in entry.findall('.//pastParticiple'):
            if pp_el.text and pp_el.text.strip():
                word_forms_set.add(pp_el.text.strip())

        word_forms = sorted(word_forms_set) if word_forms_set else None
        # --- END: WORD FORMS ---

        meanings = entry.findall('.//meaning')

        if meanings:
            for meaning in meanings:
                meaning_id = meaning.attrib.get('id', '')
                meaning_number = meaning.findtext('number')

                translations = {lang: None for lang in languages}
                clarifiers = {lang: None for lang in languages}

                for tl in meaning.findall('targetLanguage'):
                    lang = tl.attrib.get('lang')
                    if lang not in translations:
                        # Optionally include unexpected languages
                        translations[lang] = None
                        clarifiers[lang] = None
                    translation_elements = [t.text for t in tl.findall('translation') if t.text]
                    clarifier_element = tl.findtext('semanticClarifier')
                    if translation_elements:
                        translations[lang] = translation_elements
                    if clarifier_element:
                        clarifiers[lang] = clarifier_element

                synonyms = [syn.text for syn in meaning.findall('.//synonyms/synonym') if syn.text]
                attributes = [a.text.strip() for a in meaning.findall('attribute') if a.text and a.text.strip()] or None


                row = {
                    'Lemma': lemma,
                    'MeaningID': meaning_id,
                    'MeaningNumber': meaning_number,
                    'Synonyms': synonyms,
                    'PartOfSpeech': part_of_speech,
                    'Categories': categories,
                    'Attributes': attributes,
                    'word_forms': word_forms,
                    'spelling_variation': spelling_variations,
                }
                for lang in translations:
                    row[f'Translation_{lang.upper()}'] = translations[lang]
                    row[f'Clarifier_{lang.upper()}'] = clarifiers[lang]

                entries.append(row)
        else:
            # Fallback when there are no meanings
            row = {
                'Lemma': lemma,
                'MeaningID': None,
                'MeaningNumber': None,
                'Synonyms': None,
                'PartOfSpeech': part_of_speech,
                'Categories': categories,
                'Attributes': None,
                'word_forms': word_forms,
                'spelling_variation': spelling_variations,
            }
            for lang in languages:
                row[f'Translation_{lang.upper()}'] = None
                row[f'Clarifier_{lang.upper()}'] = None

            entries.append(row)

    entries = pd.DataFrame(entries)
    entries = augment_with_spelling_variations(entries, id_suffix='_SPELL_VAR')

    return entries


def _as_list(x: Any) -> List[str]:
    """Coerce cell content to a clean list of strings, ignoring Nones/NaNs."""
    if x is None or (isinstance(x, float) and pd.isna(x)):  # NaN
        return []
    if isinstance(x, str):
        return [x.strip()] if x.strip() else []
    if isinstance(x, Iterable):
        out = []
        for v in x:
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            s = str(v).strip()
            if s:
                out.append(s)
        return out
    return []

def augment_with_spelling_variations(df: pd.DataFrame, id_suffix: str = "_SPELL_VAR") -> pd.DataFrame:
    """
    1) Adds spelling variations into each row's `word_forms`.
    2) Duplicates rows for each spelling variant, using the variant as `Lemma`
       and appending `id_suffix` to `MeaningID`.

    Assumes columns: 'Lemma', 'MeaningID', 'word_forms', 'spelling_variation' exist.
    Returns a NEW DataFrame with the extra rows appended.
    """

    df = df.copy()

    # --- Step 1: merge spelling variations into word_forms for each row ---
    merged_word_forms = []
    for _, row in df.iterrows():
        wf = set(_as_list(row.get("word_forms")))
        sv = set(_as_list(row.get("spelling_variation")))
        # Merge and keep stable, readable order
        merged = sorted(wf.union(sv))
        merged_word_forms.append(merged if merged else None)
    df["word_forms"] = merged_word_forms

    # --- Step 2: create new rows for each spelling variation ---
    new_rows = []
    existing_keys = set(zip(df["Lemma"].astype(str), df["MeaningID"].astype(str)))

    for _, row in df.iterrows():
        base_lemma = (row.get("Lemma") or "").strip()
        meaning_id = (row.get("MeaningID") or "").strip()
        variants = _as_list(row.get("spelling_variation"))

        for var in variants:
            if not var or var == base_lemma:
                continue  # skip identity/no-op variants

            # Avoid duplicate (Lemma, MeaningID+suffix) pairs if already present
            new_meaning_id = f"{meaning_id}{id_suffix}"
            key = (var, new_meaning_id)
            if key in existing_keys:
                continue

            # Build the new row as a dict
            new_row = row.to_dict()

            # Update changed fields
            new_row["Lemma"] = var
            new_row["MeaningID"] = new_meaning_id

            # Keep the merged word_forms, but ensure the variant is included
            wf = set(_as_list(new_row.get("word_forms")))
            wf.add(var)
            new_row["word_forms"] = sorted(wf) if wf else None

            new_rows.append(new_row)
            existing_keys.add(key)

    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

    return df
