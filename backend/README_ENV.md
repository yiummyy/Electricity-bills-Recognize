# Project Environment Setup & Isolation Guide

This guide explains how to set up a project-level isolated Python environment for the **Electricity Bills Recognition** backend. This ensures that the project runs with the exact dependency versions it needs, without interfering with your system-wide Python installation or other projects.

## 1. Prerequisites

- **Python 3.8+** must be installed on your system.
  - Windows: [Download Python](https://www.python.org/downloads/windows/)
  - macOS/Linux: Usually pre-installed, or use `brew install python3`.

## 2. One-Click Setup

We provide automated scripts to create a virtual environment (`venv`) and install all required dependencies.

### Windows
Double-click `setup_env.bat` or run it from Command Prompt / PowerShell:

```cmd
cd backend
setup_env.bat
```

### macOS / Linux
Run the shell script:

```bash
cd backend
chmod +x setup_env.sh
./setup_env.sh
```

**What these scripts do:**
1. Check for Python installation.
2. Create a local `venv` directory (if it doesn't exist).
3. Activate the virtual environment.
4. Upgrade `pip` to the latest version.
5. Install all dependencies listed in `requirements.txt`.

## 3. Verifying the Environment

To ensure that your environment is correctly isolated and all dependencies are loaded from the local `venv`, run the verification script:

### Windows
```cmd
backend\venv\Scripts\python verify_env.py
```

### macOS / Linux
```bash
./backend/venv/bin/python verify_env.py
```

**Success Output:**
You should see a report ending with:
```
========================================================
VERIFICATION SUCCESSFUL: Environment is isolated and ready.
========================================================
```

If it fails, the script will tell you which dependency is missing or if you are running from the wrong interpreter.

## 4. Running the Server

Always ensure you are using the python interpreter from the `venv` directory.

### Windows
```cmd
backend\venv\Scripts\python run_server.py
```

### macOS / Linux
```bash
./backend/venv/bin/python run_server.py
```

## 5. CI/CD Integration Example

For automated pipelines (e.g., GitHub Actions, Jenkins), you can use the same logic.

**Example (GitHub Actions):**

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install Dependencies
        run: |
          cd backend
          python -m venv venv
          source venv/bin/activate
          pip install --upgrade pip
          pip install -r requirements.txt
          
      - name: Verify Environment
        run: |
          cd backend
          source venv/bin/activate
          python verify_env.py
          
      - name: Run Tests
        run: |
          cd backend
          source venv/bin/activate
          pytest
```
