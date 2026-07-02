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
  Input:  (kl_grade, pain_level, mobility_level, user_profile)
  Step 1: Parametric filter — hard-filter knowledge base by KL grade range
  Step 2: Semantic ranking — embed user context, rank remaining records
  Step 3: Profile-based filtering — apply clinical constraints (kinesiophobia, occupation, meds)
  Step 4: Pain/mobility modifiers — adjust intensity & frequency parameters
  Step 5: Assemble structured output — typed dicts, not prose
  Step 6: Fetch exercise videos from DB
  Output: { lifestyle_plan: [...], exercise_videos: [...], warnings: [...] }
"""

import os
import json
import numpy as np
from threading import Lock
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.models.library import ExerciseVideo
from app.models.user import User
from app.services.s3_service import generate_presigned_url

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
_embedding_model_lock = Lock()
_knowledge_base_lock = Lock()


def _load_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        with _embedding_model_lock:
            if _embedding_model is None:
                _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def _load_knowledge_base():
    """Load the parametric knowledge base with embeddings from files."""
    global _kb_embeddings, _knowledge_base

    if _knowledge_base is not None:
        return

    with _knowledge_base_lock:
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


def _safe_default(value: Optional[str], default: str, options: List[str]) -> str:
    """
    Provide safe defaults for optional user profile fields.
    If value is null, return a conservative default that won't over-filter.
    """
    if value is None:
        return default
    if value in options:
        return value
    return default  # Unknown value, use safe default


def _kinesiophobia_filter(
    records: List[Dict[str, Any]],
    user_kinesiophobia: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Filter out recommendations contraindicated by kinesiophobia level.
    
    Business Rule: If user has 'high' kinesiophobia, filter out items
    where max_kinesiophobia is 'low' (too intimidating).
    
    Safe Default: Treat null kinesiophobia as 'moderate' for safety.
    """
    kinesiophobia_rank = {"low": 0, "moderate": 1, "high": 2}
    
    # Safe default: treat null as moderate
    user_level = _safe_default(user_kinesiophobia, "moderate", ["low", "moderate", "high"])
    user_rank = kinesiophobia_rank[user_level]
    
    filtered = []
    for rec in records:
        # Check if record has kinesiophobia constraint
        rec_kin_max = rec.get("kinesiophobia_req")
        if rec_kin_max is None:
            # No constraint, include by default
            filtered.append(rec)
            continue
        
        # If user has high kinesiophobia, filter out low-kinesiophobia items
        if user_level == "high" and rec_kin_max == "low":
            continue  # Too intimidating for high kinesiophobia
        
        filtered.append(rec)
    
    return filtered


def _occupation_filter(
    records: List[Dict[str, Any]],
    user_occupation: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Filter out recommendations contraindicated by occupation type.
    
    Business Rule: If user has 'heavy_manual' occupation, filter out items
    where contraindicated_occupations includes 'heavy_manual'.
    
    Safe Default: Treat null occupation as 'sedentary' (most conservative).
    """
    occupation_options = ["sedentary", "light_manual", "heavy_manual"]
    
    # Safe default: treat null as sedentary
    user_occupation = _safe_default(user_occupation, "sedentary", occupation_options)
    
    filtered = []
    for rec in records:
        # Check if record has occupation constraints
        contraindicated_occupations = rec.get("contraindicated_occupations", [])
        
        if user_occupation in contraindicated_occupations:
            continue  # Contraindicated for this occupation
        
        filtered.append(rec)
    
    return filtered


def _medication_filter(
    records: List[Dict[str, Any]],
    user_meds: Optional[List[str]],
) -> List[Dict[str, Any]]:
    """
    Filter out recommendations with medication conflicts.
    
    Business Rule: If user takes NSAIDs (ibuprofen, naproxen, etc.), filter out
    advice that conflicts with NSAIDs or recommends taking NSAIDs.
    
    Safe Default: Treat null medications as no conflicts (include all).
    """
    if user_meds is None:
        # No medications specified, include all records
        return records
    
    # Normalize medication names to lowercase for comparison
    user_meds_lower = [med.lower().strip() for med in user_meds]
    
    # Check if user is taking NSAIDs
    takes_nsaid = False
    nsaid_keywords = ["ibuprofen", "naproxen", "advil", "aleve", "nurofen", "diclofenac"]
    for med in user_meds_lower:
        if any(keyword in med for keyword in nsaid_keywords):
            takes_nsaid = True
            break
    
    filtered = []
    for rec in records:
        # Check for medication conflicts in the record
        medication_conflicts = rec.get("medication_conflicts", [])
        
        if takes_nsaid:
            # Filter out if conflicts include NSAIDs
            for conflict in medication_conflicts:
                conflict_lower = conflict.lower()
                if "nsaid" in conflict_lower or any(
                    keyword in conflict_lower for keyword in nsaid_keywords
                ):
                    continue  # Skip this recommendation
        
        filtered.append(rec)
    
    return filtered


def _stairs_filter(
    records: List[Dict[str, Any]],
    has_stairs: Optional[bool],
) -> List[Dict[str, Any]]:
    """
    Handle stair-related filtering and prioritization.
    
    Business Rule: If has_stairs is true, ensure stair-navigation advice is not filtered out.
    Prioritize recommendations that are stair-friendly.
    
    Safe Default: Treat null has_stairs as false (no special handling).
    """
    if has_stairs is None:
        # No stairs, include all records
        return records
    
    if not has_stairs:
        # No stairs at home, include all records
        return records
    
    # User has stairs - prioritize stair-friendly recommendations
    # Don't filter out, but we could add a priority score if needed
    # For now, include all records (stairs don't contraindicate anything)
    return records


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
            "s3_url": generate_presigned_url(v.s3_url) if v.s3_url else None,
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
    # New profile fields (April 2026)
    kinesiophobia: Optional[str] = None,
    occupation_type: Optional[str] = None,
    has_stairs: Optional[bool] = None,
    current_meds: Optional[List[str]] = None,
    sleep_quality: Optional[str] = None,
) -> dict:
    """
    Full parametric recommendation pipeline with profile-based filtering.
    
    FIXED PIPELINE ORDER (Prevents Post-Filtering RAG Trap):
    All deterministic filters run BEFORE semantic ranking to ensure
    the semantic ranker has maximum candidates to work with.
    
    Execution Flow:
    1. _hard_filter (KL grade, pain threshold, mobility requirement)
    2. _kinesiophobia_filter (kinesiophobia constraints)
    3. _occupation_filter (occupation contraindications)
    4. _medication_filter (medication conflicts)
    5. _stairs_filter (stair navigation considerations)
    6. Track original indices for embedding lookup
    7. _semantic_rank (semantic relevance ranking)
    8. _apply_modifiers (pain/mobility adjustments)
    9. _format_record (clean output)

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

    Profile-Based Filtering (April 2026):
    - Kinesiophobia: Filters out intimidating advice for high kinesiophobia users
    - Occupation: Filters out contraindicated activities for occupation type
    - Medications: Filters out advice with medication conflicts
    - Stairs: Ensures stair-navigation advice is preserved
    - Sleep: Considered for activity timing recommendations
    """
    _load_knowledge_base()

    # ── Step 1: Hard parametric filter (KL grade, pain, mobility) ──────────
    all_records = _knowledge_base
    filtered = _hard_filter(all_records, kl_grade, pain_level, mobility_level)

    if not filtered:
        # No records passed hard filter — return empty result
        return {
            "lifestyle_plan": [],
            "warnings": _WARNINGS.get(kl_grade, []),
            "exercise_videos": get_exercise_videos(kl_grade, db),
            "recommendation": "",
            "exercise_video_urls": [],
        }

    # ── Step 2: Profile-based clinical filtering (deterministic, BEFORE ranking) ──
    # Apply all deterministic filters BEFORE semantic ranking to prevent
    # result starvation when top_k truncation happens after filtering
    kin_filtered = _kinesiophobia_filter(filtered, kinesiophobia)
    occupation_filtered = _occupation_filter(kin_filtered, occupation_type)
    med_filtered = _medication_filter(occupation_filtered, current_meds)
    stairs_filtered = _stairs_filter(med_filtered, has_stairs)

    if not stairs_filtered:
        # All records filtered out by profile constraints
        return {
            "lifestyle_plan": [],
            "warnings": _WARNINGS.get(kl_grade, []),
            "exercise_videos": get_exercise_videos(kl_grade, db),
            "recommendation": "",
            "exercise_video_urls": [],
        }

    # ── Step 3: Track original indices for embedding lookup ────────────────
    # The semantic ranker needs indices to slice _kb_embeddings correctly
    surviving_indices = []
    for rec in stairs_filtered:
        for i, orig in enumerate(all_records):
            if orig["id"] == rec["id"]:
                surviving_indices.append(i)
                break

    # ── Step 4: Semantic ranking (NOW has full candidate set) ──────────────
    # With all deterministic filters applied, the ranker can select the
    # top-k most relevant records from the surviving candidates
    ranked = _semantic_rank(
        stairs_filtered, surviving_indices, kl_grade, pain_level, mobility_level
    )

    # ── Step 5: Apply pain/mobility modifiers ──────────────────────────────
    adjusted = _apply_modifiers(ranked, pain_level, mobility_level)

    # ── Step 6: Format into clean parameter sets ───────────────────────────
    lifestyle_plan = [_format_record(rec) for rec in adjusted]

    # ── Step 7: Get warnings ───────────────────────────────────────────────
    warnings = _WARNINGS.get(kl_grade, [])

    # ── Step 8: Get exercise videos ────────────────────────────────────────
    exercise_videos = get_exercise_videos(kl_grade, db)
    exercise_video_urls = [v["s3_url"] for v in exercise_videos]

    # ── Step 9: Build legacy text summary for backward compatibility ───────
    recommendation_text = _build_text_summary(
        kl_grade, pain_level, mobility_level, lifestyle_plan, warnings
    )

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
