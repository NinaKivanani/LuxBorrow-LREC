#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Create a clean version of the RTL JSON file by removing documents with empty text.
"""

import json
from pathlib import Path

def create_clean_json():
    original_file = Path("data/rtl_raw/all_cleaned_news_articles_lu.json")
    clean_file = Path("data/rtl_raw/all_cleaned_news_articles_lu_clean.json")
    
    print(f"Reading original file: {original_file}")
    
    with original_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"Original documents: {len(data)}")
    
    # Filter out documents with empty text
    clean_data = []
    empty_count = 0
    
    for doc in data:
        text = doc.get("text", "").strip()
        text_l = doc.get("text_l", "").strip()
        
        # Keep document if it has substantial text content
        if text or text_l:
            clean_data.append(doc)
        else:
            empty_count += 1
    
    print(f"Empty documents removed: {empty_count}")
    print(f"Clean documents: {len(clean_data)}")
    
    # Save clean version
    print(f"Saving clean file: {clean_file}")
    with clean_file.open("w", encoding="utf-8") as f:
        json.dump(clean_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Clean JSON file created successfully!")
    print(f"   Original: {len(data)} documents")
    print(f"   Clean: {len(clean_data)} documents")
    print(f"   Removed: {empty_count} empty documents")

if __name__ == "__main__":
    create_clean_json()
