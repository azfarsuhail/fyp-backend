# ADR-001: TensorFlow XLA ptxas Compiler Bug Fix

**Status**: ✅ Accepted  
**Date**: 2026-06-16  
**Authors**: Development Team  
**Related**: Dockerfile (RUNTIME stage), `tensorflow/tensorflow:2.15.0-gpu` base image

---

## 📋 Context & Problem Statement

### The Bug

When running our FastAPI backend in Docker with the `tensorflow/tensorflow:2.15.0-gpu` base image, the container **crashed completely** whenever the TensorFlow diagnostic model attempted inference. The error message was:

```
F external/local_xla/xla/service/gpu/nvptx_compiler.cc:619] ptxas returned an error during compilation of ptx to sass: 'INTERNAL: ptxas 12.3.103 has a bug that we think can affect XLA. Please use a different version.'
```

### Root Cause Analysis

1. **TensorFlow's XLA Optimizer**: Uses NVIDIA's `ptxas` compiler to compile PTX (Parallel Thread Execution) code to SASS (binary GPU assembly)
2. **Hardcoded Kill-Switch**: TensorFlow has a hardcoded check that blocks `ptxas` version `12.3.103` because it computes math incorrectly
3. **Locked-in Broken Compiler**: The `tensorflow:2.15.0-gpu` base image ships with this broken compiler at `/usr/local/cuda/bin/ptxas`
4. **No Escape Hatch**: Even when disabling XLA via flags, code using `jit_compile=True` forces XLA compilation regardless

### Impact

- **Complete container crashes** during model inference
- **No graceful degradation** possible
- **Pipeline failure** at the diagnostic model stage (after successful CLIP gatekeeper)

---

## 🚫 Failed Attempts (Historical Context)

### Attempt 1: Disable XLA via Environment Variable

**Approach**: Set `TF_XLA_FLAGS="--tf_xla_auto_jit=-1"` to disable XLA compilation

**Why It Failed**: Our code explicitly requires XLA compilation via `jit_compile=True` in the model definition. TensorFlow ignores the environment flag when the code explicitly requests XLA, and the crash still occurred.

**Lesson Learned**: Environment variable workarounds cannot bypass explicit code-level XLA requirements.

---

### Attempt 2: Install Patched Compiler via pip

**Approach**: Install the patched compiler via `pip install "nvidia-cuda-nvcc-cu12>=12.4"`

**Why It Failed**: Docker's `$PATH` hierarchy prioritizes `/usr/local/cuda/bin` over the virtual environment's `bin` directory. The system continued using the broken `/usr/local/cuda/bin/ptxas` instead of the patched version installed by pip.

**Lesson Learned**: Installing a patched binary is insufficient when the system's `$PATH` forces use of the broken binary.

---

## ✅ Decision: Search and Destroy Strategy

### The Solution

We implemented a **"Search and Destroy"** command in the **RUNTIME stage** of our Dockerfile that:

1. **Locates** the patched `ptxas` binary installed by pip in `/opt/venv`
2. **Destroys** the broken system binary at `/usr/local/cuda/bin/ptxas`
3. **Replaces** it with a symlink to the patched version

### Implementation

```dockerfile
# =====================================================================
# THE BULLETPROOF FIX: Search and Destroy the broken compiler
# 1. Finds exactly where pip installed the patched ptxas binary
# 2. Forcefully overwrites the broken one inside NVIDIA's locked folder
# =====================================================================
RUN PATCHED_PTXAS=$(find /opt/venv -name ptxas -type f | head -n 1) && \
    rm -f /usr/local/cuda/bin/ptxas && \
    ln -s $PATCHED_PTXAS /usr/local/cuda/bin/ptxas && \
    ln -s $PATCHED_PTXAS /usr/local/bin/ptxas
```

### Why This Works

1. **Precise Targeting**: Uses `find /opt/venv` to locate the exact patched binary installed by pip
2. **Forceful Replacement**: `rm -f` removes the broken binary before symlinking
3. **Dual Symlinks**: Creates symlinks in both `/usr/local/cuda/bin` (NVIDIA's expected location) and `/usr/local/bin` (system PATH)
4. **Runtime Stage**: Applied in the RUNTIME stage to ensure the patched binary is present

---

## 📊 Decision Factors

| Factor | Consideration |
|--------|---------------|
| **Base Image** | `tensorflow/tensorflow:2.15.0-gpu` (locked to CUDA 11.8) |
| **TensorFlow Version** | 2.15.0 (ships with broken ptxas 12.3.103) |
| **XLA Requirement** | Explicit `jit_compile=True` in diagnostic model |
| **System Constraints** | NVIDIA's `/usr/local/cuda` is read-only in base image |
| **Alternative** | Upgrade to newer TensorFlow base image (breaking change) |

---

## ⚠️ Warnings & Constraints

### DO NOT REMOVE THIS FIX

**Future developers must NOT remove or modify this Dockerfile command** because:

1. **The broken compiler is hardcoded** in the `tensorflow:2.15.0-gpu` base image
2. **TensorFlow will crash** if it detects ptxas version 12.3.103
3. **No workaround exists** without replacing the binary

### DO NOT UPGRADE BASE IMAGE WITHOUT TESTING

If you upgrade the TensorFlow base image (e.g., to `tensorflow/tensorflow:2.16.0-gpu` or later):

1. **Verify the ptxas version** in the new base image
2. **Test the fix** to ensure it still works
3. **Check for breaking changes** in TensorFlow 2.16+

### DO NOT MODIFY THE SEARCH PATH

The `find /opt/venv` command assumes pip installs the patched binary in the virtual environment. If you change the pip installation strategy, update this path accordingly.

---

## 🔄 Alternative Solutions Considered

### Option 1: Upgrade TensorFlow Base Image

**Approach**: Switch to `tensorflow/tensorflow:2.16.0-gpu` or later

**Pros**:
- Newer base image may include patched compiler
- Access to TensorFlow 2.16+ features

**Cons**:
- Breaking changes in TensorFlow API
- Requires extensive testing
- May require dependency updates

**Decision**: Rejected due to high risk and maintenance cost

---

### Option 2: Build Custom Base Image

**Approach**: Create a custom Docker image based on `tensorflow:2.15.0-gpu` with the patched compiler pre-installed

**Pros**:
- Cleaner separation of concerns
- Reusable across projects

**Cons**:
- Additional maintenance burden
- Requires building and hosting custom image
- Delays immediate fix

**Decision**: Rejected in favor of immediate fix in existing Dockerfile

---

## 📝 Related Documentation

- [Docker Audit](../docker/DOCKER_AUDIT.md) - Docker configuration audit
- [Docker Quick Reference](../docker/DOCKER_QUICKREF.md) - Docker commands and best practices
- [README.md](../README.md) - Main project documentation

---

## 📌 References

1. [TensorFlow XLA GPU Compilation](https://www.tensorflow.org/xla/operation_semantics#gpu_compilation)
2. [NVIDIA ptxas Compiler](https://docs.nvidia.com/cuda/parallel-thread-execution/)
3. [TensorFlow Docker Images](https://hub.docker.com/r/tensorflow/tensorflow/)
4. [CUDA Toolkit Documentation](https://docs.nvidia.com/cuda/)

---

**Last Updated**: 2026-06-16  
**Next Review**: When upgrading TensorFlow base image
