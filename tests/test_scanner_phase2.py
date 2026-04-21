# File: tests/test_scanner_phase2.py

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from pathlib import Path

# Add MCP root to path for testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp"))

from scanner.validator import TargetValidator
from scanner.parser import NmapXMLParser
from scanner.nmap_wrapper import NmapWrapper


class TestTargetValidator:
    """Test IP range validation"""

    @patch('scanner.validator.get_config')
    def test_valid_private_range(self, mock_get_config):
        """Valid private ranges should be allowed"""
        # Mock config with whitelist
        mock_config = Mock()
        mock_config.scanner.enabled_ip_ranges = ["192.168.0.0/16", "10.0.0.0/8"]
        mock_get_config.return_value = mock_config

        validator = TargetValidator()
        valid, msg = validator.validate_target("192.168.1.0/24")
        assert valid, f"Should allow valid range: {msg}"

    @patch('scanner.validator.get_config')
    def test_invalid_external_range(self, mock_get_config):
        """External ranges should be rejected"""
        mock_config = Mock()
        mock_config.scanner.enabled_ip_ranges = ["192.168.0.0/16"]
        mock_get_config.return_value = mock_config

        validator = TargetValidator()
        valid, msg = validator.validate_target("8.8.8.0/24")
        assert not valid, "Should reject external range"
        assert "not in whitelist" in msg

    @patch('scanner.validator.get_config')
    def test_invalid_cidr_format(self, mock_get_config):
        """Invalid CIDR should be rejected"""
        mock_config = Mock()
        mock_config.scanner.enabled_ip_ranges = ["192.168.0.0/16"]
        mock_get_config.return_value = mock_config

        validator = TargetValidator()
        valid, msg = validator.validate_target("192.168.1.999/24")
        assert not valid, "Should reject invalid CIDR"
        assert "Invalid" in msg


class TestNmapXMLParser:
    """Test XML parsing functionality"""

    def test_parse_basic_host(self):
        """Test parsing basic host information"""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<nmaprun>
<host>
<status state="up"/>
<address addr="192.168.1.1" addrtype="ipv4"/>
<hostnames><hostname name="test.local"/></hostnames>
<ports>
<port protocol="tcp" portid="22">
<state state="open"/>
<service name="ssh" version="OpenSSH_7.4"/>
</port>
</ports>
</host>
</nmaprun>'''

        parser = NmapXMLParser()
        result = parser.parse(xml_content)

        assert len(result["hosts"]) == 1
        host = result["hosts"][0]
        assert host["ip"] == "192.168.1.1"
        assert host["hostname"] == "test.local"
        assert len(host["ports"]) == 1
        assert host["ports"][0]["service"] == "ssh"

    def test_parse_empty_xml(self):
        """Test parsing empty or invalid XML"""
        parser = NmapXMLParser()
        result = parser.parse("<invalid>")

        assert len(result["hosts"]) == 0
        assert len(result["errors"]) > 0

    def test_parse_os_info(self):
        """Test parsing OS fingerprinting results"""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<nmaprun>
<host>
<status state="up"/>
<address addr="192.168.1.1" addrtype="ipv4"/>
<os>
<osmatch name="Linux 3.10" accuracy="85"/>
</os>
</host>
</nmaprun>'''

        parser = NmapXMLParser()
        result = parser.parse(xml_content)

        assert len(result["hosts"]) == 1
        host = result["hosts"][0]
        assert host["os"] == "Linux 3.10"
        assert host["os_accuracy"] == 0.85


class TestNmapWrapper:
    """Test Nmap wrapper functionality"""

    @patch('scanner.nmap_wrapper.TargetValidator')
    @patch('subprocess.run')
    def test_verify_nmap_installed_success(self, mock_run, mock_validator_class):
        """Test successful nmap verification"""
        # Mock validator to avoid config issues
        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator

        mock_run.return_value = Mock(returncode=0, stdout="Nmap version")

        wrapper = NmapWrapper()
        # Should not raise exception
        assert wrapper.nmap_path == "nmap"

    @patch('scanner.nmap_wrapper.TargetValidator')
    @patch('subprocess.run')
    def test_verify_nmap_installed_failure(self, mock_run, mock_validator_class):
        """Test failed nmap verification"""
        # Mock validator to avoid config issues
        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator

        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(RuntimeError):
            NmapWrapper()

    @patch('subprocess.run')
    @patch('scanner.nmap_wrapper.TargetValidator')
    def test_run_host_discovery(self, mock_validator_class, mock_run):
        """Test host discovery execution"""
        # Mock validator
        mock_validator = Mock()
        mock_validator.validate_target.return_value = (True, "OK")
        mock_validator_class.return_value = mock_validator

        # Mock subprocess - need to handle both calls (verification + scan)
        mock_result_verify = Mock(returncode=0, stdout="Nmap version")
        mock_result_scan = Mock(returncode=0, stdout="<xml>test</xml>")
        mock_run.side_effect = [mock_result_verify, mock_result_scan]

        wrapper = NmapWrapper()
        result = wrapper.run_host_discovery("192.168.1.0/24")

        assert result == "<xml>test</xml>"
        # Should be called twice: once for verification, once for scan
        assert mock_run.call_count == 2

    @patch('scanner.nmap_wrapper.TargetValidator')
    def test_invalid_target_rejection(self, mock_validator_class):
        """Test that invalid targets are rejected"""
        mock_validator = Mock()
        mock_validator.validate_target.return_value = (False, "Not in whitelist")
        mock_validator_class.return_value = mock_validator

        wrapper = NmapWrapper()

        with pytest.raises(ValueError, match="Invalid target"):
            wrapper.run_host_discovery("8.8.8.0/24")