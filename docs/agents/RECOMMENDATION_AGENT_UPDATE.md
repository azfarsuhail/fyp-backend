# Recommendation Agent Update

## Changes Made

### 1. **Removed Hardcoded Knowledge Base**
- Removed the `_build_parametric_knowledge_base()` function (14 records)
- The knowledge base is now loaded exclusively from `parametric_knowledge.json`

### 2. **Updated Knowledge Base Loading**
- `_load_knowledge_base()` now loads from external files
- Added validation to ensure embeddings count matches knowledge base count
- Added clear error message if files are missing

### 3. **Updated Embedding Generation**
- Embeddings are now generated from the `action` field (not `semantic_key`)
- This matches the format in `parametric_knowledge.json`

### 4. **Updated Semantic Ranking**
- `_semantic_rank()` now uses the loaded embeddings directly
- No longer calls the embedding model for each query (uses cached embeddings)

---

## File Structure

```
app/ml_assets/vector_store/
├── parametric_knowledge.json  # 22 knowledge records (external file)
└── parametric_embeddings.npy  # 22 embeddings × 384 dimensions
```

---

## Knowledge Base Format

Each record in `parametric_knowledge.json` contains:

```json
{
  "id": "rec_001",
  "category": "strengthening",
  "action": "Quadriceps sets (isometric tightening)...",
  "frequency": "Daily",
  "duration_min": 10,
  "intensity": "low",
  "kl_grade_min": 0,
  "kl_grade_max": 3,
  "pain_threshold": 7,
  "mobility_req": "limited",
  "contraindications": ["acute joint inflammation"],
  "evidence_level": "High",
  "source": "OARSI Guidelines for Non-Surgical Management of Knee OA"
}
```

---

## Benefits

1. **Separation of Concerns**: Knowledge base is now a data file, not code
2. **Easier Updates**: Update recommendations without changing code
3. **Version Control**: Track knowledge base changes separately
4. **Validation**: Automatic check that embeddings match knowledge base
5. **Clear Errors**: Helpful error messages if files are missing

---

## Usage

The recommendation agent will automatically:
1. Load `parametric_knowledge.json`
2. Load `parametric_embeddings.npy`
3. Validate that counts match
4. Use embeddings for semantic ranking

If files are missing, it will raise a `FileNotFoundError` with instructions to run:
```bash
python scripts/generate_embeddings.py
```

---

## Testing

To verify the changes work correctly:

```python
from app.agents.recommendation_agent import generate_recommendation

# Test with sample data
result = generate_recommendation(
    kl_grade=2,
    pain_level=5,
    mobility_level="moderate",
    db=session
)

print(f"Generated {len(result['lifestyle_plan'])} recommendations")
print(f"Warnings: {len(result['warnings'])}")
```

---

## Migration Notes

- **No breaking changes** to the API
- **Backward compatible** with existing code
- **Embeddings regenerated** to match the new knowledge base format
- **22 records** in the knowledge base (vs 14 previously)

---

**Date**: April 17, 2026  
**Status**: ✅ Complete
