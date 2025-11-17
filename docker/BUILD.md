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
docker build -f docker/Dockerfile -t tams-api .
```

Or in one command:
```bash
cd ~/images/vasttams && docker build -f docker/Dockerfile -t tams-api .
```

### ❌ Wrong Ways (causes errors):

```bash
# ❌ WRONG: Sets build context to docker/ directory
docker build -t tams-api docker/.

# ❌ WRONG: Running from src/ directory - can't find docker/Dockerfile
cd src
docker build -f docker/Dockerfile -t tams-api .
# Error: unable to evaluate symlinks in Dockerfile path: lstat docker: no such file or directory
```

## Why?

When you run `docker build docker/.`, Docker uses `docker/` as the build context. All `COPY` commands in the Dockerfile are then relative to that directory. Since `src/server/requirements.txt` is at the project root level, it can't be found.

When you run `docker build -f docker/Dockerfile .`, Docker uses `.` (current directory = project root) as the build context, and `-f docker/Dockerfile` just tells Docker where to find the Dockerfile. This way, `COPY src/server/requirements.txt` works correctly.

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
  dockerfile: docker/Dockerfile
```

