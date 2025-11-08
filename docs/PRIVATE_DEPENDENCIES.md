# Private Dependencies Setup

This project depends on two private packages hosted on GitLab:
- `vastdbmanager` - VAST database management library
- `vasts3` - VAST S3 client library

These packages are **not publicly available** and require authentication to install.

## Quick Start: Using Pre-built Wheels (Recommended for Docker)

If you have access to the local GitLab packages, you can build wheel files that are included in the repository:

```bash
# Build wheels from local packages
./scripts/build_private_wheels.sh

# The wheels will be in wheels/ directory and can be committed to the repo
# Docker builds will automatically use these wheels
```

This approach is **recommended for Docker builds** as it doesn't require GitLab authentication during the build process.

## Installation Methods

### Method 1: GitLab Personal Access Token (Recommended)

1. **Create a GitLab Personal Access Token**:
   - Go to GitLab → Settings → Access Tokens
   - Create a token with `read_api` and `read_repository` scopes
   - Save the token securely

2. **Install using pip with authentication**:

   ```bash
   # Set environment variable (recommended)
   export GITLAB_TOKEN=your_token_here
   
   # Install dependencies
   pip install --index-url https://__token__:${GITLAB_TOKEN}@gitlab.com/api/v4/projects/PROJECT_ID/packages/pypi/simple vastdbmanager vasts3
   ```

   Or use pip's credential helper:
   ```bash
   pip install vastdbmanager vasts3 --extra-index-url https://__token__:${GITLAB_TOKEN}@gitlab.com/api/v4/projects/PROJECT_ID/packages/pypi/simple
   ```

3. **For requirements.txt installation**:

   Create a `.pip.conf` file in your home directory (`~/.pip/pip.conf` on Linux/Mac, `%APPDATA%\pip\pip.ini` on Windows):

   ```ini
   [global]
   extra-index-url = https://__token__:YOUR_TOKEN@gitlab.com/api/v4/projects/PROJECT_ID/packages/pypi/simple
   ```

   Then install normally:
   ```bash
   pip install -r requirements.txt
   ```

### Method 2: GitLab Deploy Token

1. **Create a GitLab Deploy Token**:
   - Go to your GitLab project → Settings → Repository → Deploy Tokens
   - Create a token with `read_repository` scope
   - Save the username and token

2. **Install directly from Git repository**:

   ```bash
   pip install git+https://<deploy_token_username>:<deploy_token>@gitlab.com/your-group/vastdbmanager.git
   pip install git+https://<deploy_token_username>:<deploy_token>@gitlab.com/your-group/vasts3.git
   ```

### Method 3: SSH Key (For Development)

If you have SSH access to the GitLab repositories:

```bash
pip install git+ssh://git@gitlab.com/your-group/vastdbmanager.git
pip install git+ssh://git@gitlab.com/your-group/vasts3.git
```

### Method 4: Local Installation

If you have the packages locally:

```bash
# Clone the repositories
git clone git@gitlab.com:your-group/vastdbmanager.git
git clone git@gitlab.com:your-group/vasts3.git

# Install in development mode
cd vastdbmanager && pip install -e . && cd ..
cd vasts3 && pip install -e . && cd ..
```

## Docker Installation

### Method 1: Using Pre-built Wheels (Recommended)

The repository includes pre-built wheel files in the `wheels/` directory. The Dockerfile automatically installs these if available:

```bash
# Build wheels from local packages (if you have access)
./scripts/build_private_wheels.sh

# Build Docker image (wheels will be used automatically)
docker build -t tams-api .
```

### Method 2: Using GitLab Token

If wheels are not available, you can pass the GitLab token as a build argument:

```dockerfile
# In Dockerfile
ARG GITLAB_TOKEN
RUN pip install --index-url https://__token__:${GITLAB_TOKEN}@gitlab.com/api/v4/projects/PROJECT_ID/packages/pypi/simple vastdbmanager vasts3
```

Build with:
```bash
docker build --build-arg GITLAB_TOKEN=your_token_here .
```

Or use Docker secrets for production:
```bash
echo "your_token_here" | docker secret create gitlab_token -
```

## CI/CD Setup

For CI/CD pipelines, use GitLab CI/CD variables:

```yaml
# .gitlab-ci.yml
variables:
  PIP_EXTRA_INDEX_URL: "https://__token__:${CI_JOB_TOKEN}@gitlab.com/api/v4/projects/${VASTDBMANAGER_PROJECT_ID}/packages/pypi/simple"

# Or use a project access token
before_script:
  - pip install --index-url https://__token__:${GITLAB_ACCESS_TOKEN}@gitlab.com/api/v4/projects/${VASTDBMANAGER_PROJECT_ID}/packages/pypi/simple vastdbmanager vasts3
```

## Environment Variables

You can set these environment variables to configure authentication:

- `GITLAB_TOKEN` - Personal access token for GitLab
- `GITLAB_USERNAME` - Username for deploy token
- `GITLAB_DEPLOY_TOKEN` - Deploy token
- `PIP_EXTRA_INDEX_URL` - Extra PyPI index URL with authentication

## Troubleshooting

### Error: "Could not find a version that satisfies the requirement"

This means pip cannot access the private repository. Check:
1. Token is valid and has correct scopes
2. Project ID is correct
3. Package names are correct
4. Network access to GitLab

### Error: "401 Unauthorized"

Your token may be expired or invalid. Generate a new token.

### Error: "403 Forbidden"

Your token doesn't have sufficient permissions. Ensure it has `read_api` and `read_repository` scopes.

## Security Notes

⚠️ **Never commit tokens or credentials to the repository**

- Use environment variables or secret management systems
- Use `.gitignore` to exclude credential files
- Rotate tokens regularly
- Use deploy tokens with minimal permissions for CI/CD

## Alternative: Public Mirror

If these packages become public in the future, update `requirements.txt` to use the public PyPI index:

```txt
vastdbmanager>=1.0.0
vasts3>=1.0.0
```

