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
    """Load or build the parametric knowledge base with embeddings."""
    global _kb_embeddings, _knowledge_base

    if _knowledge_base is not None:
        return

    if os.path.exists(EMBEDDINGS_FILE) and os.path.exists(KNOWLEDGE_FILE):
        _kb_embeddings = np.load(EMBEDDINGS_FILE)
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            _knowledge_base = json.load(f)
    else:
        _knowledge_base = _build_parametric_knowledge_base()
        model = _load_embedding_model()
        # Embed the semantic_key of each record for retrieval
        texts = [rec["semantic_key"] for rec in _knowledge_base]
        _kb_embeddings = model.encode(texts, show_progress_bar=False)
        # Persist
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
        np.save(EMBEDDINGS_FILE, _kb_embeddings)
        with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
            json.dump(_knowledge_base, f, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
#  PARAMETRIC KNOWLEDGE BASE
#  Every record is a typed parameter set — NOT free text.
#  Fields:
#    id              — unique identifier
#    semantic_key    — natural-language description used ONLY for embedding/retrieval
#    category        — "exercise" | "nutrition" | "pain_management" | "lifestyle" | "flexibility"
#    action          — the specific recommendation (imperative, short)
#    frequency       — how often (e.g. "daily", "3x/week")
#    duration_min    — session duration in minutes
#    intensity       — "low" | "moderate" | "high"
#    kl_grade_min/max— which KL grades this applies to
#    pain_threshold  — max pain level (0-10) this is safe for; null = any
#    mobility_req    — minimum mobility needed: "limited" | "moderate" | "good" | null
#    contraindications — list of conditions where this should NOT be recommended
#    evidence_level  — "strong" | "moderate" | "emerging"
#    source          — citation / guideline reference
# ══════════════════════════════════════════════════════════════════════════════

def _build_parametric_knowledge_base() -> List[Dict[str, Any]]:
    return [
        # ── EXERCISE ──────────────────────────────────────────────────────
        {
            "id": "EX-001",
            "semantic_key": "low-impact aerobic exercise walking cycling swimming early knee osteoarthritis",
            "category": "exercise",
            "action": "Perform low-impact aerobic exercise: walking, cycling, or swimming",
            "frequency": "5x/week",
            "duration_min": 30,
            "intensity": "moderate",
            "kl_grade_min": 0,
            "kl_grade_max": 2,
            "pain_threshold": 6,
            "mobility_req": "moderate",
            "contraindications": ["acute_flare", "post_surgery"],
            "evidence_level": "strong",
            "source": "OARSI 2019 Guidelines",
        },
        {
            "id": "EX-002",
            "semantic_key": "quadriceps hamstring strengthening exercises moderate knee osteoarthritis",
            "category": "exercise",
            "action": "Strengthen quadriceps and hamstrings with isometric exercises and leg presses",
            "frequency": "3x/week",
            "duration_min": 20,
            "intensity": "moderate",
            "kl_grade_min": 1,
            "kl_grade_max": 3,
            "pain_threshold": 7,
            "mobility_req": "moderate",
            "contraindications": ["acute_flare", "joint_instability"],
            "evidence_level": "strong",
            "source": "ACR/AF 2020 Guidelines",
        },
        {
            "id": "EX-003",
            "semantic_key": "aqua therapy water-based exercise severe knee osteoarthritis buoyancy",
            "category": "exercise",
            "action": "Perform water-based exercises (aqua therapy) to reduce joint loading by up to 90%",
            "frequency": "3x/week",
            "duration_min": 30,
            "intensity": "low",
            "kl_grade_min": 2,
            "kl_grade_max": 4,
            "pain_threshold": 9,
            "mobility_req": "limited",
            "contraindications": ["open_wounds", "skin_infection"],
            "evidence_level": "strong",
            "source": "Cochrane Review 2016",
        },
        {
            "id": "EX-004",
            "semantic_key": "gentle range of motion exercises severe osteoarthritis limited mobility",
            "category": "exercise",
            "action": "Perform gentle seated range-of-motion exercises (ankle pumps, knee extensions)",
            "frequency": "daily",
            "duration_min": 10,
            "intensity": "low",
            "kl_grade_min": 3,
            "kl_grade_max": 4,
            "pain_threshold": 10,
            "mobility_req": "limited",
            "contraindications": [],
            "evidence_level": "moderate",
            "source": "NICE NG226 2022",
        },
        # ── FLEXIBILITY ───────────────────────────────────────────────────
        {
            "id": "FL-001",
            "semantic_key": "stretching hamstrings calves hip flexors flexibility knee osteoarthritis",
            "category": "flexibility",
            "action": "Stretch hamstrings, calves, and hip flexors (hold each stretch 30 seconds)",
            "frequency": "daily",
            "duration_min": 15,
            "intensity": "low",
            "kl_grade_min": 0,
            "kl_grade_max": 4,
            "pain_threshold": 8,
            "mobility_req": "limited",
            "contraindications": ["acute_flare"],
            "evidence_level": "moderate",
            "source": "ACSM Exercise Guidelines 2021",
        },
        {
            "id": "FL-002",
            "semantic_key": "yoga tai chi balance flexibility knee osteoarthritis pain reduction",
            "category": "flexibility",
            "action": "Practice yoga or tai chi for balance and pain reduction",
            "frequency": "2x/week",
            "duration_min": 30,
            "intensity": "low",
            "kl_grade_min": 0,
            "kl_grade_max": 3,
            "pain_threshold": 6,
            "mobility_req": "moderate",
            "contraindications": ["severe_instability"],
            "evidence_level": "moderate",
            "source": "Arthritis Foundation 2020",
        },
        # ── NUTRITION ─────────────────────────────────────────────────────
        {
            "id": "NU-001",
            "semantic_key": "weight management diet anti-inflammatory foods knee osteoarthritis",
            "category": "nutrition",
            "action": "Follow an anti-inflammatory diet rich in fish, nuts, and leafy greens",
            "frequency": "daily",
            "duration_min": None,
            "intensity": None,
            "kl_grade_min": 0,
            "kl_grade_max": 4,
            "pain_threshold": None,
            "mobility_req": None,
            "contraindications": ["fish_allergy", "nut_allergy"],
            "evidence_level": "moderate",
            "source": "Mediterranean Diet & OA Meta-analysis 2018",
        },
        {
            "id": "NU-002",
            "semantic_key": "weight loss body weight reduction knee joint pressure osteoarthritis",
            "category": "nutrition",
            "action": "Aim for gradual weight loss (0.5-1 kg/week) — each 1 kg lost removes ~4 kg of knee pressure",
            "frequency": "ongoing",
            "duration_min": None,
            "intensity": None,
            "kl_grade_min": 0,
            "kl_grade_max": 4,
            "pain_threshold": None,
            "mobility_req": None,
            "contraindications": ["underweight"],
            "evidence_level": "strong",
            "source": "Messier et al. JAMA 2013",
        },
        # ── PAIN MANAGEMENT ───────────────────────────────────────────────
        {
            "id": "PM-001",
            "semantic_key": "heat therapy before exercise warm stiff joints knee osteoarthritis",
            "category": "pain_management",
            "action": "Apply heat therapy for 15-20 minutes before exercise to loosen stiff joints",
            "frequency": "before exercise",
            "duration_min": 20,
            "intensity": None,
            "kl_grade_min": 1,
            "kl_grade_max": 4,
            "pain_threshold": None,
            "mobility_req": None,
            "contraindications": ["acute_inflammation", "open_wounds"],
            "evidence_level": "moderate",
            "source": "NICE NG226 2022",
        },
        {
            "id": "PM-002",
            "semantic_key": "cold therapy ice after exercise reduce swelling knee osteoarthritis",
            "category": "pain_management",
            "action": "Apply cold therapy (ice pack) for 10-15 minutes after exercise to reduce swelling",
            "frequency": "after exercise",
            "duration_min": 15,
            "intensity": None,
            "kl_grade_min": 1,
            "kl_grade_max": 4,
            "pain_threshold": None,
            "mobility_req": None,
            "contraindications": ["raynauds_disease", "cold_sensitivity"],
            "evidence_level": "moderate",
            "source": "NICE NG226 2022",
        },
        {
            "id": "PM-003",
            "semantic_key": "assistive devices walking aids cane knee osteoarthritis severe pain",
            "category": "pain_management",
            "action": "Use assistive devices (cane, knee brace) to reduce joint loading during daily activities",
            "frequency": "as needed",
            "duration_min": None,
            "intensity": None,
            "kl_grade_min": 3,
            "kl_grade_max": 4,
            "pain_threshold": None,
            "mobility_req": "limited",
            "contraindications": [],
            "evidence_level": "strong",
            "source": "OARSI 2019 Guidelines",
        },
        # ── LIFESTYLE ─────────────────────────────────────────────────────
        {
            "id": "LS-001",
            "semantic_key": "proper footwear arch support cushioning knee osteoarthritis",
            "category": "lifestyle",
            "action": "Wear footwear with good arch support and cushioning; consider orthotic insoles",
            "frequency": "daily",
            "duration_min": None,
            "intensity": None,
            "kl_grade_min": 0,
            "kl_grade_max": 4,
            "pain_threshold": None,
            "mobility_req": None,
            "contraindications": [],
            "evidence_level": "moderate",
            "source": "Cochrane Review 2015",
        },
        {
            "id": "LS-002",
            "semantic_key": "sleep quality pain management pillow knee alignment osteoarthritis",
            "category": "lifestyle",
            "action": "Ensure 7-9 hours of sleep; use a pillow between knees when sleeping on your side",
            "frequency": "nightly",
            "duration_min": None,
            "intensity": None,
            "kl_grade_min": 0,
            "kl_grade_max": 4,
            "pain_threshold": None,
            "mobility_req": None,
            "contraindications": [],
            "evidence_level": "moderate",
            "source": "Sleep Foundation & OA Guidelines 2021",
        },
        {
            "id": "LS-003",
            "semantic_key": "avoid high impact activities running jumping knee osteoarthritis moderate severe",
            "category": "lifestyle",
            "action": "Avoid high-impact activities (running, jumping, heavy squats)",
            "frequency": "always",
            "duration_min": None,
            "intensity": None,
            "kl_grade_min": 2,
            "kl_grade_max": 4,
            "pain_threshold": None,
            "mobility_req": None,
            "contraindications": [],
            "evidence_level": "strong",
            "source": "OARSI 2019 Guidelines",
        },
    ]


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
    model = _load_embedding_model()

    # Build context query
    parts = [f"knee osteoarthritis KL grade {kl_grade}"]
    if pain_level is not None:
        severity = "mild" if pain_level <= 3 else "moderate" if pain_level <= 6 else "severe"
        parts.append(f"{severity} pain")
    if mobility_level:
        parts.append(f"{mobility_level} mobility")

    query_embedding = model.encode(". ".join(parts), show_progress_bar=False)

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
