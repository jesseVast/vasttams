# Private Dependency Wheels

This directory contains pre-built wheel files for private dependencies:
- `vastdbmanager` - VAST database management library
- `vasts3` - VAST S3 client library

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

