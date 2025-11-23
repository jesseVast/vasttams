# Private Dependency Wheels

This directory contains pre-built wheel files for private dependencies:
- `vastdbmanager` - VAST database management library
- `vasts3` - VAST S3 client library

## Git LFS Storage

⚠️ **IMPORTANT**: These wheel files are stored using **Git LFS (Large File Storage)**, not directly in the Git repository.

### Why Git LFS?

- Wheel files are binary and can be large
- Git LFS keeps repository size manageable
- Enables faster clone operations (LFS files downloaded on demand)
- Allows Docker builds without GitLab authentication

### Setup

```bash
# Install Git LFS (one-time setup per machine)
git lfs install

# Pull LFS objects (wheel files) - REQUIRED after cloning
git lfs pull
```

### Verifying Wheels

After pulling LFS objects, verify wheels are present:

```bash
ls wheels/*.whl
# Should show:
# wheels/vastdbmanager-*.whl
# wheels/vasts3-*.whl
```

### Configuration

The `.gitattributes` file in the project root configures Git LFS:

```
wheels/*.whl filter=lfs diff=lfs merge=lfs -text
```

This ensures all `.whl` files in this directory are tracked by Git LFS.

## Building Wheels

To build the wheel files from local GitLab packages, run:

```bash
./scripts/build_private_wheels.sh
```

This script:
1. Builds wheel files from `~/Developer/gitlab/vaststore/vastdbmanager`
2. Builds wheel files from `~/Developer/gitlab/vaststore/vasts3`
3. Copies the `.whl` files to this directory

## Docker Usage

The Dockerfile automatically installs wheels from this directory if they exist. This allows Docker builds to work without requiring GitLab authentication.

## Updating Wheels

When the private packages are updated, rebuild the wheels:

```bash
./scripts/build_private_wheels.sh
```

Then commit the updated `.whl` files to the repository.

## Note

These wheel files are **binary distributions** of the private packages. They can be safely committed to the repository as they don't contain source code, only compiled Python bytecode and package metadata.

