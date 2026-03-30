# Git & Version Control Documentation

## 📦 Git Configuration

This folder contains Git configuration guides and best practices.

## 📄 Files

### [GIT_GUIDE.md](./GIT_GUIDE.md)
Comprehensive Git guide including:
- What to commit vs. what to ignore
- Security checklist before committing
- Recommended Git workflow
- Common mistakes to avoid
- Quick reference commands

## 🔒 Security Checklist

### Before Committing
- [ ] Check for secrets in changes
- [ ] Verify .env is ignored
- [ ] Review all staged changes
- [ ] Check for accidental secret inclusion

### What Should NOT Be Committed
- ❌ `.env` - Contains secrets, keys, passwords
- ❌ `.venv/` - Python virtual environment
- ❌ `__pycache__/` - Python bytecode cache
- ❌ `*.log` - Log files
- ❌ `*.db` - Database files
- ❌ `ml_assets/` - Model weights
- ❌ `*.pem`, `*.key` - SSL certificates

## 🚀 Recommended Workflow

### 1. Create Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
```bash
git add app/
git add tests/
```

### 3. Review Before Committing
```bash
git status
git diff --cached
```

### 4. Commit with Clear Message
```bash
git commit -m "feat: add user profile logging"
```

### 5. Push to Remote
```bash
git push origin feature/your-feature-name
```

## 📋 Quick Reference

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

## 🛡️ If You Accidentally Committed Secrets

### 1. Immediate Action
```bash
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
git log -p --all | grep -i "password\|secret\|key"
```

---

**Last Updated**: March 30, 2026
