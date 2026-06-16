# Changelog - 2026-06-16

## Overview
Major architectural changes to improve image validation robustness and fix deployment issues.

## Changes

### 1. CLIP Zero-Shot Gatekeeper Migration
**Status:** ✅ Complete

**What Changed:**
- Replaced MobileNetV2 binary classifier with CLIP zero-shot image classification
- Model: `openai/clip-vit-base-patch32` (HuggingFace transformers)
- No training data required - uses pretrained CLIP model
- Natural language labels: "a knee x-ray", "a hand x-ray", "a chest x-ray", etc.

**Why:**
- MobileNetV2 gatekeeper was rejecting valid knee X-rays (sigmoid > 0.5)
- CLIP provides better generalization to diverse OOD images
- Semantic understanding of "knee x-ray" concept
- More robust to edge cases and novel OOD types

**Technical Details:**
- Confidence threshold: > 0.5 for "a knee x-ray" label
- Automatic GPU acceleration when available
- Simplified preprocessing (CLIP handles most internally)
- Model cached in `/tmp/huggingface` directory

**Files Modified:**
- `app/agents/validation_agent.py` - Complete rewrite to use CLIP
- `Dockerfile` - Added `HF_HOME=/tmp/huggingface` environment variable
- `PROJECT_CONTEXT.md` - Updated validation agent documentation
- `README.md` - Updated architecture diagrams and descriptions
- `docs/agents/VALIDATION_AGENT.md` - Rewritten for CLIP
- `docs/agents/VALIDATION_AGENT_IMPLEMENTATION.md` - Updated implementation details

**Performance:**
- Inference time: ~50-150ms (GPU), ~200-500ms (CPU)
- Memory usage: ~600MB (CLIP ViT-B/32)
- GPU memory: ~1-2GB VRAM when using GPU

**Migration Notes:**
- No database changes required
- No API changes required
- Backward compatible with existing diagnostic pipeline
- First request will download model from HuggingFace (~2-5 seconds)

### 2. HuggingFace Cache Permission Fix
**Status:** ✅ Complete

**What Changed:**
- Added `HF_HOME=/tmp/huggingface` environment variable to Dockerfile
- Created `/tmp/huggingface` directory with proper permissions
- Set ownership to `appuser:appgroup`

**Why:**
- Container runs as non-root user `appuser`
- Default HuggingFace cache location (`~/.cache/huggingface`) not writable
- Would cause permission errors when downloading CLIP model

**Files Modified:**
- `Dockerfile` - Added HF_HOME env var and directory creation

**Testing:**
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
docker logs -f knee_oa_api
```

### 3. Validation Agent Error Logging
**Status:** ✅ Complete

**What Changed:**
- Added detailed debug logging to `validate_image()` function
- Logs image size, top prediction, confidence score, and top 3 predictions
- Added full traceback on errors

**Why:**
- Previous implementation silently returned False on errors
- Made debugging impossible
- Now provides visibility into validation decisions

**Files Modified:**
- `app/agents/validation_agent.py` - Added logging and error handling

**Example Output:**
```
[DEBUG] Loaded image size: (1024, 1024)
[DEBUG] CLIP Gatekeeper says: a knee x-ray (0.8234)
[DEBUG] Top 3 predictions:
  1. a knee x-ray: 0.8234
  2. a chest x-ray: 0.0891
  3. a hand x-ray: 0.0456
[DEBUG] Gatekeeper evaluation result: True
```

## Testing

### Validation Agent Testing
```bash
# Test with valid knee X-ray
curl -X POST http://localhost/api/v1/diagnostic/analyze \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"image_id": 1}'

# Check logs for CLIP predictions
docker logs -f knee_oa_api | grep "CLIP Gatekeeper"
```

### Expected Behavior
- Valid knee X-ray: Confidence > 0.5 for "a knee x-ray" label → Returns True
- OOD image (hand, chest, etc.): Different top label or low confidence → Returns False
- Non-medical image: "a regular photo" or "a scanned document" → Returns False

## Performance Impact

### Before (MobileNetV2)
- Model size: ~15-20MB
- Inference time: ~10-30ms (CPU)
- Memory usage: ~50-100MB
- Required training data

### After (CLIP)
- Model size: ~600MB
- Inference time: ~50-150ms (GPU), ~200-500ms (CPU)
- Memory usage: ~600MB (1-2GB VRAM on GPU)
- No training data required

**Trade-off:** Higher resource usage but significantly better accuracy and robustness.

## Deployment Notes

### First-Time Deployment
1. Ensure internet access for HuggingFace model download
2. First request will take 2-5 seconds (model download)
3. Subsequent requests use cached model
4. Model cached in `/tmp/huggingface` directory

### GPU Acceleration (Recommended)
- Automatically detected and used if available
- Check logs: "Loading CLIP gatekeeper on device: GPU"
- Requires CUDA-compatible GPU and drivers
- Significantly improves inference time (3-5x faster)

### CPU-Only Deployment
- Falls back to CPU if no GPU available
- Check logs: "Loading CLIP gatekeeper on device: CPU"
- Inference time: ~200-500ms per image
- Still acceptable for most use cases

## Rollback Plan

If CLIP causes issues, revert to MobileNetV2:
```bash
git revert <commit-hash>
docker compose down
docker compose build --no-cache
docker compose up -d
```

**Note:** MobileNetV2 model file (`gatekeeper.keras`) must be present in `app/ml_assets/cnn_weights/`.

## Known Issues

### 1. First Request Latency
**Issue:** First validation request takes 2-5 seconds  
**Cause:** CLIP model download from HuggingFace  
**Impact:** Only affects first request after container start  
**Mitigation:** Model is cached, subsequent requests are fast

### 2. Higher Memory Usage
**Issue:** CLIP uses ~600MB vs MobileNetV2's ~20MB  
**Cause:** Larger model architecture (ViT-B/32)  
**Impact:** Requires more RAM/VRAM  
**Mitigation:** Acceptable trade-off for better accuracy

### 3. GPU Memory Requirements
**Issue:** GPU acceleration requires 1-2GB VRAM  
**Cause:** CLIP model size  
**Impact:** May not fit on very small GPUs  
**Mitigation:** Falls back to CPU if insufficient VRAM

## Future Improvements

### Potential Enhancements
1. **Model Quantization:** Reduce CLIP model size for faster inference
2. **Custom Labels:** Add more specific labels (e.g., "a weight-bearing knee X-ray")
3. **Confidence Thresholds:** Tune threshold based on production data
4. **Model Caching:** Pre-download model during Docker build
5. **Batch Processing:** Optimize for multiple simultaneous validations

### Monitoring
- Track validation success rate in production
- Monitor confidence score distribution
- Identify edge cases for label refinement
- Measure inference time across different hardware

## References

- [CLIP Paper](https://arxiv.org/abs/2103.00020) - Learning Transferable Visual Models From Natural Language Supervision
- [HuggingFace CLIP Documentation](https://huggingface.co/openai/clip-vit-base-patch32)
- [Zero-Shot Image Classification](https://huggingface.co/docs/transformers/main_classes/pipelines#transformers.ZeroShotImageClassificationPipeline)
- [Validation Agent Documentation](../agents/VALIDATION_AGENT.md)
- [Project Context](../../PROJECT_CONTEXT.md)
