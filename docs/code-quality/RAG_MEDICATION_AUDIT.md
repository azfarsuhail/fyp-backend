# RAG Medication Data Extraction Pipeline Audit

**Date:** 2026-07-03  
**Files Audited:**
- `app/ml_assets/vector_store/parametric_knowledge.json`
- `app/agents/recommendation_agent.py`
- `app/api/v1/diagnostic.py`
- `app/schemas/recommendation_schema.py`
- `app/models/medication.py`
- `app/services/medication_service.py`

---

## Executive Summary

### 🔴 CRITICAL ISSUE FOUND

The **medications field is NOT being populated** in diagnostic reports. The `RecommendationResult` schema includes a `medications` field, but the recommendation agent and diagnostic endpoint **never fetch or include medication data** from the database.

---

## 1. Knowledge Base Audit (`parametric_knowledge.json`)

### Current Structure

The JSON file contains **exercise and lifestyle recommendations**, NOT medication data. Each record has:

```json
{
  "id": "rec_001",
  "category": "strengthening",  // or "flexibility", "low-impact", "medication_guidance", "supplement"
  "action": "Quadriceps sets...",
  "frequency": "Daily",
  "duration_min": 10,
  "intensity": "low",
  "kl_grade_min": 0,
  "kl_grade_max": 3,
  "pain_threshold": 7,
  "mobility_req": "limited",
  "contraindications": ["acute joint inflammation"],
  "evidence_level": "High",
  "source": "OARSI Guidelines...",
  "kinesiophobia_req": "high",
  "contraindicated_occupations": [],
  "medication_conflicts": []  // ← This field EXISTS but is EMPTY
}
```

### Key Findings

| Field | Status | Purpose |
|-------|--------|---------|
| `category` | ✅ Present | Classifies recommendations (exercise, flexibility, medication_guidance, supplement) |
| `medication_conflicts` | ✅ Present | Lists medications that conflict with this recommendation (e.g., ["oral NSAIDs"]) |
| **Medication Data** | ❌ **MISSING** | No actual medication records (name, dosage, frequency, etc.) |

### Structural Issue

The knowledge base is designed for **filtering recommendations based on medication conflicts**, NOT for **retrieving medication recommendations**. 

**Example from rec_007 (medication_guidance category):**
```json
{
  "category": "medication_guidance",
  "action": "Topical NSAIDs. Discuss with your GP...",
  "medication_conflicts": ["oral NSAIDs"]  // ← Filters OUT this rec if user takes oral NSAIDs
}
```

This is **advice about medications**, not **structured medication catalog data**.

---

## 2. Recommendation Agent Analysis (`recommendation_agent.py`)

### Current Implementation

The `generate_recommendation()` function returns:

```python
return {
    "lifestyle_plan": lifestyle_plan,      # ✅ Populated from knowledge base
    "warnings": warnings,                  # ✅ Populated from _WARNINGS table
    "exercise_videos": exercise_videos,    # ✅ Populated from ExerciseVideo DB
    "recommendation": recommendation_text, # ✅ Built from lifestyle_plan
    "exercise_video_urls": exercise_video_urls, # ✅ Extracted from exercise_videos
    # ❌ NO "medications" field!
}
```

### Missing Medication Logic

**The agent does NOT:**
1. Query the `MEDICATION` database table
2. Filter medications by KL grade
3. Filter medications by user's current medications (contraindications)
4. Include medications in the return dictionary

### Code Evidence

**Line 400-430** (`generate_recommendation` return statement):
```python
return {
    "lifestyle_plan": lifestyle_plan,
    "warnings": warnings,
    "exercise_videos": exercise_videos,
    "recommendation": recommendation_text,
    "exercise_video_urls": exercise_video_urls,
}
# ❌ No "medications" key!
```

**Line 420-430** (`get_exercise_videos` function exists, but no `get_medications`):
```python
def get_exercise_videos(kl_grade: int, db: Session) -> List[Dict[str, Any]]:
    """Fetch exercise videos from the DB as structured objects."""
    videos = db.query(ExerciseVideo).filter(...).all()
    return [...]  # ✅ Returns structured video data
```

**No equivalent function for medications exists!**

---

## 3. Diagnostic Endpoint Analysis (`diagnostic.py`)

### Current Implementation

**Line 155-165** (Report creation):
```python
new_report = Report(
    image_id=image.image_id,
    user_id=user.user_id,
    kl_grade=kl_grade,
    confidence=confidence,
    diagnosis_summary=diagnosis_summary,
    recommendation=rec_result["recommendation"],
    lifestyle_plan=json.dumps(rec_result.get("lifestyle_plan", [])),
    warnings=json.dumps(rec_result.get("warnings", [])),
    exercise_video_urls=json.dumps(rec_result["exercise_video_urls"]),
    # ❌ NO medications field!
)
```

**Line 170-185** (ReportOut response):
```python
return ReportOut(
    report_id=new_report.report_id,
    # ... other fields ...
    lifestyle_plan=json.loads(new_report.lifestyle_plan) if new_report.lifestyle_plan else [],
    warnings=json.loads(new_report.warnings) if new_report.warnings else [],
    exercise_video_urls=json.loads(new_report.exercise_video_urls) if new_report.exercise_video_urls else [],
    created_at=new_report.created_at,
    # ❌ NO medications field in response!
)
```

### Schema Mismatch

**`ReportOut` schema** (`app/schemas/report_schema.py` line 64):
```python
class ReportOut(BaseModel):
    lifestyle_plan: Optional[List[LifestyleItem]] = None
    warnings: Optional[List[Warning]] = None
    exercise_video_urls: Optional[List[str]] = []
    # ❌ NO medications field defined!
```

**`RecommendationResult` schema** (`app/schemas/recommendation_schema.py` line 28):
```python
class RecommendationResult(BaseModel):
    lifestyle_plan: List[LifestyleItem] = Field(default_factory=list)
    warnings: List[Warning] = Field(default_factory=list)
    exercise_videos: List[ExerciseVideoOut] = Field(default_factory=list)
    medications: List[Medication] = Field(default_factory=list)  # ✅ Defined here!
    recommendation: str
    exercise_video_urls: List[str] = Field(default_factory=list)
```

**Problem:** `RecommendationResult` has a `medications` field, but `ReportOut` does NOT. The diagnostic endpoint uses `ReportOut`, so medications can never be returned.

---

## 4. Profile Database Integration

### Current Implementation

**Line 125-130** (`diagnostic.py`):
```python
rec_result = await run_in_threadpool(
    generate_recommendation,
    kl_grade=kl_grade,
    db=db,
    pain_level=request.pain_level,
    mobility_level=request.mobility_level,
    # New profile fields (April 2026)
    kinesiophobia=user.kinesiophobia,
    occupation_type=user.occupation_type,
    has_stairs=user.has_stairs,
    current_meds=json.loads(user.current_meds) if user.current_meds else None,
    sleep_quality=user.sleep_quality,
)
```

### ✅ Profile Context IS Being Passed

The user's profile data (including `current_meds`) **IS** being passed to the recommendation agent. However:

1. The recommendation agent **receives** it but **doesn't use it** for medication filtering
2. The recommendation agent **doesn't return** any medication data
3. The diagnostic endpoint **doesn't add** medication data to the report

### Medication Filtering Logic Exists (But Unused)

**`_medication_filter()` function** (`recommendation_agent.py` line 245-285):
```python
def _medication_filter(
    records: List[Dict[str, Any]],
    user_meds: Optional[List[str]],
) -> List[Dict[str, Any]]:
    """
    Filter out recommendations with medication conflicts.
    
    Business Rule: If user takes NSAIDs (ibuprofen, naproxen, etc.), filter out
    advice that conflicts with NSAIDs or recommends taking NSAIDs.
    """
    if user_meds is None:
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
        medication_conflicts = rec.get("medication_conflicts", [])
        
        if takes_nsaid:
            for conflict in medication_conflicts:
                conflict_lower = conflict.lower()
                if "nsaid" in conflict_lower or any(
                    keyword in conflict_lower for keyword in nsaid_keywords
                ):
                    continue  # Skip this recommendation
        
        filtered.append(rec)
    
    return filtered
```

**This function EXISTS and IS CALLED** (line 525), but it only **filters exercise recommendations**, it doesn't **retrieve medication catalog data**.

---

## 5. Medication Service & Database

### ✅ Medication Infrastructure Exists

**`MedicationModel`** (`app/models/medication.py`):
```python
class MedicationModel(Base):
    __tablename__ = "MEDICATION"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    instructions = Column(Text, nullable=True)
    contraindications = Column(Text, nullable=True)
    kl_grade_min = Column(Integer, nullable=False)
    kl_grade_max = Column(Integer, nullable=False)
```

**`medication_service.py`** provides:
- `list_medications(db)` - Returns all medications
- `create_medication(db, payload)` - Creates new medication

**`medications.py`** API endpoints:
- `GET /api/v1/medications/` - Public medication catalog
- `POST /api/v1/admin/medications/` - Admin-only medication creation

### ✅ `Medication` Schema Exists

**`app/schemas/recommendation_schema.py`**:
```python
class Medication(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    dosage: str
    frequency: str
    instructions: Optional[str] = None
    contraindications: Optional[List[str]] = None
    kl_grade_min: int
    kl_grade_max: int
```

---

## 6. Root Cause Analysis

### Why Medications Are Missing

| Layer | Issue |
|-------|-------|
| **Knowledge Base** | Contains medication GUIDANCE (advice), not medication CATALOG (structured data) |
| **Recommendation Agent** | Never queries `MEDICATION` table, never returns medications in result |
| **Diagnostic Endpoint** | Uses `ReportOut` schema which lacks `medications` field |
| **Database Schema** | `Report` table has no `medications` column |

### Data Flow Breakdown

```
User Profile (current_meds) 
    ↓
Recommendation Agent (receives current_meds)
    ↓
❌ Agent filters exercise recs by medication conflicts
❌ Agent NEVER queries MEDICATION table
❌ Agent NEVER includes medications in return dict
    ↓
Diagnostic Endpoint (receives rec_result)
    ↓
❌ Endpoint doesn't add medications to Report
❌ ReportOut schema has no medications field
    ↓
Frontend (receives ReportOut)
    ↓
❌ NO medications data to display!
```

---

## 7. Required Fixes

### Fix 1: Add Medications Field to Report Schema

**File:** `app/schemas/report_schema.py`

```python
class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    report_id: int
    image_id: int
    user_id: int
    kl_grade: int
    confidence: float
    diagnosis_summary: Optional[str] = None
    recommendation: Optional[str] = None
    lifestyle_plan: Optional[List[LifestyleItem]] = None
    warnings: Optional[List[Warning]] = None
    medications: Optional[List[Medication]] = None  # ← ADD THIS
    exercise_video_urls: Optional[List[str]] = []
    created_at: datetime
```

### Fix 2: Add Medications Field to Report Model

**File:** `app/models/report.py`

```python
class Report(Base):
    __tablename__ = "REPORT"
    
    # ... existing fields ...
    medications = Column(Text, nullable=True)  # ← ADD THIS (JSON string)
```

### Fix 3: Add Medication Retrieval to Recommendation Agent

**File:** `app/agents/recommendation_agent.py`

Add new function after `get_exercise_videos()`:

```python
def get_medications(kl_grade: int, db: Session) -> List[Dict[str, Any]]:
    """
    Fetch medications from the DB that match the patient's KL grade.
    Filters by kl_grade_min <= kl_grade <= kl_grade_max.
    """
    from app.models.medication import MedicationModel
    
    medications = (
        db.query(MedicationModel)
        .filter(
            MedicationModel.kl_grade_min <= kl_grade,
            MedicationModel.kl_grade_max >= kl_grade,
        )
        .all()
    )
    
    return [
        {
            "id": m.id,
            "name": m.name,
            "dosage": m.dosage,
            "frequency": m.frequency,
            "instructions": m.instructions,
            "contraindications": m.contraindications,
            "kl_grade_min": m.kl_grade_min,
            "kl_grade_max": m.kl_grade_max,
        }
        for m in medications
    ]
```

### Fix 4: Include Medications in Recommendation Result

**File:** `app/agents/recommendation_agent.py`

Update `generate_recommendation()` return statement (around line 420):

```python
# ── Step 8: Get exercise videos ────────────────────────────────────────
exercise_videos = get_exercise_videos(kl_grade, db)
exercise_video_urls = [v["s3_url"] for v in exercise_videos]

# ── Step 9: Get medications ───────────────────────────────────────────
medications = get_medications(kl_grade, db)

# ── Step 10: Build legacy text summary for backward compatibility ─────
recommendation_text = _build_text_summary(
    kl_grade, pain_level, mobility_level, lifestyle_plan, warnings
)

return {
    "lifestyle_plan": lifestyle_plan,
    "warnings": warnings,
    "exercise_videos": exercise_videos,
    "medications": medications,  # ← ADD THIS
    "recommendation": recommendation_text,
    "exercise_video_urls": exercise_video_urls,
}
```

### Fix 5: Include Medications in Diagnostic Endpoint

**File:** `app/api/v1/diagnostic.py`

Update Report creation (around line 155):

```python
new_report = Report(
    image_id=image.image_id,
    user_id=user.user_id,
    kl_grade=kl_grade,
    confidence=confidence,
    diagnosis_summary=diagnosis_summary,
    recommendation=rec_result["recommendation"],
    lifestyle_plan=json.dumps(rec_result.get("lifestyle_plan", [])),
    warnings=json.dumps(rec_result.get("warnings", [])),
    medications=json.dumps(rec_result.get("medications", [])),  # ← ADD THIS
    exercise_video_urls=json.dumps(rec_result["exercise_video_urls"]),
)
```

Update ReportOut response (around line 170):

```python
return ReportOut(
    report_id=new_report.report_id,
    image_id=new_report.image_id,
    user_id=new_report.user_id,
    kl_grade=new_report.kl_grade,
    confidence=new_report.confidence,
    diagnosis_summary=new_report.diagnosis_summary,
    recommendation=new_report.recommendation,
    lifestyle_plan=json.loads(new_report.lifestyle_plan) if new_report.lifestyle_plan else [],
    warnings=json.loads(new_report.warnings) if new_report.warnings else [],
    medications=json.loads(new_report.medications) if new_report.medications else [],  # ← ADD THIS
    exercise_video_urls=json.loads(new_report.exercise_video_urls)
    if new_report.exercise_video_urls
    else [],
    created_at=new_report.created_at,
)
```

---

## 8. Testing Checklist

After implementing fixes:

- [ ] `GET /api/v1/diagnostic/reports` returns `medications` array
- [ ] `medications` array contains objects with: `id`, `name`, `dosage`, `frequency`, `kl_grade_min`, `kl_grade_max`
- [ ] Medications are filtered by KL grade (only meds where `kl_grade_min <= user_kl_grade <= kl_grade_max`)
- [ ] Frontend displays medications in diagnostic reports
- [ ] Admin can add medications via `POST /api/v1/admin/medications/`
- [ ] Medications persist in database across restarts

---

## 9. Summary

### What's Working ✅

- Medication database model exists
- Medication service functions exist
- Medication API endpoints exist
- User profile `current_meds` field exists and is passed to recommendation agent
- Medication conflict filtering logic exists (for exercise recommendations)

### What's Broken ❌

- Recommendation agent never queries `MEDICATION` table
- Recommendation agent never returns `medications` in result
- `ReportOut` schema lacks `medications` field
- `Report` model lacks `medications` column
- Diagnostic endpoint never includes medications in response

### Priority: 🔴 HIGH

This is a **critical data pipeline break**. The backend has all the infrastructure, but the recommendation agent and diagnostic endpoint are not wired together to return medication data.

---

## 10. Next Steps

1. **Implement Fixes 1-5** (see section 7)
2. **Run database migration** to add `medications` column to `REPORT` table
3. **Test end-to-end** with a diagnostic request
4. **Verify frontend** displays medications correctly
5. **Update documentation** to reflect medication data flow
