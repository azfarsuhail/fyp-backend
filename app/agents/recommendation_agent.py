"""
Recommendation Agent — Parametric RAG
--------------------------------------
A **hallucination-free** recommendation system that returns structured,
typed parameters instead of free-text prose.

Why Parametric?
  Traditional RAG retrieves text chunks and feeds them to an LLM which can
  hallucinate, rephrase inaccurately, or invent medical claims. This system
  eliminates that risk entirely:

  1. The knowledge base is a **structured parameter table** — every piece of
     advice is a typed record with fixed fields (category, action, frequency,
     duration, intensity, contraindications, evidence_level).
  2. Retrieval uses sentence-transformer embeddings + cosine similarity to
     find the most relevant records for the patient's context.
  3. The output is a **list of structured JSON objects** — no generation,
     no paraphrasing, no hallucination. The mobile app renders the parameters
     directly into UI cards.

Architecture:
  Input:  (kl_grade, pain_level, mobility_level)
  Step 1: Parametric filter — hard-filter knowledge base by KL grade range
  Step 2: Semantic ranking — embed user context, rank remaining records
  Step 3: Pain/mobility modifiers — adjust intensity & frequency parameters
  Step 4: Assemble structured output — typed dicts, not prose
  Step 5: Fetch exercise videos from DB
  Output: { lifestyle_plan: [...], exercise_videos: [...], warnings: [...] }
"""

import os
import json
import numpy as np
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.models.library import ExerciseVideo

# ── Configuration ─────────────────────────────────────────────────────────────
VECTOR_STORE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "ml_assets", "vector_store"
)
EMBEDDINGS_FILE = os.path.join(VECTOR_STORE_DIR, "parametric_embeddings.npy")
KNOWLEDGE_FILE = os.path.join(VECTOR_STORE_DIR, "parametric_knowledge.json")
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# ── Singleton Loader ─────────────────────────────────────────────────────────
_embedding_model = None
_kb_embeddings = None
_knowledge_base = None


def _load_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def _load_knowledge_base():
    """Load the parametric knowledge base with embeddings from files."""
    global _kb_embeddings, _knowledge_base

    if _knowledge_base is not None:
        return

    if not os.path.exists(EMBEDDINGS_FILE) or not os.path.exists(KNOWLEDGE_FILE):
        raise FileNotFoundError(
            f"Vector store files not found. Please run: python scripts/generate_embeddings.py"
        )

    # Load embeddings
    _kb_embeddings = np.load(EMBEDDINGS_FILE)
    
    # Load knowledge base
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
        _knowledge_base = json.load(f)
    
    # Verify embeddings match knowledge base
    if len(_kb_embeddings) != len(_knowledge_base):
        raise ValueError(
            f"Embedding count ({len(_kb_embeddings)}) doesn't match "
            f"knowledge base count ({len(_knowledge_base)}). "
            "Please regenerate embeddings."
        )


# ── WARNINGS TABLE (deterministic, grade-based) ──────────────────────────────

_WARNINGS = {
    0: [],
    1: [
        {"level": "info", "message": "Early signs detected. Preventive measures can significantly slow progression."},
    ],
    2: [
        {"level": "caution", "message": "Avoid high-impact activities that may accelerate joint deterioration."},
        {"level": "info", "message": "Strengthening exercises are strongly recommended at this stage."},
    ],
    3: [
        {"level": "caution", "message": "Moderate OA detected. Consult your GP before starting new exercise routines."},
        {"level": "warning", "message": "Avoid exercises that cause sharp or increasing pain during the session."},
    ],
    4: [
        {"level": "warning", "message": "Severe OA detected. A GP referral for specialist assessment is recommended."},
        {"level": "caution", "message": "Focus on pain management and gentle mobility. Avoid weight-bearing stress."},
        {"level": "info", "message": "Aqua therapy and seated exercises are the safest options at this stage."},
    ],
}


# ── Core Parametric RAG Functions ─────────────────────────────────────────────

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity between a query vector and a matrix of document vectors."""
    dot = np.dot(b, a)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b, axis=1)
    return dot / (norm_a * norm_b + 1e-10)


def _hard_filter(
    records: List[Dict[str, Any]],
    kl_grade: int,
    pain_level: Optional[int],
    mobility_level: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Step 1: Hard parametric filter.
    Only keep records whose KL grade range covers the patient's grade,
    whose pain threshold is safe, and whose mobility requirement is met.
    """
    mobility_rank = {"limited": 0, "moderate": 1, "good": 2}
    user_mobility = mobility_rank.get(mobility_level, 2)  # Default: assume good

    filtered = []
    for rec in records:
        # KL grade range check
        if not (rec["kl_grade_min"] <= kl_grade <= rec["kl_grade_max"]):
            continue

        # Pain threshold check — skip exercises too intense for current pain
        if pain_level is not None and rec.get("pain_threshold") is not None:
            if pain_level > rec["pain_threshold"]:
                continue

        # Mobility requirement check
        req = rec.get("mobility_req")
        if req is not None:
            req_rank = mobility_rank.get(req, 0)
            if user_mobility < req_rank:
                continue

        filtered.append(rec)

    return filtered


def _semantic_rank(
    records: List[Dict[str, Any]],
    indices: List[int],
    kl_grade: int,
    pain_level: Optional[int],
    mobility_level: Optional[str],
    top_k: int = 6,
) -> List[Dict[str, Any]]:
    """
    Step 2: Semantic ranking of pre-filtered records.
    Uses embeddings to rank by relevance to the patient's specific context.
    """
    if not records:
        return []

    _load_knowledge_base()

    # Build context query
    parts = [f"knee osteoarthritis KL grade {kl_grade}"]
    if pain_level is not None:
        severity = "mild" if pain_level <= 3 else "moderate" if pain_level <= 6 else "severe"
        parts.append(f"{severity} pain")
    if mobility_level:
        parts.append(f"{mobility_level} mobility")

    query_text = ". ".join(parts)
    query_embedding = _load_embedding_model().encode(query_text, show_progress_bar=False)

    # Get embeddings for only the filtered records
    filtered_embeddings = _kb_embeddings[indices]
    similarities = _cosine_similarity(query_embedding, filtered_embeddings)

    # Sort by similarity, take top_k
    ranked_idx = np.argsort(similarities)[::-1][:top_k]
    return [records[i] for i in ranked_idx]


def _apply_modifiers(
    records: List[Dict[str, Any]],
    pain_level: Optional[int],
    mobility_level: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Step 3: Apply pain/mobility modifiers to adjust parameters.
    This is deterministic — no LLM, just rule-based adjustments.
    """
    modified = []
    for rec in records:
        rec = rec.copy()  # Don't mutate the knowledge base

        # High pain → reduce intensity and duration
        if pain_level is not None and pain_level >= 7 and rec.get("intensity"):
            intensity_map = {"high": "moderate", "moderate": "low", "low": "low"}
            rec["intensity"] = intensity_map.get(rec["intensity"], rec["intensity"])
            if rec.get("duration_min"):
                rec["duration_min"] = max(5, rec["duration_min"] - 10)
            rec["_modifier_applied"] = "Adjusted for high pain level"

        # Limited mobility → reduce frequency
        if mobility_level == "limited" and rec.get("frequency"):
            freq_map = {"5x/week": "3x/week", "3x/week": "2x/week", "daily": "3x/week"}
            original = rec["frequency"]
            rec["frequency"] = freq_map.get(original, original)
            if rec["frequency"] != original:
                rec["_modifier_applied"] = rec.get("_modifier_applied", "") + " Reduced frequency for limited mobility."

        modified.append(rec)

    return modified


def _format_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a knowledge base record into a clean output parameter set.
    Strips internal fields (semantic_key, etc.) and returns only
    what the mobile app needs to render a recommendation card.
    """
    output = {
        "id": rec["id"],
        "category": rec["category"],
        "action": rec["action"],
        "evidence_level": rec["evidence_level"],
        "source": rec["source"],
    }
    # Only include non-None optional fields
    if rec.get("frequency"):
        output["frequency"] = rec["frequency"]
    if rec.get("duration_min") is not None:
        output["duration_min"] = rec["duration_min"]
    if rec.get("intensity"):
        output["intensity"] = rec["intensity"]
    if rec.get("contraindications"):
        output["contraindications"] = rec["contraindications"]
    if rec.get("_modifier_applied"):
        output["modifier_note"] = rec["_modifier_applied"].strip()

    return output


def get_exercise_videos(kl_grade: int, db: Session) -> List[Dict[str, Any]]:
    """
    Fetch exercise videos from the DB as structured objects (not just URLs).
    """
    videos = (
        db.query(ExerciseVideo)
        .filter(
            ExerciseVideo.kl_grade_min <= kl_grade,
            ExerciseVideo.kl_grade_max >= kl_grade,
        )
        .all()
    )
    return [
        {
            "video_id": v.video_id,
            "title": v.title,
            "s3_url": v.s3_url,
            "category": v.category,
            "difficulty": v.difficulty,
            "duration_seconds": v.duration_seconds,
        }
        for v in videos
    ]


def generate_recommendation(
    kl_grade: int,
    db: Session,
    pain_level: Optional[int] = None,
    mobility_level: Optional[str] = None,
) -> dict:
    """
    Full parametric recommendation pipeline.

    Returns a structured, hallucination-free output:
    {
        "lifestyle_plan": [
            {
                "id": "EX-001",
                "category": "exercise",
                "action": "Perform low-impact aerobic exercise...",
                "frequency": "5x/week",
                "duration_min": 30,
                "intensity": "moderate",
                "evidence_level": "strong",
                "source": "OARSI 2019 Guidelines"
            },
            ...
        ],
        "warnings": [
            {"level": "caution", "message": "..."}
        ],
        "exercise_videos": [
            {"video_id": 1, "title": "...", "s3_url": "...", ...}
        ],
        "recommendation": "... (legacy text summary for backward compat)"
    }
    """
    _load_knowledge_base()

    # ── Step 1: Hard parametric filter ────────────────────────────────────
    all_records = _knowledge_base
    filtered = _hard_filter(all_records, kl_grade, pain_level, mobility_level)

    # Track original indices for embedding lookup
    filtered_indices = []
    for rec in filtered:
        for i, orig in enumerate(all_records):
            if orig["id"] == rec["id"]:
                filtered_indices.append(i)
                break

    # ── Step 2: Semantic ranking ──────────────────────────────────────────
    ranked = _semantic_rank(filtered, filtered_indices, kl_grade, pain_level, mobility_level)

    # ── Step 3: Apply pain/mobility modifiers ─────────────────────────────
    adjusted = _apply_modifiers(ranked, pain_level, mobility_level)

    # ── Step 4: Format into clean parameter sets ──────────────────────────
    lifestyle_plan = [_format_record(rec) for rec in adjusted]

    # ── Step 5: Get warnings ──────────────────────────────────────────────
    warnings = _WARNINGS.get(kl_grade, [])

    # ── Step 6: Get exercise videos ───────────────────────────────────────
    exercise_videos = get_exercise_videos(kl_grade, db)
    exercise_video_urls = [v["s3_url"] for v in exercise_videos]

    # ── Step 7: Build legacy text summary for backward compatibility ──────
    recommendation_text = _build_text_summary(kl_grade, pain_level, mobility_level, lifestyle_plan, warnings)

    return {
        "lifestyle_plan": lifestyle_plan,
        "warnings": warnings,
        "exercise_videos": exercise_videos,
        "recommendation": recommendation_text,
        "exercise_video_urls": exercise_video_urls,
    }


def _build_text_summary(
    kl_grade: int,
    pain_level: Optional[int],
    mobility_level: Optional[str],
    plan: List[Dict],
    warnings: List[Dict],
) -> str:
    """
    Build a human-readable text summary from the parametric output.
    This is for backward compatibility with the existing Report model
    and for display in contexts where structured rendering isn't available.
    """
    header = f"Personalised Plan for KL Grade {kl_grade}"
    if pain_level is not None:
        header += f" | Pain: {pain_level}/10"
    if mobility_level:
        header += f" | Mobility: {mobility_level}"
    header += "\n" + "=" * len(header) + "\n\n"

    sections = {}
    for item in plan:
        cat = item["category"].replace("_", " ").title()
        if cat not in sections:
            sections[cat] = []
        line = f"• {item['action']}"
        if item.get("frequency"):
            line += f" [{item['frequency']}"
            if item.get("duration_min"):
                line += f", {item['duration_min']} min"
            if item.get("intensity"):
                line += f", {item['intensity']} intensity"
            line += "]"
        line += f"  (Evidence: {item['evidence_level']} — {item['source']})"
        sections[cat].append(line)

    body = ""
    for cat, items in sections.items():
        body += f"📋 {cat}\n"
        body += "\n".join(items) + "\n\n"

    warning_text = ""
    if warnings:
        warning_text = "⚠️ Warnings\n"
        for w in warnings:
            icon = "🔴" if w["level"] == "warning" else "🟡" if w["level"] == "caution" else "ℹ️"
            warning_text += f"{icon} {w['message']}\n"
        warning_text += "\n"

    disclaimer = (
        "─────────────────────────────────────────\n"
        "⚠️ These are general lifestyle suggestions and do not constitute medical advice. "
        "Please consult your healthcare provider before starting any new exercise programme."
    )

    return header + body + warning_text + disclaimer
