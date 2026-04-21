# File: mcp/scanner/parser.py

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
import logging
import re

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
                        "os_accuracy": 0.85,
                        "ports": [
                            {
                                "number": 22,
                                "protocol": "tcp",
                                "state": "open",
                                "service": "ssh",
                                "version": "OpenSSH_7.4",
                                "banner": "SSH-2.0-OpenSSH_7.4",
                                "confidence": 0.9
                            }
                        ]
                    }
                ],
                "errors": [],
                "scan_info": {
                    "start_time": "2026-04-21T10:00:00",
                    "end_time": "2026-04-21T10:05:00",
                    "command": "nmap -sV -O 192.168.1.0/24"
                }
            }
        """
        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML: {e}")
            return {"hosts": [], "errors": [f"XML parse error: {e}"], "scan_info": {}}

        result = {
            "hosts": [],
            "errors": [],
            "scan_info": self._parse_scan_info(root)
        }

        # Parse each host
        for host_elem in root.findall(".//host"):
            try:
                host_data = self._parse_host(host_elem)
                if host_data:
                    result["hosts"].append(host_data)
            except Exception as e:
                logger.warning(f"Failed to parse host: {e}")
                result["errors"].append(f"Host parse error: {e}")

        return result

    def _parse_scan_info(self, root: ET.Element) -> Dict:
        """Parse scan metadata"""
        info = {}

        # Find nmaprun element
        nmaprun = root.find(".")
        if nmaprun is not None:
            info["start_time"] = nmaprun.get("startstr")
            info["command"] = nmaprun.get("args")

        # Find finished element
        finished = root.find(".//finished")
        if finished is not None:
            info["end_time"] = finished.get("timestr")

        return info

    def _parse_host(self, host_elem: ET.Element) -> Optional[Dict]:
        """Parse individual host element"""
        # Check if host is up
        status = host_elem.find("status")
        if status is None or status.get("state") != "up":
            return None

        host_data = {}

        # Parse IP address
        address = host_elem.find("address[@addrtype='ipv4']")
        if address is not None:
            host_data["ip"] = address.get("addr")
        else:
            return None  # No IP, skip host

        # Parse hostname
        hostnames = host_elem.find("hostnames")
        if hostnames is not None:
            hostname_elem = hostnames.find("hostname")
            if hostname_elem is not None:
                host_data["hostname"] = hostname_elem.get("name")

        # Parse OS information
        os_info = self._parse_os(host_elem)
        host_data.update(os_info)

        # Parse ports
        host_data["ports"] = self._parse_ports(host_elem)

        return host_data

    def _parse_ports(self, host_elem: ET.Element) -> List[Dict]:
        """Parse ports from host element"""
        ports = []

        ports_elem = host_elem.find("ports")
        if ports_elem is None:
            return ports

        for port_elem in ports_elem.findall("port"):
            try:
                port_data = self._parse_port(port_elem)
                if port_data:
                    ports.append(port_data)
            except Exception as e:
                logger.warning(f"Failed to parse port: {e}")

        return ports

    def _parse_port(self, port_elem: ET.Element) -> Optional[Dict]:
        """Parse individual port element"""
        port_data = {
            "number": int(port_elem.get("portid")),
            "protocol": port_elem.get("protocol"),
            "state": None,
            "service": None,
            "version": None,
            "banner": None,
            "confidence": None
        }

        # Parse state
        state_elem = port_elem.find("state")
        if state_elem is not None:
            port_data["state"] = state_elem.get("state")

        # Parse service
        service_elem = port_elem.find("service")
        if service_elem is not None:
            port_data["service"] = service_elem.get("name")
            port_data["version"] = service_elem.get("version")
            port_data["banner"] = service_elem.get("banner")

            # Parse confidence
            confidence = service_elem.get("conf")
            if confidence:
                try:
                    port_data["confidence"] = float(confidence) / 10.0  # Nmap uses 0-10 scale
                except ValueError:
                    pass

        return port_data

    def _parse_os(self, host_elem: ET.Element) -> Dict:
        """Parse OS information"""
        os_data = {
            "os": None,
            "os_version": None,
            "os_accuracy": None
        }

        os_elem = host_elem.find("os")
        if os_elem is None:
            return os_data

        # Find the OS match with highest accuracy
        best_match = None
        best_accuracy = 0

        for osmatch in os_elem.findall("osmatch"):
            try:
                accuracy = int(osmatch.get("accuracy", 0))
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_match = osmatch
            except ValueError:
                continue

        if best_match is not None:
            os_data["os"] = best_match.get("name")
            os_data["os_accuracy"] = best_accuracy / 100.0  # Convert to 0.0-1.0

            # Try to extract version from OS name
            os_name = best_match.get("name", "")
            version_match = re.search(r'(\d+\.[\d\.]+)', os_name)
            if version_match:
                os_data["os_version"] = version_match.group(1)

        return os_data