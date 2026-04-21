# File: mcp/scanner/validator.py

import ipaddress
from typing import List, Tuple
from config import get_config
import logging

logger = logging.getLogger(__name__)

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
        whitelist = []
        for cidr_str in self.config.scanner.enabled_ip_ranges:
            try:
                network = ipaddress.IPv4Network(cidr_str, strict=False)
                whitelist.append(network)
                logger.debug(f"Added whitelist range: {network}")
            except ValueError as e:
                logger.error(f"Invalid CIDR in config: {cidr_str} - {e}")
                raise ValueError(f"Invalid whitelist CIDR: {cidr_str}")
        return whitelist

    def validate_target(self, target: str) -> Tuple[bool, str]:
        """
        Validate a single target (IP or CIDR)

        Args:
            target: IP address or CIDR notation

        Returns:
            (is_valid, reason)
        """
        try:
            # Parse the target
            if '/' in target:
                # CIDR notation
                network = ipaddress.IPv4Network(target, strict=False)
                return self.validate_range(str(network))
            else:
                # Single IP
                ip = ipaddress.IPv4Address(target)
                return self._check_ip_in_whitelist(ip)

        except ValueError as e:
            return False, f"Invalid target format: {e}"

    def validate_range(self, cidr: str) -> Tuple[bool, str]:
        """
        Validate CIDR range

        Args:
            cidr: CIDR notation string

        Returns:
            (is_valid, reason)
        """
        try:
            target_network = ipaddress.IPv4Network(cidr, strict=False)

            # Check if the target range is within any whitelisted range
            for whitelist_network in self.whitelist:
                if target_network.subnet_of(whitelist_network):
                    return True, "Range is within whitelisted network"

            return False, f"Range {cidr} is not in whitelist. Allowed ranges: {[str(n) for n in self.whitelist]}"

        except ValueError as e:
            return False, f"Invalid CIDR format: {e}"

    def _check_ip_in_whitelist(self, ip: ipaddress.IPv4Address) -> Tuple[bool, str]:
        """Check if IP is in any whitelisted range"""
        for network in self.whitelist:
            if ip in network:
                return True, "IP is within whitelisted range"

        return False, f"IP {ip} is not in whitelist. Allowed ranges: {[str(n) for n in self.whitelist]}"

    def is_private_range(self, cidr: str) -> bool:
        """
        Check if CIDR is a private (RFC1918) range

        Args:
            cidr: CIDR notation

        Returns:
            True if private range
        """
        try:
            network = ipaddress.IPv4Network(cidr, strict=False)

            # RFC1918 private ranges
            private_ranges = [
                ipaddress.IPv4Network("10.0.0.0/8"),
                ipaddress.IPv4Network("172.16.0.0/12"),
                ipaddress.IPv4Network("192.168.0.0/16")
            ]

            return any(network.subnet_of(private) for private in private_ranges)

        except ValueError:
            return False