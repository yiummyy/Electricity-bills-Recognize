import sys
import os
import pytest

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_path)

if __name__ == "__main__":
    sys.exit(pytest.main(['-v', os.path.join(backend_path, 'tests/test_multi_month.py')]))
