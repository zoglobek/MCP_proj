# Virtual Environment Setup Guide

This project uses Python virtual environments to manage dependencies in isolation from the system Python installation.

## Setup Instructions

The virtual environment has been created at `/home/gal/devops/MCP_proj/venv` with all dependencies installed.

### Activate the Virtual Environment

**On Linux/Mac:**
```bash
source venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**On Windows (CMD):**
```cmd
venv\Scripts\activate.bat
```

Once activated, your prompt should show `(venv)` at the beginning.

## Running Tests

With the venv activated:

```bash
# Run all Phase 2 tests
python -m pytest tests/test_scanner_phase2.py -v

# Run specific test class
python -m pytest tests/test_scanner_phase2.py::TestNmapWrapper -v

# Run with coverage
python -m pytest tests/test_scanner_phase2.py --cov=mcp --cov-report=html
```

## Running the Application

With the venv activated:

```bash
# Start the MCP application
cd mcp
python main.py

# Or use the startup script from within mcp/
bash run.sh
```

## Installing Additional Packages

With the venv activated:

```bash
# Install new package
pip install package_name

# Update requirements files if needed
pip freeze > requirements.txt
```

## Deactivate Virtual Environment

```bash
deactivate
```

## Troubleshooting

### "command not found: python" after activating venv
- Make sure you're in the project root directory
- Verify venv was created: `ls venv/`
- Try: `source venv/bin/activate` again

### "ModuleNotFoundError" when running tests
- Ensure venv is activated (check for `(venv)` in prompt)
- Reinstall dependencies: `pip install -r requirements.txt`

### Permission errors on Linux/Mac
- Make scripts executable: `chmod +x venv/bin/activate`

## Notes

- The `venv/` directory is gitignored and should not be committed
- Each developer should have their own venv
- The venv contains all dependencies for development and testing
- All Phase 1 and Phase 2 functionality works with this setup
