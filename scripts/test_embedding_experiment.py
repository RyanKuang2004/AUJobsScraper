import sys
import os
import numpy as np
import re

# Add project root to path
sys.path.append(os.getcwd())

from jobly.utils import scraper_utils

def test_embeddings():
    print("Loading model...")
    model, role_embeddings = scraper_utils._get_embedding_model()
    roles = list(scraper_utils.ROLE_TAXONOMY.keys())
    
    # Find index of "Graduate Program"
    try:
        grad_idx = roles.index("Graduate Program")
        grad_embedding = role_embeddings[grad_idx]
    except ValueError:
        print("Error: 'Graduate Program' not found in taxonomy")
        return

    test_cases = [
        "ANAO Graduate Program",
        "Graduate Program - Multi-Discipline",
        "Graduate Development Programme"
    ]
    
    print(f"\nComparing against target role: 'Graduate Program'")
    print("-" * 60)
    
    for title in test_cases:
        print(f"\nJob Title: '{title}'")
        
        # --- 1. Raw / Minimal Cleaning (User's suggestion) ---
        # Just lowercase and basic whitespace, keep all words
        raw_text = title.lower().strip()
        raw_emb = model.embed_query(raw_text)
        
        # Calculate similarity with "Graduate Program"
        raw_sim = np.dot(raw_emb, grad_embedding) / (np.linalg.norm(raw_emb) * np.linalg.norm(grad_embedding))
        
        # --- 2. Current Cleaning Logic ---
        # Replicate the cleaning steps from extract_job_role
        cleaned_text = title.lower()
        # Remove company name (none here)
        # Remove parens
        cleaned_text = re.sub(r'\([^)]*\)', ' ', cleaned_text)
        # Remove years
        cleaned_text = re.sub(r'\b20\d{2}(?:[\s/-]*\d{2,4})?\b', ' ', cleaned_text)
        # Remove stop words (THIS IS THE KEY PART)
        for word in scraper_utils.STOP_WORDS:
            cleaned_text = re.sub(rf'\b{re.escape(word)}\b', ' ', cleaned_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        print(f"  [Raw Text]: '{raw_text}'")
        print(f"  -> Similarity to 'Graduate Program': {raw_sim:.4f}")
        
        print(f"  [Cleaned Text]: '{cleaned_text}'")
        if cleaned_text:
            clean_emb = model.embed_query(cleaned_text)
            clean_sim = np.dot(clean_emb, grad_embedding) / (np.linalg.norm(clean_emb) * np.linalg.norm(grad_embedding))
            print(f"  -> Similarity to 'Graduate Program': {clean_sim:.4f}")
        else:
            print(f"  -> Similarity to 'Graduate Program': 0.0000 (Empty text)")

if __name__ == "__main__":
    test_embeddings()
