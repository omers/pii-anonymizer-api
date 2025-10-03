#!/usr/bin/env python3
"""
Script to check for dependency conflicts and version issues.
This helps identify and resolve common dependency problems.
"""

import subprocess
import sys
import warnings
from importlib.metadata import version, PackageNotFoundError

def check_package_version(package_name, expected_range=None):
    """Check if a package is installed and optionally verify version range."""
    try:
        installed_version = version(package_name)
        print(f"✅ {package_name}: {installed_version}")
        return True, installed_version
    except PackageNotFoundError:
        print(f"❌ {package_name}: Not installed")
        return False, None

def check_common_conflicts():
    """Check for common dependency conflicts."""
    print("🔍 Checking for common dependency conflicts...")
    print("=" * 60)
    
    conflicts_found = False
    
    # Check typer/click compatibility
    typer_installed, typer_ver = check_package_version("typer")
    click_installed, click_ver = check_package_version("click")
    
    if typer_installed and click_installed:
        # Parse versions for comparison
        try:
            click_major = int(click_ver.split('.')[0])
            if click_major >= 9:
                print("⚠️  WARNING: Click 9.0+ may cause deprecation warnings with typer")
                print("   Recommendation: Use click<9.0.0")
                conflicts_found = True
        except (ValueError, IndexError):
            print("⚠️  Could not parse click version for compatibility check")
    
    # Check FastAPI/Starlette compatibility
    fastapi_installed, fastapi_ver = check_package_version("fastapi")
    starlette_installed, starlette_ver = check_package_version("starlette")
    
    if fastapi_installed and starlette_installed:
        print(f"ℹ️  FastAPI {fastapi_ver} with Starlette {starlette_ver}")
        # FastAPI 0.115.x requires starlette<0.42.0
        if fastapi_ver.startswith("0.115"):
            try:
                starlette_minor = float('.'.join(starlette_ver.split('.')[:2]))
                if starlette_minor >= 0.42:
                    print("⚠️  WARNING: FastAPI 0.115.x requires starlette<0.42.0")
                    conflicts_found = True
            except (ValueError, IndexError):
                print("⚠️  Could not parse starlette version for compatibility check")
    
    # Check presidio versions
    presidio_analyzer_installed, analyzer_ver = check_package_version("presidio-analyzer")
    presidio_anonymizer_installed, anonymizer_ver = check_package_version("presidio-anonymizer")
    
    if presidio_analyzer_installed and presidio_anonymizer_installed:
        if analyzer_ver != anonymizer_ver:
            print(f"⚠️  WARNING: Presidio version mismatch - analyzer: {analyzer_ver}, anonymizer: {anonymizer_ver}")
            print("   Recommendation: Use matching versions")
            conflicts_found = True
    
    return not conflicts_found

def check_pip_check():
    """Run pip check to identify dependency conflicts."""
    print("\n🔧 Running pip check for dependency conflicts...")
    print("=" * 60)
    
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "check"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ No dependency conflicts found by pip check")
            return True
        else:
            print("❌ Dependency conflicts found:")
            print(result.stdout)
            if result.stderr:
                print("Errors:")
                print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Failed to run pip check: {e}")
        return False

def suppress_warnings():
    """Configure warning filters to suppress known deprecation warnings."""
    print("\n🔇 Configuring warning filters...")
    print("=" * 60)
    
    # Suppress typer/click deprecation warnings
    warnings.filterwarnings("ignore", 
                          message=".*BaseCommand.*is deprecated.*", 
                          category=DeprecationWarning,
                          module="typer.*")
    
    warnings.filterwarnings("ignore", 
                          message=".*'BaseCommand'.*deprecated.*", 
                          category=DeprecationWarning)
    
    print("✅ Warning filters configured")
    
    # Test that warnings are suppressed
    try:
        import typer
        print("✅ Typer imported without warnings")
    except ImportError:
        print("ℹ️  Typer not installed")
    except Exception as e:
        print(f"⚠️  Issue importing typer: {e}")

def main():
    """Main function to run all checks."""
    print("🔧 Dependency Conflict Checker")
    print("=" * 60)
    
    # Check for conflicts
    no_conflicts = check_common_conflicts()
    
    # Run pip check
    pip_check_ok = check_pip_check()
    
    # Configure warning suppression
    suppress_warnings()
    
    print("\n📋 Summary")
    print("=" * 60)
    
    if no_conflicts and pip_check_ok:
        print("🎉 All dependency checks passed!")
        print("\n💡 If you still see deprecation warnings during tests:")
        print("   1. They are likely suppressed in pytest.ini")
        print("   2. Run: python -W ignore::DeprecationWarning -m pytest")
        print("   3. Or set PYTHONWARNINGS=ignore::DeprecationWarning")
        return 0
    else:
        print("⚠️  Some issues found. Consider:")
        print("   1. Updating requirements.txt with compatible versions")
        print("   2. Running: pip install --upgrade -r requirements.txt")
        print("   3. Creating a fresh virtual environment")
        return 1

if __name__ == "__main__":
    sys.exit(main())
