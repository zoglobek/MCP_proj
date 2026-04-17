# BETA Testing Agent - Quick Start Guide

**Status:** Ready to Run ✅  
**Purpose:** Validate Phase 1 implementation  
**Created:** April 17, 2026  

---

## Overview

The **BETA testing agent** is a comprehensive test suite that validates all Phase 1 functionality:

- ✅ Configuration management
- ✅ Database initialization  
- ✅ ORM models and relationships
- ✅ CRUD operations
- ✅ Merge logic for rescans
- ✅ User note preservation
- ✅ Flask API initialization
- ✅ Health checks

**Total Tests:** 10 categories | ~50+ assertions per run

---

## Installation

### Prerequisites

```bash
# Ensure you have Python 3.8+
python --version

# Install dependencies (if not already done)
pip install -r requirements.txt
```

### Setup

The beta agent creates a temporary test database to avoid corrupting your production database:

```bash
# No setup required - agent handles it automatically!
```

---

## Running Tests

### Method 1: Direct Python Execution

```bash
# From project root
python beta_test_agent.py
```

### Method 2: With Logging

```bash
# Run with detailed logging
python beta_test_agent.py --verbose

# Or set logging level
LOGLEVEL=DEBUG python beta_test_agent.py
```

### Method 3: As a Module (from other tests)

```python
from beta_test_agent import BetaTestAgent

agent = BetaTestAgent()
passed = agent.run_all_tests()

if passed:
    print("All tests passed!")
else:
    print("Some tests failed!")
```

---

## Test Output

### Console Output Example

```
[2026-04-17 14:32:01] [HEADER ] 
============================================================
  BETA TESTING AGENT - MCP Phase 1 Validation
============================================================
[2026-04-17 14:32:02] [HEADER ]  === PHASE 1: Configuration Tests ===
[2026-04-17 14:32:02] [SUCCESS] ✅ CONFIG: Default config loads
[2026-04-17 14:32:02] [SUCCESS] ✅ CONFIG: Config CIDR validation
[2026-04-17 14:32:03] [HEADER ]  === PHASE 1: Database Schema Tests ===
[2026-04-17 14:32:03] [SUCCESS] ✅ DATABASE: Database initialization
[2026-04-17 14:32:03] [SUCCESS] ✅ DATABASE: User model CRUD

...

[2026-04-17 14:32:15] [HEADER ]  === TEST REPORT ===
[2026-04-17 14:32:15] [INFO   ] 📊 OVERALL: 10/10 tests passed
[2026-04-17 14:32:15] [INFO   ]   CONFIG: 2/2 passed
[2026-04-17 14:32:15] [INFO   ]   DATABASE: 5/5 passed
[2026-04-17 14:32:15] [INFO   ]   STARTUP: 2/2 passed
[2026-04-17 14:32:15] [SUCCESS] ✅ Report saved to: tests/BETA_TEST_REPORT.md
```

### Report File

The agent generates `tests/BETA_TEST_REPORT.md` with:
- ✅ Overall summary
- ✅ Category breakdown
- ✅ Detailed test results
- ✅ Error messages (if any)

---

## Test Categories

### 1. Configuration Tests

**Tests:** 2  
**Validates:**
- Default config loads without errors
- CIDR validation functions correctly

```
✅ CONFIG: Default config loads
✅ CONFIG: Config CIDR validation
```

### 2. Database Schema Tests

**Tests:** 5  
**Validates:**
- Database initialization
- User CRUD operations
- Server model with relationships
- Duplicate detection and merge
- User note preservation during rescan

```
✅ DATABASE: Database initialization
✅ DATABASE: User model CRUD
✅ DATABASE: Server model relationships
✅ DATABASE: Duplicate merge logic
✅ DATABASE: User notes preservation
✅ DATABASE: Scan job tracking
```

### 3. Application Startup Tests

**Tests:** 2  
**Validates:**
- Flask app initializes correctly
- API health check responds

```
✅ STARTUP: Flask app initialization
✅ STARTUP: API health check
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Phase 1 Test Suite

on: [push, pull_request]

jobs:
  phase1-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: python beta_test_agent.py
      - uses: actions/upload-artifact@v2
        if: always()
        with:
          name: test-report
          path: tests/BETA_TEST_REPORT.md
```

---

## Troubleshooting

### Test Fails: "Configuration not found"

**Problem:** Config file can't be loaded  
**Solution:**
```bash
# Ensure config.json exists in mcp/ directory
cp mcp/config.json.example mcp/config.json

# Or set custom path
export MCP_CONFIG_PATH=/path/to/config.json
python beta_test_agent.py
```

### Test Fails: "Database locked"

**Problem:** Database is in use by another process  
**Solution:**
```bash
# Kill any existing MCP processes
pkill -f "python.*main.py"

# Or wait a moment and retry
sleep 2
python beta_test_agent.py
```

### Test Fails: "Nmap not found"

**Problem:** Nmap isn't installed (needed for Phase 2, not Phase 1)  
**Solution:** This is expected for Phase 1. Nmap is required only in Phase 2.

### Test Fails: "Import error"

**Problem:** Module imports fail  
**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python path
export PYTHONPATH="/path/to/mcp:$PYTHONPATH"
python beta_test_agent.py
```

---

## What's Being Tested

### Configuration Layer (Phase 1.1)
```python
✅ Config loads from config.json
✅ IP ranges are valid CIDR notation
✅ All required config keys present
```

### Database Layer (Phase 1.2)
```python
✅ SQLite database initializes
✅ All tables created with correct schema
✅ Indexes created for performance
✅ Relationships defined correctly
✅ Constraints enforced
```

### Models & ORM (Phase 1.2)
```python
✅ Server model CRUD works
✅ Port model with relationships
✅ Service model references
✅ User model with authentication
✅ ScanJob tracking
✅ UserNote preservation
```

### Merge Logic (Phase 1.2)
```python
✅ Duplicate IPs detected
✅ Records updated instead of duplicated
✅ User notes preserved on merge
✅ Timestamps updated
✅ Fields properly reconciled
```

### API Layer (Phase 1)
```python
✅ Flask app initializes
✅ Config is accessible
✅ Database connection works
✅ Health check endpoint responds
```

---

## Expected Results

### ✅ Success Scenario

All tests pass in ~5-10 seconds:

```
OVERALL: 10/10 tests passed
CONFIG: 2/2 passed
DATABASE: 6/6 passed
STARTUP: 2/2 passed
```

**Next Steps:** Proceed to Phase 2 implementation

### ❌ Failure Scenarios

If tests fail, the report will show:
- Which category failed
- Which specific test failed
- Error message and stack trace
- Suggestions for fixes

See troubleshooting section above.

---

## Metrics

After running tests, check:

| Metric | Target | Status |
|--------|--------|--------|
| Pass Rate | 100% | - |
| Execution Time | <15 sec | - |
| Coverage | Phase 1 All | - |
| Database Integrity | No errors | - |

---

## Next: Phase 2 Testing

Once Phase 2 is implemented, extend the beta agent:

```python
# In beta_test_agent.py (after Phase 2 development)

def test_nmap_validation(self):
    """Test 2.1.1: Nmap wrapper validates targets"""
    pass

def test_scan_orchestration(self):
    """Test 2.2.1: Scan orchestration workflow"""
    pass

def test_xml_parsing(self):
    """Test 2.1.2: Nmap XML parsing"""
    pass
```

---

## Contributing

To add new Phase 1 tests:

1. Add test method to `BetaTestAgent` class
2. Call `self.run_test(category, name, test_func)`
3. Run agent to validate

Example:
```python
def test_new_feature(self):
    """Test description"""
    def test_logic():
        # Your test code here
        assert some_condition, "Error message"
    
    self.run_test("NEW_CATEGORY", "Feature name", test_logic)
```

---

## Contact & Support

For issues:
1. Check troubleshooting section
2. Review test report: `tests/BETA_TEST_REPORT.md`
3. Check logs: `logs/mcp_*.log`

---
