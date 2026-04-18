# RAG Agent Update - Profile-Based Clinical Filtering

**Date:** April 18, 2026  
**Status:** ✅ Complete  
**Scope:** Parametric RAG Recommendation Agent with new patient profile constraints

---

## 📋 Summary

Updated the Parametric RAG Recommendation Agent to utilize the new patient profile fields (`kinesiophobia`, `occupation_type`, `has_stairs`, `current_meds`, `sleep_quality`) for **strict clinical filtering** before returning recommendations.

---

## 🔧 Changes Made

### 1. Knowledge Base Schema (`parametric_knowledge.json`)

Added new constraint fields to each recommendation object:

```json
{
  "id": "rec_007",
  "category": "ergonomic_advice",
  "action": "Use a knee support brace during work activities...",
  "frequency": "Daily during work hours",
  "duration_min": 480,
  "intensity": "low",
  "kl_grade_min": 2,
  "kl_grade_max": 4,
  "pain_threshold": 6,
  "mobility_req": "limited",
  
  // ── NEW CONSTRAINT FIELDS (April 2026) ─────────────────
  "kinesiophobia_req": "low",                    // min level required
  "contraindicated_occupations": ["heavy_manual"], // occupations to exclude
  "stairs_impact": "moderate",                    // impact level
  "medication_conflicts": ["NSAIDs", "blood thinners"],
  "sleep_consideration": "fair",                  // sleep quality needed
  
  "contraindications": [...],
  "evidence_level": "Moderate",
  "source": "ACR Guidelines for Occupational Management of Knee OA"
}
```

**New Fields Explained:**

| Field | Type | Values | Purpose |
|-------|------|--------|---------|
| `kinesiophobia_req` | String | `'low'`, `'moderate'`, `'high'` | Minimum kinesiophobia level required |
| `contraindicated_occupations` | Array | `['sedentary' \| 'light_manual' \| 'heavy_manual']` | Occupations that should avoid this advice |
| `stairs_impact` | String | `'none'`, `'low'`, `'moderate'`, `'high'` | Impact of stairs on this activity |
| `medication_conflicts` | Array | List of conflicting medications | Medications that conflict with this advice |
| `sleep_consideration` | String | `'poor'`, `'fair'`, `'good'` | Sleep quality consideration |

---

### 2. Recommendation Agent (`app/agents/recommendation_agent.py`)

#### New Helper Functions

**`_safe_default(value, default, options)`**
- Provides safe defaults for optional user profile fields
- Prevents over-filtering when values are `null`

**`_kinesiophobia_filter(records, user_kinesiophobia)`**
- **Business Rule:** If user has `'high'` kinesiophobia, filter out items where `max_kinesiophobia` is `'low'`
- **Safe Default:** Treats `null` kinesiophobia as `'moderate'` for safety

**`_occupation_filter(records, user_occupation)`**
- **Business Rule:** If user has `'heavy_manual'` occupation, filter out items where `contraindicated_occupations` includes `'heavy_manual'`
- **Safe Default:** Treats `null` occupation as `'sedentary'` (most conservative)

**`_medication_filter(records, user_meds)`**
- **Business Rule:** If user takes NSAIDs (ibuprofen, naproxen, etc.), filter out advice that conflicts with NSAIDs
- **Safe Default:** Treats `null` medications as no conflicts (include all)

**`_stairs_filter(records, has_stairs)`**
- **Business Rule:** If `has_stairs` is `true`, ensure stair-navigation advice is not filtered out
- **Safe Default:** Treats `null` as `false` (no special handling)

#### Updated Function Signature

```python
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
```

#### New Filtering Pipeline

```
Step 1: Hard parametric filter (KL grade, pain, mobility)
    ↓
Step 2: Semantic ranking (vector similarity)
    ↓
Step 3: Profile-based clinical filtering (April 2026)
    ├─ _kinesiophobia_filter()
    ├─ _occupation_filter()
    ├─ _medication_filter()
    └─ _stairs_filter()
    ↓
Step 4: Apply pain/mobility modifiers
    ↓
Step 5: Format into clean parameter sets
    ↓
Step 6: Get warnings
    ↓
Step 7: Get exercise videos
    ↓
Step 8: Build legacy text summary
```

---

### 3. API Endpoints Updated

#### Diagnostic Endpoint (`app/api/v1/diagnostic.py`)

```python
rec_result = generate_recommendation(
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

#### Recommendation Endpoint (`app/api/v1/recommendation.py`)

```python
# Fetch full user profile for new constraint fields
user = db.query(User).filter(User.email == current_user["email"]).first()

result = generate_recommendation(
    kl_grade=kl_grade,
    db=db,
    pain_level=pain_level,
    mobility_level=mobility_level,
    # New profile fields (April 2026)
    kinesiophobia=user.kinesiophobia,
    occupation_type=user.occupation_type,
    has_stairs=user.has_stairs,
    current_meds=json.loads(user.current_meds) if user.current_meds else None,
    sleep_quality=user.sleep_quality,
)
```

---

## 🛡️ Safe Defaults & Fallback Logic

| User Field | Null Default | Rationale |
|------------|--------------|-----------|
| `kinesiophobia` | `'moderate'` | Conservative middle ground - won't over-filter |
| `occupation_type` | `'sedentary'` | Most conservative - least physical demand |
| `has_stairs` | `false` | No special handling needed |
| `current_meds` | `[]` (no conflicts) | Include all recommendations |
| `sleep_quality` | Not filtered | No strict filtering applied |

**Key Principle:** When user data is missing, the system defaults to **safe, conservative values** that won't accidentally exclude helpful recommendations.

---

## 🧪 Testing Recommendations

1. **Unit Tests:** Add tests for each new filter function with various input combinations
2. **Integration Tests:** Test full pipeline with users having different profile combinations
3. **Edge Cases:**
   - User with all fields `null` → should get all recommendations (safe defaults)
   - User with `'high'` kinesiophobia → should filter out `'low'` kinesiophobia items
   - User taking NSAIDs → should filter out conflicting advice
   - User with `'heavy_manual'` occupation → should filter out contraindicated items

---

## 📊 Example Filtering Scenarios

### Scenario 1: High Kinesiophobia User
**User Profile:**
- `kinesiophobia`: `'high'`
- `occupation_type`: `'sedentary'`
- `current_meds`: `['ibuprofen']`

**Filtering Applied:**
- ❌ Filter out: Items with `kinesiophobia_req: 'low'` (too intimidating)
- ❌ Filter out: Items with `medication_conflicts: ['NSAIDs']`
- ✅ Include: All `'moderate'` and `'high'` kinesiophobia items

### Scenario 2: Heavy Manual Worker
**User Profile:**
- `kinesiophobia`: `'moderate'`
- `occupation_type`: `'heavy_manual'`
- `has_stairs`: `true`

**Filtering Applied:**
- ❌ Filter out: Items with `contraindicated_occupations: ['heavy_manual']`
- ✅ Include: All `'sedentary'` and `'light_manual'` items
- ✅ Prioritize: Stair-friendly recommendations

### Scenario 3: Legacy User (No New Fields)
**User Profile:**
- All new fields: `null`

**Filtering Applied:**
- ✅ Include: All recommendations (safe defaults applied)
- No over-filtering occurs

---

## 🚀 Next Steps

1. **Update Knowledge Base:** Add new constraint fields to existing `parametric_knowledge.json` entries
2. **Regenerate Embeddings:** Run `python scripts/generate_embeddings.py` after updating JSON
3. **Test Endpoints:** Verify filtering works correctly with various user profiles
4. **Frontend Integration:** Update mobile/web apps to collect new profile fields

---

## 📝 Files Modified

| File | Changes |
|------|---------|
| `app/agents/recommendation_agent.py` | Added 5 new filter functions, updated `generate_recommendation()` signature |
| `app/api/v1/diagnostic.py` | Pass user profile fields to recommendation agent |
| `app/api/v1/recommendation.py` | Fetch user profile and pass fields to recommendation agent |
| `app/ml_assets/vector_store/parametric_knowledge.json` | ⚠️ **Needs manual update** with new constraint fields |

---

## 🔐 Backward Compatibility

✅ **Fully backward compatible:**
- Existing users with `null` values get safe defaults
- No breaking changes to API responses
- Legacy endpoints continue to work
- Database columns are nullable

---

## 📚 References

- [Parametric RAG Architecture](../docs/RECOMMENDATION_AGENT_UPDATE.md)
- [Patient Profile Schema](../app/models/user.py)
- [Profile Logging Audit Trail](../app/api/v1/profile.py)
