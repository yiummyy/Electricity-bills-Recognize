import sys
import os
import site

def verify_environment():
    print("="*60)
    print("ENVIRONMENT VERIFICATION REPORT")
    print("="*60)
    
    # 1. Check if running in a virtual environment
    is_venv = (sys.prefix != sys.base_prefix)
    print(f"Virtual Environment Active: {'YES' if is_venv else 'NO'}")
    print(f"  - Python Executable: {sys.executable}")
    print(f"  - Prefix: {sys.prefix}")
    print(f"  - Base Prefix: {sys.base_prefix}")
    
    if not is_venv:
        print("\n[FAIL] Not running inside a virtual environment!")
        print("Please activate the environment using:")
        if os.name == 'nt':
            print("  backend\\venv\\Scripts\\activate")
        else:
            print("  source backend/venv/bin/activate")
        return False

    # 2. Check site-packages location
    site_packages = site.getsitepackages()
    print(f"\nSite Packages Locations:")
    for path in site_packages:
        print(f"  - {path}")
        
    # verify that site-packages is within the venv directory
    venv_path = os.path.abspath(sys.prefix)
    valid_paths = [p for p in site_packages if venv_path in os.path.abspath(p)]
    
    if not valid_paths:
        print("\n[WARNING] Site-packages seem to be outside the virtual environment root!")
    else:
        print("\n[PASS] Site-packages are correctly located within the virtual environment.")

    # 3. Check critical dependencies
    try:
        import fastapi
        import uvicorn
        import paddleocr
        print("\n[PASS] Critical dependencies (fastapi, uvicorn, paddleocr) importable.")
        print(f"  - FastAPI version: {fastapi.__version__}")
        print(f"  - PaddleOCR location: {os.path.dirname(paddleocr.__file__)}")
    except ImportError as e:
        print(f"\n[FAIL] Missing dependency: {e}")
        return False

    print("\n" + "="*60)
    print("VERIFICATION SUCCESSFUL: Environment is isolated and ready.")
    print("="*60)
    return True

if __name__ == "__main__":
    success = verify_environment()
    sys.exit(0 if success else 1)
