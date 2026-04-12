#!/usr/bin/env python3
"""
Generate parametric embeddings from the knowledge base JSON file.
This script uses sentence-transformers to create embeddings for the RAG system.
"""

import json
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import os

def load_knowledge_base(file_path: str) -> List[Dict[str, Any]]:
    """Load the knowledge base from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        knowledge_base = json.load(f)
    return knowledge_base

def generate_embeddings(knowledge_base: List[Dict[str, Any]]) -> np.ndarray:
    """Generate embeddings for the knowledge base using sentence-transformers."""
    
    # Load the sentence transformer model
    print("Loading sentence transformer model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Extract text descriptions for embedding
    texts = []
    for item in knowledge_base:
        # Combine relevant fields into a single text for embedding
        text = f"{item['category']}: {item['action']}. " \
               f"Frequency: {item['frequency']}. " \
               f"Duration: {item['duration_min']} minutes. " \
               f"Intensity: {item['intensity']}. " \
               f"KL grades: {item['kl_grade_min']}-{item['kl_grade_max']}. " \
               f"Pain threshold: {item['pain_threshold']}. " \
               f"Mobility required: {item['mobility_req']}."
        texts.append(text)
    
    # Generate embeddings
    print(f"Generating embeddings for {len(texts)} items...")
    embeddings = model.encode(texts, show_progress_bar=True)
    
    return embeddings

def save_embeddings(embeddings: np.ndarray, output_path: str):
    """Save embeddings to a numpy file."""
    print(f"Saving embeddings to {output_path}...")
    np.save(output_path, embeddings)
    print(f"✅ Successfully saved {embeddings.shape[0]} embeddings with dimension {embeddings.shape[1]}")

def main():
    # File paths
    knowledge_base_path = 'app/ml_assets/vector_store/parametric_knowledge.json'
    embeddings_path = 'app/ml_assets/vector_store/parametric_embeddings.npy'
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(embeddings_path), exist_ok=True)
    
    # Load knowledge base
    print("Loading knowledge base...")
    knowledge_base = load_knowledge_base(knowledge_base_path)
    print(f"✅ Loaded {len(knowledge_base)} knowledge items")
    
    # Generate embeddings
    embeddings = generate_embeddings(knowledge_base)
    
    # Save embeddings
    save_embeddings(embeddings, embeddings_path)
    
    print("\n🎉 Embedding generation complete!")
    print(f"📊 Generated {embeddings.shape[0]} embeddings")
    print(f"📏 Embedding dimension: {embeddings.shape[1]}")
    print(f"💾 Saved to: {embeddings_path}")

if __name__ == "__main__":
    main()