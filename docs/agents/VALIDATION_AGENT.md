# Validation Agent (Gatekeeper) - Implementation Guide

**Date:** June 16, 2026 (Updated from April 18, 2026)  
**Status:** ✅ Complete  
**Model:** CLIP Zero-Shot Classifier (openai/clip-vit-base-patch32)  
**Purpose:** Reject Out-of-Distribution (OOD) images before diagnostic pipeline

---

## 📋 Overview

The **Validation Agent** (also called "Gatekeeper") is a zero-shot image classification model that validates whether an uploaded image is a valid knee X-ray before it reaches the main diagnostic CNN.

**Why it's needed:**
- Prevents garbage uploads (random photos, documents, etc.)
- Blocks wrong body part images (hands, feet, hips, etc.)
- Rejects corrupt or malformed files
- Protects the diagnostic CNN from OOD inputs that could cause false predictions

**Why CLIP instead of MobileNetV2:**
- No training data required (uses pretrained model)
- Better generalization to diverse OOD images
- Semantic understanding of "knee x-ray" concept
- More robust to edge cases and novel OOD types

---

## 🏗️ Architecture

### File Location
`app/agents/validation_agent.py`

### Model Details
- **Architecture:** CLIP (Contrastive Language-Image Pre-Training)
- **Model:** openai/clip-vit-base-patch32 (from HuggingFace)
- **Method:** Zero-shot image classification
- **Input:** Raw image bytes (any format: JPEG, PNG, etc.)
- **Output:** Confidence scores for candidate labels
- **Threshold:** Confidence > 0.5 for "a knee x-ray" label
- **Candidate Labels:** 6 labels including "a knee x-ray", "a hand x-ray", "a chest x-ray", etc.

### Design Pattern: Singleton
- Pipeline loaded **once** at module initialization
- Reused across all requests for efficiency
- Automatic GPU acceleration when available, falls back to CPU

---

## 🔧 Implementation Details

### 1. Model Loading (Singleton)

```python
class ValidationAgent:
    _instance: Optional["ValidationAgent"] = None
    _pipeline: Optional[pipeline] = None
    
    LABELS = [
        "a knee x-ray",
        "a black and white logo",
        "a regular photo of a person",
        "a scanned document",
        "a hand x-ray",
        "a chest x-ray",
    ]
    
    def __new__(cls):
        """Singleton pattern - ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(ValidationAgent, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize or reuse the loaded pipeline."""
        if ValidationAgent._pipeline is None:
            self._load_model()
    
    def _load_model(self):
        """Load the CLIP zero-shot classification pipeline."""
        device = 0 if torch.cuda.is_available() else -1
        ValidationAgent._pipeline = pipeline(
            "zero-shot-image-classification",
            model="openai/clip-vit-base-patch32",
            device=device
        )
```

**Key Points:**
- Uses HuggingFace transformers pipeline
- Automatically detects and uses GPU if available
- Model downloaded from HuggingFace on first use (cached in `/tmp/huggingface`)
- Loaded on first initialization
- Shared across all requests
- Raises `RuntimeError` if loading fails

---

### 2. Image Preprocessing (SIMPLIFIED)

**IMPORTANT:** CLIP handles image preprocessing internally, so we only need to load and convert to RGB.

```python
def validate_image(self, image_bytes: bytes) -> bool:
    """Validate whether an image is a valid knee X-ray."""
    try:
        # Step 1: Load image from bytes using PIL
        image = Image.open(io.BytesIO(image_bytes))
        
        # Step 2: Convert to RGB (CLIP expects RGB)
        image = image.convert("RGB")
        
        # CLIP pipeline handles resizing and normalization internally
        
        # Step 3: Run zero-shot classification
        results = ValidationAgent._pipeline(image, candidate_labels=self.LABELS)
        
        # Step 4: Get top prediction
        best_guess = results[0]['label']
        confidence = results[0]['score']
        
        # Step 5: Apply threshold
        is_valid = best_guess == "a knee x-ray" and confidence > 0.5
        return is_valid
        
    except Exception as e:
        # Any error (corrupt file, invalid format, etc.) → reject
        return False
```

**Preprocessing Steps Explained:**

| Step | Operation | Purpose |
|------|-----------|---------|
| 1 | `PIL.Image.open(io.BytesIO(image_bytes))` | Load image from raw bytes |
| 2 | `.convert("RGB")` | Convert to 3-channel RGB |
| 3 | `pipeline(image, candidate_labels=LABELS)` | CLIP handles preprocessing + inference |
| 4 | `results[0]['label']` | Get top predicted label |
| 5 | `results[0]['score']` | Get confidence score |
| 6 | `best_guess == "a knee x-ray" and confidence > 0.5` | Apply threshold |

---

### 3. Inference & Return Logic

```python
# Zero-shot classification output: confidence scores for each label
best_guess = results[0]['label']  # e.g., "a knee x-ray"
confidence = results[0]['score']  # e.g., 0.87

if best_guess == "a knee x-ray" and confidence > 0.5:
    return True  # Valid knee X-ray → proceed to diagnostic CNN
else:
    return False  # OOD/invalid → reject
```

**Error Handling:**
- Wrapped in `try/except` block
- Any exception (corrupt file, invalid format, parsing error) → returns `False`
- Gracefully rejects problematic images without crashing
- Detailed debug logging for troubleshooting

---

## 🔗 Integration into Diagnostic Pipeline

### Updated Flow

```
┌─────────────────────────────────────────────────────────────┐
│  POST /api/v1/diagnostic/analyze                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Validate image ownership (user_id check)                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Download image bytes from S3                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Gatekeeper Validation ⭐ NEW                            │
│     - validate_image(image_bytes)                           │
│     - If False → HTTP 400 error                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ (only if True)
┌─────────────────────────────────────────────────────────────┐
│  4. Diagnostic Agent (CNN) → KL grade prediction            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Upload processed image to S3                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Recommendation Agent (RAG) → lifestyle advice           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  7. Persist Report to Neon DB                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  8. Return Report to Client                                 │
└─────────────────────────────────────────────────────────────┘
```

### Code Integration

**Import:**
```python
from app.agents.validation_agent import validate_image
```

**Integration Point:**
```python
# ── 3. Download image bytes from S3 ──────────────────────────────────
try:
    response = requests.get(image.s3_url, timeout=30)
    response.raise_for_status()
    image_bytes = response.content
except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=f"Failed to download image from S3: {e}",
    )

# ── 4. Validate image is a valid knee X-ray (Gatekeeper) ────────────
# This prevents OOD images from reaching the diagnostic CNN
if not validate_image(image_bytes):
    raise HTTPException(
        status_code=400,
        detail="Image validation failed. Please upload a clear, weight-bearing knee X-ray.",
    )
```

**Error Response:**
```json
{
  "detail": "Image validation failed. Please upload a clear, weight-bearing knee X-ray."
}
```
HTTP Status: `400 Bad Request`

---

## 🧪 Testing Recommendations

### Unit Tests

1. **Valid Knee X-ray:**
   - Input: Known valid knee X-ray image
   - Expected: `True`

2. **OOD Image (wrong body part):**
   - Input: Hand X-ray, foot X-ray, hip X-ray
   - Expected: `False`

3. **Non-medical Image:**
   - Input: Photo of a cat, document, random photo
   - Expected: `False`

4. **Corrupt File:**
   - Input: Truncated/corrupted JPEG
   - Expected: `False` (exception caught)

5. **Invalid Format:**
   - Input: Text file, PDF, executable
   - Expected: `False` (exception caught)

6. **Threshold Edge Case:**
   - Input: Image with prediction ≈ 0.5
   - Expected: `False` (≥ 0.5 is OOD)

### Integration Tests

1. **Full Pipeline with Valid Image:**
   - Upload valid knee X-ray
   - Verify report generated successfully

2. **Full Pipeline with OOD Image:**
   - Upload hand X-ray
   - Verify HTTP 400 error returned
   - Verify no report created

3. **Full Pipeline with Corrupt File:**
   - Upload corrupted image
   - Verify HTTP 400 error returned

---

## 📊 Performance Considerations

### Model Loading
- **Cost:** ~2-5 seconds (first request only, downloads from HuggingFace)
- **Strategy:** Singleton pattern avoids repeated loading
- **Caching:** Model cached in `/tmp/huggingface` directory

### Inference Time
- **Per Image:** ~50-150ms (on GPU), ~200-500ms (on CPU)
- **Impact:** Moderate added latency to pipeline
- **Optimization:** GPU acceleration significantly improves performance

### Memory Usage
- **Model Size:** ~600MB (CLIP ViT-B/32)
- **Strategy:** Shared across all requests
- **GPU Memory:** ~1-2GB VRAM when using GPU

---

## 🔐 Error Handling

### Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| Model loading fails | Raises `RuntimeError` (startup failure) |
| Image parsing fails | Returns `False` (rejects image) |
| Inference fails | Returns `False` (rejects image) |
| Corrupt file | Returns `False` (exception caught) |

### User-Friendly Error Messages

```python
if not validate_image(image_bytes):
    raise HTTPException(
        status_code=400,
        detail="Image validation failed. Please upload a clear, weight-bearing knee X-ray.",
    )
```

**Why this message?**
- Clear and actionable
- Doesn't expose technical details
- Guides user to correct behavior

---

## 🚀 Deployment Checklist

- [ ] HuggingFace cache directory writable (`/tmp/huggingface`)
- [ ] Internet access available for first-time model download (or model pre-cached)
- [ ] GPU drivers installed (optional, but recommended for performance)
- [ ] Singleton pattern tested (pipeline loaded only once)
- [ ] Error handling tested (corrupt files, invalid formats)
- [ ] Integration tested with full diagnostic pipeline
- [ ] Performance tested (inference time <200ms per image on GPU)
- [ ] Confidence threshold validated on test set (aim for >95% accuracy on OOD detection)

---

## 📚 Related Documentation

- [Diagnostic Pipeline](../README.md)
- [Recommendation Agent](./RAG_AGENT_PROFILE_FILTERING.md)
- [Project Context](../../PROJECT_CONTEXT.md)

---

## 🔍 Troubleshooting

### Issue: Model loading fails at startup
**Solution:** Check internet connection for HuggingFace download. Verify `/tmp/huggingface` directory is writable. Check Docker logs for detailed error messages.

### Issue: All images rejected (even valid ones)
**Solution:** Check confidence scores in debug logs. May need to lower threshold from 0.5 to 0.4. Verify candidate labels are appropriate.

### Issue: OOD images not being rejected
**Solution:** Check confidence scores in debug logs. May need to raise threshold from 0.5 to 0.6. Consider adding more specific candidate labels.

### Issue: Slow inference time
**Solution:** Ensure GPU is available and being used (check logs for "Loading CLIP gatekeeper on device: GPU"). Consider using a smaller CLIP model variant.

### Issue: HuggingFace cache permission errors
**Solution:** Ensure `HF_HOME=/tmp/huggingface` is set in Dockerfile and directory has correct permissions (`chown -R appuser:appgroup /tmp/huggingface`).

---

**Author:** AI Development Agent  
**Reviewed By:** Pending  
**Approved for Production:** Pending model validation
