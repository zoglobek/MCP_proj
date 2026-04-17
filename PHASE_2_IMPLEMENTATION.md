# PHASE 2: Network Scanning Engine Implementation Guide

**Status:** In Development 🚀  
**Target Duration:** 1-2 weeks  
**Goal:** Implement robust host and service discovery using Nmap  
**Prerequisites:** Phase 1 complete ✅

---

## Overview

Phase 2 builds the core scanning capability of MCP. It creates safe, local-only scanning wrappers around Nmap with proper validation, error handling, and result storage.

### Key Deliverables
- ✅ Nmap CLI wrapper with IP range validation
- ✅ XML parsing and result normalization
- ✅ Scan orchestration workflow
- ✅ Atomic database writes with merge logic
- ✅ Comprehensive test coverage (>90%)
- ✅ CI/CD ready implementation

---

## Architecture

```
┌─────────────────────────────────────────┐
│   Scan Request (CLI/API)                │
└────────────────┬────────────────────────┘
                 │
    ┌────────────▼────────────┐
    │ Target Validation       │
    │ - Check IP ranges       │
    │ - Validate CIDR blocks  │
    │ - Whitelist enforcement │
    └────────────┬────────────┘
                 │
    ┌────────────▼────────────────────┐
    │ Scan Execution                  │
    │ 1. Host Discovery (-sn)         │
    │ 2. Port Scan (-sV)              │
    │ 3. OS Detection (-O)            │
    └────────────┬────────────────────┘
                 │
    ┌────────────▼────────────┐
    │ XML Parsing             │
    │ - Extract results       │
    │ - Normalize data        │
    │ - Handle errors         │
    └────────────┬────────────┘
                 │
    ┌────────────▼────────────────┐
    │ Database Merge             │
    │ - Deduplicate             │
    │ - Preserve user data      │
    │ - Atomic writes           │
    └────────────┬────────────────┘
                 │
    ┌────────────▼────────────┐
    │ Store Results           │
    │ - Servers               │
    │ - Ports                 │
    │ - Services              │
    │ - Metadata              │
    └────────────────────────┘
```

---

## Implementation Steps

### Step 1: Nmap Wrapper Development (Days 1-2)

**Objective:** Create safe Nmap subprocess wrapper with validation

#### 1.1 Setup `scanner/nmap_wrapper.py`

Create the main wrapper that handles all Nmap subprocess calls:

```python
# File: mcp/scanner/nmap_wrapper.py

import subprocess
import logging
import re
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class NmapWrapper:
    """
    Safe Nmap wrapper with input validation and error handling.
    
    Features:
    - Validates all targets against whitelist
    - Runs Nmap with safe default flags
    - Handles timeouts gracefully
    - Captures XML output for parsing
    - Logs all scan activities
    """
    
    # Default safe Nmap flags
    DEFAULT_FLAGS = ["-sV", "--script=default", "-O", "-A"]
    TIMEOUT_SECONDS = 300  # 5 minute timeout per scan
    
    def __init__(self, nmap_path: str = "nmap"):
        """
        Args:
            nmap_path: Path to nmap binary (default: system PATH)
        """
        self.nmap_path = nmap_path
        self._verify_nmap_installed()
    
    def _verify_nmap_installed(self):
        """Verify Nmap is available"""
        try:
            result = subprocess.run(
                [self.nmap_path, "-V"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("Nmap check returned non-zero")
            logger.info("Nmap verified and available")
        except Exception as e:
            logger.error(f"Nmap not found or not executable: {e}")
            raise
    
    def run_host_discovery(self, target_range: str) -> str:
        """
        Run host discovery scan (-sn flag for ping sweep)
        
        Args:
            target_range: IP address or CIDR range (e.g., "192.168.1.0/24")
        
        Returns:
            XML output as string
        
        Raises:
            ValueError: If target is invalid
            subprocess.TimeoutExpired: If scan takes too long
        """
        pass  # Implementation in task
    
    def run_port_scan(self, target: str, ports: str = "-") -> str:
        """
        Run service version detection scan (-sV flag)
        
        Args:
            target: Single IP address
            ports: Port specification (default: all ports)
        
        Returns:
            XML output as string
        """
        pass  # Implementation in task
    
    def run_os_detection(self, target: str) -> str:
        """
        Run OS fingerprinting scan (-O flag)
        
        Args:
            target: Single IP address
        
        Returns:
            XML output as string
        """
        pass  # Implementation in task
```

#### 1.2 Create `scanner/validator.py` for Target Validation

```python
# File: mcp/scanner/validator.py

import ipaddress
from typing import List, Tuple
from config import get_config

class TargetValidator:
    """
    Validates scan targets against configured whitelist.
    
    Prevents scanning of:
    - External ranges (non-RFC1918)
    - Unwhitelisted IPs
    - Invalid CIDR blocks
    """
    
    def __init__(self):
        self.config = get_config()
        self.whitelist = self._parse_whitelist()
    
    def _parse_whitelist(self) -> List[ipaddress.IPv4Network]:
        """Parse whitelist from config"""
        pass  # Implementation in task
    
    def validate_target(self, target: str) -> Tuple[bool, str]:
        """
        Validate a single target (IP or CIDR)
        
        Args:
            target: IP address or CIDR notation
        
        Returns:
            (is_valid, reason)
        """
        pass  # Implementation in task
    
    def validate_range(self, cidr: str) -> Tuple[bool, str]:
        """Validate CIDR range"""
        pass  # Implementation in task
```

#### 1.3 Create `scanner/parser.py` for XML Parsing

```python
# File: mcp/scanner/parser.py

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class NmapXMLParser:
    """
    Parse Nmap XML output into normalized JSON structure.
    
    Handles:
    - Host discovery results
    - Port information
    - Service versions
    - OS fingerprinting
    - Errors and incomplete data
    """
    
    def parse(self, xml_string: str) -> Dict:
        """
        Parse Nmap XML output
        
        Returns:
            {
                "hosts": [
                    {
                        "ip": "192.168.1.1",
                        "hostname": "router.local",
                        "os": "Linux",
                        "os_version": "3.10",
                        "ports": [
                            {
                                "number": 22,
                                "protocol": "tcp",
                                "state": "open",
                                "service": "ssh",
                                "version": "OpenSSH_7.4"
                            }
                        ]
                    }
                ],
                "errors": []
            }
        """
        pass  # Implementation in task
    
    def _parse_host(self, host_elem) -> Dict:
        """Parse individual host element"""
        pass  # Implementation in task
    
    def _parse_ports(self, host_elem) -> List[Dict]:
        """Parse ports from host element"""
        pass  # Implementation in task
    
    def _parse_os(self, host_elem) -> Tuple[Optional[str], Optional[str]]:
        """Parse OS information"""
        pass  # Implementation in task
```

#### 1.4 Test Requirements

Create `tests/test_scanner_phase2.py`:

```python
# File: tests/test_scanner_phase2.py

import pytest
from scanner.validator import TargetValidator
from scanner.parser import NmapXMLParser
from scanner.nmap_wrapper import NmapWrapper

class TestTargetValidator:
    """Test IP range validation"""
    
    def test_valid_private_range(self):
        """Valid private ranges should be allowed"""
        validator = TargetValidator()
        valid, msg = validator.validate_target("192.168.1.0/24")
        assert valid, f"Should allow valid range: {msg}"
    
    def test_invalid_external_range(self):
        """External ranges should be rejected"""
        validator = TargetValidator()
        valid, msg = validator.validate_target("8.8.8.0/24")
        assert not valid, "Should reject external range"
    
    def test_invalid_cidr_format(self):
        """Invalid CIDR should be rejected"""
        validator = TargetValidator()
        valid, msg = validator.validate_target("192.168.1.999")
        assert not valid, "Should reject invalid IP"

class TestNmapXMLParser:
    """Test Nmap XML parsing"""
    
    def test_parse_valid_xml(self):
        """Parser handles valid Nmap XML"""
        xml_sample = """<?xml version="1.0"?>
        <nmaprun>
            <host>
                <address addr="192.168.1.1" addrtype="ipv4"/>
                <hostnames><hostname name="router.local"/></hostnames>
                <ports>
                    <port protocol="tcp" portid="22">
                        <state state="open"/>
                        <service name="ssh" version="OpenSSH_7.4"/>
                    </port>
                </ports>
            </host>
        </nmaprun>"""
        
        parser = NmapXMLParser()
        result = parser.parse(xml_sample)
        
        assert len(result["hosts"]) == 1
        assert result["hosts"][0]["ip"] == "192.168.1.1"
        assert len(result["hosts"][0]["ports"]) == 1
    
    def test_parse_incomplete_data(self):
        """Parser handles incomplete results"""
        # Test with missing OS, service version, etc.
        pass
    
    def test_parse_error_handling(self):
        """Parser handles malformed XML gracefully"""
        pass
```

---

### Step 2: Scan Orchestration & Storage (Days 3-4)

**Objective:** Chain scans and store results atomically

#### 2.1 Create `scanner/orchestrator.py`

```python
# File: mcp/scanner/orchestrator.py

from typing import Dict, List, Optional
from datetime import datetime
from scanner.nmap_wrapper import NmapWrapper
from scanner.validator import TargetValidator
from scanner.parser import NmapXMLParser
from db.models import Server, Port, Service, ScanJob, get_session
import logging

logger = logging.getLogger(__name__)

class ScanOrchestrator:
    """
    Orchestrates the complete scan workflow:
    1. Validate targets
    2. Run host discovery
    3. Run port scans on discovered hosts
    4. Run OS detection
    5. Parse and merge results
    """
    
    def __init__(self):
        self.nmap = NmapWrapper()
        self.validator = TargetValidator()
        self.parser = NmapXMLParser()
    
    def scan_network(self, target_range: str) -> Dict:
        """
        Execute complete network scan workflow
        
        Args:
            target_range: CIDR block to scan
        
        Returns:
            {
                "scan_id": 1,
                "status": "completed",
                "hosts_found": 42,
                "services_detected": 156,
                "errors": []
            }
        """
        session = get_session()
        scan_job = None
        
        try:
            # Validate
            valid, msg = self.validator.validate_range(target_range)
            if not valid:
                raise ValueError(f"Invalid target range: {msg}")
            
            # Create scan job
            scan_job = ScanJob(
                status="in_progress",
                results_summary={}
            )
            session.add(scan_job)
            session.commit()
            
            # Step 1: Host discovery
            logger.info(f"Starting host discovery for {target_range}")
            discovery_xml = self.nmap.run_host_discovery(target_range)
            discovery_results = self.parser.parse(discovery_xml)
            
            hosts = [h["ip"] for h in discovery_results["hosts"]]
            logger.info(f"Discovered {len(hosts)} hosts")
            
            # Step 2-3: Port scan + OS detection per host
            all_results = {"hosts": [], "errors": []}
            for host_ip in hosts:
                try:
                    port_xml = self.nmap.run_port_scan(host_ip)
                    port_results = self.parser.parse(port_xml)
                    all_results["hosts"].extend(port_results["hosts"])
                except Exception as e:
                    logger.error(f"Port scan failed for {host_ip}: {e}")
                    all_results["errors"].append(f"Port scan failed for {host_ip}")
            
            # Step 4: Store results
            self._merge_results(session, scan_job, all_results)
            
            scan_job.status = "completed"
            session.commit()
            
            return {
                "scan_id": scan_job.id,
                "status": "completed",
                "hosts_found": len(all_results["hosts"]),
                "services_detected": sum(
                    len(h.get("ports", [])) for h in all_results["hosts"]
                )
            }
        
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            if scan_job:
                scan_job.status = "failed"
                session.commit()
            raise
    
    def _merge_results(self, session, scan_job: ScanJob, results: Dict):
        """
        Atomically merge scan results into database.
        
        - Deduplicate by IP
        - Preserve user notes
        - Update only changed fields
        """
        pass  # Implementation in task
```

#### 2.2 Create `scanner/storage.py` for Atomic Writes

```python
# File: mcp/scanner/storage.py

from db.models import Server, Port, Service, get_session
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class ScanResultStorage:
    """
    Handles atomic storage of scan results with conflict resolution.
    """
    
    @staticmethod
    def save_results(scan_results: Dict) -> int:
        """
        Save parsed scan results to database atomically.
        
        Returns:
            Number of new servers created
        """
        pass  # Implementation in task
    
    @staticmethod
    def merge_host_data(existing_server: Server, new_data: Dict):
        """
        Merge new host data with existing server record.
        
        - Updates OS, hostname, last_scan
        - Preserves user notes and labels
        - Deduplicates ports/services
        """
        pass  # Implementation in task
    
    @staticmethod
    def upsert_services(port_record: Port, service_list: List[Dict]):
        """
        Insert or update service records for a port.
        """
        pass  # Implementation in task
```

#### 2.3 Test Requirements

Create `tests/test_orchestrator_phase2.py`:

```python
# File: tests/test_orchestrator_phase2.py

import pytest
from scanner.orchestrator import ScanOrchestrator
from scanner.storage import ScanResultStorage
from db.models import Server, Port, get_session

class TestOrchestrator:
    """Test scan orchestration workflow"""
    
    def test_scan_valid_range(self, temp_db):
        """Orchestrator validates and scans valid ranges"""
        pass
    
    def test_scan_rejects_invalid_range(self):
        """Orchestrator rejects targets outside whitelist"""
        pass

class TestScanResultStorage:
    """Test atomic storage and merge logic"""
    
    def test_save_new_servers(self, temp_db):
        """New servers are correctly saved"""
        pass
    
    def test_merge_duplicate_servers(self, temp_db):
        """Duplicate IPs are merged, not duplicated"""
        pass
    
    def test_preserve_user_notes_on_merge(self, temp_db):
        """User notes survive rescan merge"""
        pass
    
    def test_atomic_transaction_rollback(self, temp_db):
        """Failed writes roll back cleanly"""
        pass
```

---

### Step 3: Integration & Testing (Days 5)

**Objective:** Integrate with Phase 1, verify end-to-end

#### 3.1 CLI Integration

Create `mcp/cli.py`:

```python
# File: mcp/cli.py

import click
from scanner.orchestrator import ScanOrchestrator
from scanner.validator import TargetValidator
import logging

logger = logging.getLogger(__name__)

@click.group()
def cli():
    """MCP Command Line Interface"""
    pass

@cli.command()
@click.argument('target_range')
@click.option('--timeout', default=300, help='Scan timeout in seconds')
def scan(target_range, timeout):
    """Scan a network range"""
    orchestrator = ScanOrchestrator()
    
    try:
        result = orchestrator.scan_network(target_range)
        click.echo(f"✅ Scan completed:")
        click.echo(f"  Hosts found: {result['hosts_found']}")
        click.echo(f"  Services detected: {result['services_detected']}")
    except Exception as e:
        click.echo(f"❌ Scan failed: {e}", err=True)
        raise

@cli.command()
def validate():
    """Validate configuration"""
    validator = TargetValidator()
    click.echo("✅ Configuration is valid")

if __name__ == "__main__":
    cli()
```

#### 3.2 Test Coverage Requirements

- Unit tests: >85%
- Integration tests: All workflows
- Edge cases: Timeouts, malformed XML, network errors
- Performance: Scan 256-host network in <5 minutes

---

## Quality Gates (Definition of Done)

### Code Quality
- ✅ All functions have docstrings
- ✅ Type hints on all functions
- ✅ PEP 8 compliant
- ✅ No hardcoded paths/credentials
- ✅ Logging at INFO, DEBUG, ERROR levels

### Testing
- ✅ >85% code coverage
- ✅ All unit tests pass
- ✅ Integration tests pass
- ✅ Performance benchmarks met

### Documentation
- ✅ Code comments for complex logic
- ✅ README for scanner module
- ✅ Example config for scan ranges
- ✅ API documentation updated

### Deployment
- ✅ Works in Docker container
- ✅ No external network access (verified with iptables mock)
- ✅ Database doesn't get corrupted on error
- ✅ Logs are readable and actionable

---

## File Checklist

```
mcp/scanner/
├── __init__.py                              ✅ NEW
├── nmap_wrapper.py                          ✅ NEW (Nmap subprocess)
├── validator.py                             ✅ NEW (IP range validation)
├── parser.py                                ✅ NEW (XML parsing)
├── orchestrator.py                          ✅ NEW (Workflow orchestration)
└── storage.py                               ✅ NEW (Atomic database writes)

mcp/cli.py                                   ✅ NEW (CLI interface)

tests/
├── fixtures/
│   ├── nmap_sample_output.xml               ✅ NEW (Sample Nmap XML)
│   └── mock_nmap_data.json                  ✅ NEW (Test data)
├── test_scanner_phase2.py                   ✅ NEW (Unit tests)
└── test_orchestrator_phase2.py              ✅ NEW (Integration tests)

docs/
└── PHASE_2_API.md                           ✅ NEW (Scan API docs)
```

---

## Success Metrics

| Metric | Target | Pass |
|--------|--------|------|
| Unit test pass rate | 100% | - |
| Code coverage | >85% | - |
| Scan speed (256 hosts) | <5 min | - |
| IPv4 validation accuracy | 100% | - |
| Database integrity on error | 100% | - |
| Duplicate prevention | 100% | - |

---

## Next Steps (Phase 3)

Once Phase 2 is complete:
1. ✅ Start Phase 3 (Service Probing)
2. Service-specific probes (HTTP, SSH, SQL, SMB, RDP)
3. Integration with orchestrator

---
