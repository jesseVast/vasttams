# Requirements Files Organization

This document explains the organization of Python requirements files in the TAMS project.

## 📁 **File Structure**

```
bbctams/
├── requirements.txt                    # Main application requirements
├── requirements-dev.txt                # Development dependencies
├── requirements-prod.txt               # Production dependencies
├── REQUIREMENTS.md                     # This documentation
├── app/
│   └── storage/
│       └── vastdbmanager/
│           └── requirements-vastdbmanager.txt  # Module-specific requirements
├── docker/
│   └── requirements.txt               # Docker container requirements
└── tests/
    └── requirements.txt               # Testing dependencies
```

## 🔧 **Requirements Files**

### **1. `requirements.txt` (Root)**
**Purpose**: Main application dependencies for all environments
**Location**: Project root
**Usage**: Base requirements for development, testing, and production

**Key Dependencies**:
- FastAPI and web framework
- VAST database and analytics
- S3 storage and AWS
- Authentication and security
- Telemetry and observability

### **2. `requirements-dev.txt`**
**Purpose**: Development and debugging tools
**Location**: Project root
**Usage**: `pip install -r requirements-dev.txt`

**Additional Dependencies**:
- Code quality tools (black, flake8, mypy)
- Testing frameworks (pytest, coverage)
- Development utilities (ipython, jupyter)
- Performance profiling tools
- Documentation generators

### **3. `requirements-prod.txt`**
**Purpose**: Minimal production dependencies
**Location**: Project root
**Usage**: `pip install -r requirements-prod.txt`

**Features**:
- Essential runtime dependencies only
- No development or testing tools
- Optimized for production containers
- Security-focused package selection

### **4. `docker/requirements.txt`**
**Purpose**: Docker container dependencies
**Location**: `docker/` directory
**Usage**: Container builds and deployments

**Features**:
- Container-optimized versions
- Production-ready dependencies
- Gunicorn for production serving
- No development tools

### **5. `tests/requirements.txt`**
**Purpose**: Testing-specific dependencies
**Location**: `tests/` directory
**Usage**: `pip install -r tests/requirements.txt`

**Additional Dependencies**:
- Advanced testing frameworks
- Performance testing tools
- Database testing utilities
- API testing libraries

### **6. `app/storage/vastdbmanager/requirements-vastdbmanager.txt`**
**Purpose**: VASTDBManager module dependencies
**Location**: Module directory
**Usage**: Module-specific installations

**Dependencies**:
- VAST database SDK
- PyArrow for data handling
- DuckDB for analytics
- Ibis for data manipulation

## 🚀 **Installation Commands**

### **Development Environment**
```bash
# Install main requirements
pip install -r requirements.txt

# Install development tools
pip install -r requirements-dev.txt
```

### **Production Environment**
```bash
# Install production requirements only
pip install -r requirements-prod.txt
```

### **Testing Environment**
```bash
# Install testing dependencies
pip install -r tests/requirements.txt
```

### **Docker Build**
```bash
# Docker will use docker/requirements.txt automatically
cd docker
docker build -t tams-api .
```

### **Module Development**
```bash
# Install module-specific requirements
cd app/storage/vastdbmanager
pip install -r requirements-vastdbmanager.txt
```

## 📋 **Dependency Management**

### **Adding New Dependencies**

1. **Runtime Dependencies**: Add to `requirements.txt`
2. **Development Dependencies**: Add to `requirements-dev.txt`
3. **Testing Dependencies**: Add to `tests/requirements.txt`
4. **Production Dependencies**: Add to `requirements-prod.txt`
5. **Module Dependencies**: Add to module-specific requirements file

### **Updating Dependencies**

```bash
# Update all requirements
pip install --upgrade -r requirements.txt
pip install --upgrade -r requirements-dev.txt

# Check for security vulnerabilities
safety check -r requirements.txt
safety check -r requirements-dev.txt
```

### **Pinning Versions**

- **Production**: Pin exact versions for stability
- **Development**: Allow minor version updates
- **Testing**: Pin major versions for compatibility

## 🔒 **Security Considerations**

### **Production Security**
- Use `requirements-prod.txt` for production
- Regularly update dependencies
- Scan for vulnerabilities with `safety`
- Avoid development tools in production

### **Development Security**
- Use virtual environments
- Keep development dependencies separate
- Regular security audits
- Use `pip-audit` for vulnerability scanning

## 📊 **Best Practices**

### **File Organization**
- ✅ Keep requirements organized by purpose
- ✅ Use relative paths for includes (`-r ../requirements.txt`)
- ✅ Document purpose and usage
- ✅ Separate development and production dependencies

### **Version Management**
- ✅ Pin versions for production stability
- ✅ Use version ranges for development flexibility
- ✅ Regular dependency updates
- ✅ Security vulnerability monitoring

### **Dependency Selection**
- ✅ Only include necessary dependencies
- ✅ Avoid duplicate dependencies across files
- ✅ Use compatible version ranges
- ✅ Consider security implications

## 🆘 **Troubleshooting**

### **Common Issues**

#### **Version Conflicts**
```bash
# Check for conflicts
pip check

# Resolve conflicts
pip install --upgrade --force-reinstall -r requirements.txt
```

#### **Missing Dependencies**
```bash
# Install missing packages
pip install -r requirements.txt --no-deps

# Check what's missing
pip install -r requirements.txt --dry-run
```

#### **Environment Issues**
```bash
# Create fresh virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install requirements
pip install -r requirements.txt
```

## 📚 **Additional Resources**

- [Python Packaging User Guide](https://packaging.python.org/)
- [pip User Guide](https://pip.pypa.io/en/stable/)
- [Python Virtual Environments](https://docs.python.org/3/library/venv.html)
- [Dependency Management Best Practices](https://pip.pypa.io/en/stable/user_guide/)

---

*Last Updated: August 2024*
*Version: 1.0*
