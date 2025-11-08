<!-- 4bfbcc60-1e1c-4ba3-b763-bb765e060d46 f9314e26-f383-40c3-aeb0-e298686a3d63 -->
# Package Reorganization Plan

## Overview

Reorganize codebase to have two independent packages under `src/` with proper Python packaging structure:

- `src/server/vasttamsserver/` (server code, currently `src/vasttams/`)
- `src/client/vasttamsclient/` (client code, currently `tams_client/src/tams_client/`)

Both packages will be independently installable with their own setup files in their respective directories.

## Phase 1: Server Package Reorganization

### 1.1 Create server directory structure

- Create `src/server/` directory
- Move `src/vasttams/` → `src/server/vasttamsserver/`
- Update `src/server/vasttamsserver/__init__.py` to reflect new package name

### 1.2 Move and update server package configuration

- Move `src/setup.py` → `src/server/setup.py`
- Move `src/pyproject.toml` → `src/server/pyproject.toml`
- Move `src/requirements.txt` → `src/server/requirements.txt` (if exists)
- Move `src/MANIFEST.in` → `src/server/MANIFEST.in` (if exists)
- Update `src/server/setup.py`:
- Change `name="vasttams"` → `name="vasttamsserver"`
- Update `packages=find_packages(where=".")` or `packages=["vasttamsserver"]`
- Update `package_dir={"": "."}` to point to current directory
- Update entry point: `"tams=vasttamsserver.main:main"`
- Update `src/server/pyproject.toml`:
- Change `name = "vasttams"` → `name = "vasttamsserver"`
- Update `[tool.setuptools]` section: `packages = ["vasttamsserver"]`
- Update `[tool.setuptools.package-dir]`: `"" = "."`
- Update `[project.scripts]`: `tams = "vasttamsserver.main:main"`
- Update `[tool.setuptools.package-data]`: `vasttamsserver = [...]`

### 1.3 Update all server internal imports

- All files in `src/server/vasttamsserver/` that import from `vasttams.*` need to change to `vasttamsserver.*`
- Use find/replace: `from vasttams.` → `from vasttamsserver.`
- Use find/replace: `import vasttams.` → `import vasttamsserver.`

## Phase 2: Client Package Reorganization

### 2.1 Create client directory structure

- Create `src/client/` directory
- Move `tams_client/src/tams_client/` → `src/client/vasttamsclient/`
- Update `src/client/vasttamsclient/__init__.py` to reflect new package name

### 2.2 Move and update client package configuration

- Move `tams_client/setup.py` → `src/client/setup.py`
- Move `tams_client/pyproject.toml` → `src/client/pyproject.toml`
- Move `tams_client/requirements.txt` → `src/client/requirements.txt`
- Move `tams_client/README.md` → `src/client/README.md` (optional)
- Update `src/client/setup.py`:
- Change `name="tams-client"` → `name="vasttamsclient"`
- Update `packages=find_packages(where=".")` or `packages=["vasttamsclient"]`
- Update `package_dir={"": "."}` to point to current directory
- Update `src/client/pyproject.toml`:
- Change `name = "tams-client"` → `name = "vasttamsclient"`
- Update `[tool.setuptools]` section: `packages = ["vasttamsclient"]`
- Update `[tool.setuptools.package-dir]`: `"" = "."`

### 2.3 Update all client internal imports

- All files in `src/client/vasttamsclient/` that import from `tams_client.*` need to change to `vasttamsclient.*`
- Use find/replace: `from tams_client.` → `from vasttamsclient.`
- Use find/replace: `import tams_client.` → `import vasttamsclient.`

## Phase 3: Update External References

### 3.1 Update entry point scripts

- `run.py`: Change `from vasttams.core.config` → `from vasttamsserver.core.config`
- `run.py`: Change `"vasttams.main:app"` → `"vasttamsserver.main:app"`
- `run_dev.py`: Change `from vasttams.core.config` → `from vasttamsserver.core.config`
- `run_dev.py`: Change `"vasttams.main:app"` → `"vasttamsserver.main:app"`
- `run_dev.py`: Change `reload_dirs=["src/vasttams"]` → `reload_dirs=["src/server/vasttamsserver"]`

### 3.2 Update test files (~98 files)

- Use find/replace across `tests/` directory:
- `from vasttams.` → `from vasttamsserver.`
- `import vasttams.` → `import vasttamsserver.`
- Update `tests/conftest.py`:
- Change `from vasttams.core.config` → `from vasttamsserver.core.config`
- Update any cache paths that reference "vasttams"

### 3.3 Update management scripts

- Update all `mgmt/*.py` files:
- `from vasttams.` → `from vasttamsserver.`
- `import vasttams.` → `import vasttamsserver.`

### 3.4 Update documentation

- Update `README.md` (main) to reflect new package structure and names
- Update `NOTES.md` to document the reorganization
- Update `EDITS.md` to track the changes
- Update `docs/` directory files:
- `docs/README.md`
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `docs/USAGE.md`
- Any other docs that reference package names or paths
- Update `src/server/README.md` (if exists) or create one for server package
- Update `src/client/README.md` (if exists) or create one for client package

## Phase 4: Cleanup and Verification

### 4.1 Remove old directories

- Remove `tams_client/` directory (after confirming all files moved)
- Verify no remaining references to old paths

### 4.2 Update .gitignore if needed

- Ensure both packages are properly tracked

### 4.3 Verify independent installation

- Test: `cd src && pip install -e .` (should install vasttamsserver
- Test: `cd src && pip install -e . -e .` with both packages (if using separate setup files)
- Or test installing each package independently

## Implementation Strategy

### Minimize Import Changes

1. Use systematic find/replace for all import statements
2. Update internal imports first (within each package)
3. Then update external imports (tests, scripts, mgmt)
4. Use grep to verify all changes are complete

### Independent Development/Deployment

- Each package has its own setup.py/pyproject.toml in `src/`
- Server: `cd src && pip install -e .` (installs vasttamsserver)
- Client: `cd src && pip install -e .` with client setup (installs vasttamsclient)
- Both can be installed together or separately
- Consider using separate setup files or a unified setup that handles both

## Files to Modify

**Server Package:**

- `src/vasttams/` → `src/vasttamsserver/` (entire directory rename)
- `src/setup.py` (package name, entry points)
- `src/pyproject.toml` (package name, configuration)
- All files in `src/vasttamsserver/` (internal imports)

**Client Package:**

- `tams_client/src/tams_client/` → `src/vasttamsclient/` (move and rename)
- `tams_client/setup.py` → `src/setup_client.py` (move and update)
- `tams_client/pyproject.toml` → `src/pyproject_client.toml` (move and update)
- All files in `src/vasttamsclient/` (internal imports)

**External Files:**

- `run.py` (imports)
- `run_dev.py` (imports, reload_dirs)
- `tests/` directory (~98 files with imports)
- `mgmt/` directory (all Python files with imports)
- `src/README.md` (documentation)

## Notes

- No backward compatibility needed
- Both packages remain under `src/` for consistency
- Use systematic find/replace to minimize errors
- Test imports after each phase to catch issues early