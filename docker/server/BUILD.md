# Docker Build Instructions

## ⚠️ IMPORTANT: Build from Project Root

The Dockerfile expects the build context to be the **project root directory**, not the `docker/` or `src/` directories.

### ✅ Correct Way (from project root):

**Step 1: Navigate to project root**
```bash
cd ~/images/vasttams
# Make sure you're in the project root (where docker/, src/, config/ directories are)
```

**Step 2: Build the image**
```bash
docker build -f docker/server/Dockerfile -t tams-api .
```

Or in one command:
```bash
cd ~/images/vasttams && docker build -f docker/server/Dockerfile -t tams-api .
```

### ❌ Wrong Ways (causes errors):

```bash
# ❌ WRONG: Sets build context to docker/ directory
docker build -t tams-api docker/.

# ❌ WRONG: Running from src/ directory - can't find docker/Dockerfile
cd src
docker build -f docker/server/Dockerfile -t tams-api .
# Error: unable to evaluate symlinks in Dockerfile path: lstat docker: no such file or directory
```

## Why?

When you run `docker build docker/.`, Docker uses `docker/` as the build context. All `COPY` commands in the Dockerfile are then relative to that directory. Since `src/server/requirements.txt` is at the project root level, it can't be found.

When you run `docker build -f docker/Dockerfile .`, Docker uses `.` (current directory = project root) as the build context, and `-f docker/Dockerfile` just tells Docker where to find the Dockerfile. This way, `COPY src/server/requirements.txt` works correctly.

## Git LFS Requirements

⚠️ **IMPORTANT**: This repository uses Git LFS for wheel files. You must pull LFS objects before building.

### Setup

```bash
# Install Git LFS (if not already installed)
git lfs install

# Pull LFS objects (wheel files) - REQUIRED before building
git lfs pull

# Verify wheels are present
ls wheels/*.whl
```

### Why Git LFS?

The `wheels/` directory contains pre-built wheel files for private dependencies (`vastdbmanager` and `vasts3`). These are stored via Git LFS because:
- Wheel files are binary and can be large
- Git LFS keeps the repository size manageable
- Enables faster clone operations (LFS files downloaded on demand)
- Allows Docker builds without GitLab authentication

### Build Behavior

The Dockerfile automatically handles wheels:

1. **If wheels exist** (`wheels/*.whl`): Installs them automatically (no GitLab auth needed)
2. **If wheels missing**: Attempts to install from `requirements.txt` (requires GitLab authentication)

**Always run `git lfs pull` before building to ensure wheels are available.**

### Troubleshooting

**Error: "No wheels found"**
```bash
# Make sure you've pulled LFS objects
git lfs pull

# Check if wheels directory exists and has files
ls -la wheels/
```

**Error: "Wheels directory is empty"**
- The wheels are stored in Git LFS, not directly in the repository
- Run `git lfs pull` to download them
- If you don't have Git LFS installed, install it: `git lfs install`

**Error: "Cannot find wheels" during Docker build**
- Ensure you're building from the project root (not from `docker/` directory)
- The Dockerfile expects `wheels/` to be at the project root level
- Verify: `ls wheels/*.whl` should show `.whl` files

## Using docker-compose (Recommended)

The easiest way is to use docker-compose, which automatically sets the correct build context:

```bash
cd docker
docker-compose build
```

The `docker-compose.yml` file correctly sets:
```yaml
build:
  context: ..          # Project root
      dockerfile: docker/server/Dockerfile
```

