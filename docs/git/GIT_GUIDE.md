# Git Configuration Guide

## ✅ What SHOULD Be Committed

### Source Code
- `app/` - All application code
- `tests/` - All test files
- `scripts/` - Utility scripts (except those with secrets)
- `alembic/versions/` - Database migrations

### Configuration Templates
- `.env.example` - Template for environment variables
- `docker-compose.yml` - Docker configuration
- `Dockerfile` - Container definition
- `requirements.txt` - Python dependencies
- `alembic.ini` - Alembic configuration

### Documentation
- `README.md`
- `PROJECT_CONTEXT.md`
- `SECURITY_AUDIT.md`
- `SECURITY_APPLIED.md`
- `SECURITY_FIXES.md`
- `GIT_GUIDE.md` (this file)

### CI/CD (if added later)
- `.github/` - GitHub Actions workflows
- `*.yml` - CI configuration files

---

## ❌ What Should NOT Be Committed

### Sensitive Files (ALWAYS IGNORED)
- `.env` - Contains secrets, keys, passwords
- `.env.local` - Local environment overrides
- `.env.*.local` - Any local environment files

### Virtual Environments
- `.venv/` - Python virtual environment
- `venv/` - Alternative venv name
- `ENV/` - Alternative venv name

### Cache & Build Artifacts
- `__pycache__/` - Python bytecode cache
- `*.pyc`, `*.pyo` - Compiled Python files
- `.pytest_cache/` - pytest cache
- `htmlcov/` - Coverage reports
- `build/`, `dist/` - Build outputs

### IDE & Editor Files
- `.vscode/` - VS Code settings
- `.idea/` - IntelliJ/PyCharm settings
- `*.swp`, `*.swo` - Vim swap files
- `.DS_Store` - macOS system files

### Database Files
- `*.db` - SQLite databases
- `*.sqlite` - SQLite databases
- `migrations/` - Generated migrations (keep alembic/versions/)

### ML Models & Assets
- `ml_assets/` - Model weights, embeddings
- `*.keras`, `*.h5`, `*.pkl` - Model files
- `*.pt`, `*.pth` - PyTorch models

### Logs & Temporary Files
- `*.log` - Log files
- `*.tmp`, `*.temp` - Temporary files
- `*.bak`, `*.backup` - Backup files

---

## 🔐 Security Checklist Before Committing

### 1. Check for Secrets
```bash
# Search for potential secrets in your changes
git diff --cached | grep -i "password\|secret\|key\|token"
```

### 2. Verify .env is Ignored
```bash
# Check if .env is in gitignore
grep "^\.env$" .gitignore
```

### 3. Review Changes
```bash
# Review all staged changes
git status

# Review diff before committing
git diff --cached
```

### 4. Pre-commit Hooks (Recommended)
Install pre-commit hooks to automatically check for secrets:
```bash
pip install pre-commit
pre-commit install
```

Add `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files

  - repo: https://github.com/securego/gosec
    rev: v2.15.0
    hooks:
      - id: gosec
        args: ['--severity=high', '--confidence=medium']
```

---

## 🚀 Recommended Git Workflow

### 1. Create Branch for Changes
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
```bash
# Add your changes
git add app/
git add tests/
```

### 3. Review Before Committing
```bash
# Check what will be committed
git status
git diff --cached

# Check for accidental secret inclusion
git diff --cached | grep -i "secret\|password\|key"
```

### 4. Commit with Clear Message
```bash
git commit -m "feat: add user profile logging

- Add ProfileLog model
- Implement change tracking
- Add history endpoint
- Write tests"
```

### 5. Push to Remote
```bash
git push origin feature/your-feature-name
```

---

## 🔍 Common Mistakes to Avoid

### ❌ Committing .env file
```bash
# WRONG - This will expose your secrets!
git add .env
git commit -m "add env"

# CORRECT - Only add the example
git add .env.example
git commit -m "add env template"
```

### ❌ Committing virtual environment
```bash
# WRONG
git add .venv/

# CORRECT
git add requirements.txt
```

### ❌ Committing database files
```bash
# WRONG
git add database.db

# CORRECT
git add alembic/versions/
```

### ❌ Committing model weights
```bash
# WRONG
git add ml_assets/cnn_weights/CNN.keras

# CORRECT
# Document in README how to download models
```

---

## 📋 Quick Reference Commands

### Check what's being tracked
```bash
git ls-files
```

### Check if a file is ignored
```bash
git check-ignore -v .env
```

### Remove accidentally tracked file
```bash
git rm --cached .env
git commit -m "remove .env from tracking"
```

### Clean untracked files
```bash
git clean -nd  # Dry run
git clean -fd  # Actually remove
```

### Show ignored files
```bash
git ls-files -o -i --exclude-standard
```

---

## 🛡️ If You Accidentally Committed Secrets

### 1. Immediate Action
```bash
# Remove the file from git history
git rm --cached .env
git commit -m "remove sensitive file"
git push --force
```

### 2. Rotate All Secrets
- Generate new SECRET_KEY
- Change database passwords
- Regenerate AWS keys
- Update all environment variables

### 3. Check Git History
```bash
# Search for secrets in history
git log -p --all | grep -i "password\|secret\|key"
```

### 4. Force Push to Remote
```bash
git push --force --all
git push --force --tags
```

---

## 📚 Additional Resources

- [Git Ignore Template](https://github.com/github/gitignore)
- [Pre-commit Hooks](https://pre-commit.com/)
- [Secret Scanning](https://github.com/securego/gosec)
- [Git Best Practices](https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows)

---

**Last Updated**: March 30, 2026
**Project**: Knee OA Backend
