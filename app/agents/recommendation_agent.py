"""
Recommendation Agent
--------------------
Uses Retrieval-Augmented Generation (RAG) to provide personalised,
non-medical lifestyle advice based on:
  - The predicted KL grade from the Diagnostic Agent
  - User-reported pain level (0-10)
  - User-reported mobility level

Architecture:
  1. A local knowledge base of lifestyle advice documents is embedded using
     Sentence-Transformers and stored as a simple NumPy-based vector store.
  2. At query time, we embed the user's context, retrieve the top-k most
     relevant passages, and compose a structured recommendation.
  3. Exercise video URLs are fetched from the database (ExerciseVideo table)
     filtered by the KL grade.

NOTE: This is a retrieval-only RAG (no LLM generation step) to keep the
system deterministic and avoid hallucinated medical advice.
"""

import os
import json
import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.models.library import ExerciseVideo

# ── Configuration ─────────────────────────────────────────────────────────────
VECTOR_STORE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "ml_assets", "vector_store"
)
EMBEDDINGS_FILE = os.path.join(VECTOR_STORE_DIR, "embeddings.npy")
DOCUMENTS_FILE = os.path.join(VECTOR_STORE_DIR, "documents.json")
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  # Lightweight, fast, 384-dim

# ── Singleton Loader ─────────────────────────────────────────────────────────
_embedding_model = None
_doc_embeddings = None
_documents = None


def _load_embedding_model() -> SentenceTransformer:
    """Lazy-load the sentence-transformer model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def _load_vector_store():
    """Load the pre-computed document embeddings and their text."""
    global _doc_embeddings, _documents

    if _doc_embeddings is None:
        if os.path.exists(EMBEDDINGS_FILE) and os.path.exists(DOCUMENTS_FILE):
            _doc_embeddings = np.load(EMBEDDINGS_FILE)
            with open(DOCUMENTS_FILE, "r", encoding="utf-8") as f:
                _documents = json.load(f)
        else:
            # If vector store hasn't been built yet, use the fallback knowledge base
            _documents = _get_fallback_knowledge_base()
            model = _load_embedding_model()
            texts = [doc["text"] for doc in _documents]
            _doc_embeddings = model.encode(texts, show_progress_bar=False)
            # Persist for next time
            os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
            np.save(EMBEDDINGS_FILE, _doc_embeddings)
            with open(DOCUMENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(_documents, f, indent=2)


def _get_fallback_knowledge_base() -> List[dict]:
    """
    Built-in knowledge base of lifestyle advice passages.
    Each document is tagged with the KL grades it's most relevant to.
    """
    return [
        {
            "text": "For early-stage knee osteoarthritis (KL Grade 0-1), maintaining an active lifestyle is key. Low-impact exercises such as swimming, cycling, and walking help keep the joint mobile without excessive stress. Aim for 30 minutes of moderate activity most days of the week.",
            "kl_grades": [0, 1],
            "category": "exercise",
        },
        {
            "text": "Weight management is one of the most effective strategies for knee OA. Every pound of body weight lost removes approximately 4 pounds of pressure from the knee joint. A balanced diet rich in anti-inflammatory foods (fish, nuts, leafy greens) can support joint health.",
            "kl_grades": [0, 1, 2, 3, 4],
            "category": "nutrition",
        },
        {
            "text": "For moderate knee osteoarthritis (KL Grade 2-3), focus on strengthening the quadriceps and hamstrings to provide better support for the knee joint. Isometric exercises, leg presses with light weight, and seated leg extensions are recommended. Avoid high-impact activities like running or jumping.",
            "kl_grades": [2, 3],
            "category": "exercise",
        },
        {
            "text": "Flexibility exercises are important at all stages. Gentle stretching of the hamstrings, calves, and hip flexors can reduce stiffness. Yoga and tai chi have been shown to improve balance and reduce pain in knee OA patients.",
            "kl_grades": [0, 1, 2, 3, 4],
            "category": "flexibility",
        },
        {
            "text": "For severe knee osteoarthritis (KL Grade 4), focus on pain management and maintaining as much mobility as possible. Water-based exercises (aqua therapy) are excellent as buoyancy reduces joint loading by up to 90%. Use assistive devices if needed and consult your healthcare provider about pain management options.",
            "kl_grades": [3, 4],
            "category": "exercise",
        },
        {
            "text": "Heat therapy before exercise can help loosen stiff joints, while cold therapy after activity can reduce swelling. Apply heat for 15-20 minutes before exercise and ice for 10-15 minutes after. This is particularly helpful for KL Grade 2-4.",
            "kl_grades": [2, 3, 4],
            "category": "pain_management",
        },
        {
            "text": "Proper footwear with good arch support and cushioning can significantly reduce knee stress. Consider orthotic insoles for additional support. Avoid high heels and flat shoes without support. This applies to all stages of knee OA.",
            "kl_grades": [0, 1, 2, 3, 4],
            "category": "lifestyle",
        },
        {
            "text": "Sleep quality affects pain perception. Ensure 7-9 hours of quality sleep. Use a pillow between the knees when sleeping on your side to maintain proper alignment. A consistent sleep schedule helps manage chronic pain associated with moderate to severe OA.",
            "kl_grades": [2, 3, 4],
            "category": "lifestyle",
        },
    ]


# ── Core RAG Functions ────────────────────────────────────────────────────────

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between a query vector and a matrix of document vectors."""
    dot = np.dot(b, a)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b, axis=1)
    return dot / (norm_a * norm_b + 1e-10)


def retrieve_relevant_passages(
    kl_grade: int,
    pain_level: Optional[int] = None,
    mobility_level: Optional[str] = None,
    top_k: int = 3,
) -> List[str]:
    """
    Retrieve the top-k most relevant advice passages for the given context.

    Args:
        kl_grade: Predicted KL grade (0-4).
        pain_level: Self-reported pain (0-10), optional.
        mobility_level: e.g. "limited", "moderate", "good", optional.
        top_k: Number of passages to retrieve.

    Returns:
        List of relevant advice text strings.
    """
    _load_vector_store()
    model = _load_embedding_model()

    # Build a natural-language query from the user's context
    query_parts = [f"Knee osteoarthritis KL grade {kl_grade}"]
    if pain_level is not None:
        severity = "mild" if pain_level <= 3 else "moderate" if pain_level <= 6 else "severe"
        query_parts.append(f"{severity} pain level {pain_level} out of 10")
    if mobility_level:
        query_parts.append(f"{mobility_level} mobility")
    query_parts.append("lifestyle advice exercise recommendation")

    query = ". ".join(query_parts)
    query_embedding = model.encode(query, show_progress_bar=False)

    # Compute similarities
    similarities = _cosine_similarity(query_embedding, _doc_embeddings)

    # Boost scores for documents that explicitly match the KL grade
    for i, doc in enumerate(_documents):
        if kl_grade in doc.get("kl_grades", []):
            similarities[i] += 0.15  # Relevance boost

    # Get top-k indices
    top_indices = np.argsort(similarities)[::-1][:top_k]

    return [_documents[i]["text"] for i in top_indices]


def get_exercise_videos(kl_grade: int, db: Session) -> List[str]:
    """
    Fetch exercise video S3 URLs from the database for the given KL grade.

    Args:
        kl_grade: The predicted KL grade.
        db: SQLAlchemy database session.

    Returns:
        List of S3 video URLs.
    """
    videos = (
        db.query(ExerciseVideo)
        .filter(
            ExerciseVideo.kl_grade_min <= kl_grade,
            ExerciseVideo.kl_grade_max >= kl_grade,
        )
        .all()
    )
    return [v.s3_url for v in videos]


def generate_recommendation(
    kl_grade: int,
    db: Session,
    pain_level: Optional[int] = None,
    mobility_level: Optional[str] = None,
) -> dict:
    """
    Full recommendation pipeline.

    Args:
        kl_grade: Predicted KL grade from the Diagnostic Agent.
        db: Database session for fetching exercise videos.
        pain_level: Optional self-reported pain (0-10).
        mobility_level: Optional mobility descriptor.

    Returns:
        dict with keys:
          - "recommendation": str — compiled lifestyle advice
          - "exercise_video_urls": List[str] — matching S3 video URLs
    """
    # 1. Retrieve relevant passages via RAG
    passages = retrieve_relevant_passages(kl_grade, pain_level, mobility_level)

    # 2. Compose a structured recommendation from retrieved passages
    header = f"Based on your KL Grade {kl_grade} diagnosis"
    if pain_level is not None:
        header += f" and reported pain level of {pain_level}/10"
    if mobility_level:
        header += f" with {mobility_level} mobility"
    header += ", here are personalised lifestyle recommendations:\n\n"

    body = "\n\n".join(
        [f"• {passage}" for passage in passages]
    )

    disclaimer = (
        "\n\n⚠️ Disclaimer: These are general lifestyle suggestions and do not "
        "constitute medical advice. Please consult your healthcare provider "
        "before starting any new exercise programme."
    )

    recommendation_text = header + body + disclaimer

    # 3. Fetch matching exercise videos from the database
    video_urls = get_exercise_videos(kl_grade, db)

    return {
        "recommendation": recommendation_text,
        "exercise_video_urls": video_urls,
    }
