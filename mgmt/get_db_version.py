#!/usr/bin/env python3
"""
Simple script to get VAST database version information.
This script doesn't require a database connection.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_vast_version():
    """Get VAST database version information."""
    
    print("🔍 VAST Database Version Information")
    print("=" * 40)
    
    try:
        # Get vastdb version
        import vastdb
        print(f"✅ VAST DB Python client version: {vastdb.__version__}")
    except ImportError:
        print("❌ VAST DB Python client not installed")
    except Exception as e:
        print(f"❌ Failed to get VAST DB version: {e}")
    
    try:
        # Get ibis version
        import ibis
        print(f"✅ Ibis version: {ibis.__version__}")
    except ImportError:
        print("❌ Ibis not installed")
    except Exception as e:
        print(f"❌ Failed to get Ibis version: {e}")
    
    try:
        # Get pyarrow version
        import pyarrow
        print(f"✅ PyArrow version: {pyarrow.__version__}")
    except ImportError:
        print("❌ PyArrow not installed")
    except Exception as e:
        print(f"❌ Failed to get PyArrow version: {e}")
    
    try:
        # Get pandas version
        import pandas
        print(f"✅ Pandas version: {pandas.__version__}")
    except ImportError:
        print("❌ Pandas not installed")
    except Exception as e:
        print(f"❌ Failed to get Pandas version: {e}")


def get_config_info():
    """Get configuration information."""
    
    try:
        from app.config import get_settings
        
        print("\n🔧 Configuration Information")
        print("=" * 30)
        
        settings = get_settings()
        
        print(f"VAST Endpoint: {settings.vast_endpoint}")
        print(f"VAST Bucket: {settings.vast_bucket}")
        print(f"VAST Schema: {settings.vast_schema}")
        print(f"VAST Access Key: {settings.vast_access_key[:8]}...")
        print(f"VAST Secret Key: {settings.vast_secret_key[:8]}...")
        
        print(f"\nS3 Endpoint: {settings.s3_endpoint_url}")
        print(f"S3 Bucket: {settings.s3_bucket_name}")
        print(f"S3 Access Key: {settings.s3_access_key_id[:8]}...")
        print(f"S3 Secret Key: {settings.s3_secret_access_key[:8]}...")
        print(f"S3 Use SSL: {settings.s3_use_ssl}")
        
    except Exception as e:
        print(f"❌ Failed to get configuration: {e}")


def test_imports():
    """Test if all required modules can be imported."""
    
    print("\n📦 Module Import Test")
    print("=" * 20)
    
    modules = [
        ("vastdb", "VAST Database client"),
        ("ibis", "Ibis data manipulation"),
        ("pyarrow", "PyArrow data processing"),
        ("pandas", "Pandas data analysis"),
        ("boto3", "AWS S3 client"),
        ("fastapi", "FastAPI web framework"),
        ("pydantic", "Data validation"),
        ("opentelemetry", "Telemetry"),
    ]
    
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name} - {description}")
        except ImportError:
            print(f"❌ {module_name} - {description} (not installed)")
        except Exception as e:
            print(f"⚠️  {module_name} - {description} (error: {e})")


def main():
    """Main function."""
    
    print("🚀 TAMS Database Version Check")
    print("=" * 35)
    print()
    
    # Test imports
    test_imports()
    
    # Get version information
    get_vast_version()
    
    # Get configuration
    get_config_info()
    
    print("\n✅ Version check completed!")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 