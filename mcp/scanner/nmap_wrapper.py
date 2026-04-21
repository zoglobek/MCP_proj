# File: mcp/scanner/nmap_wrapper.py

import subprocess
import logging
import re
from typing import List, Dict, Optional
from pathlib import Path
import time

from .validator import TargetValidator

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
        self.validator = TargetValidator()
        self._verify_nmap_installed()

    def _verify_nmap_installed(self):
        """Verify Nmap is available"""
        try:
            result = subprocess.run(
                [self.nmap_path, "-V"],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError("Nmap check returned non-zero")
            logger.info("Nmap verified and available")
        except FileNotFoundError as e:
            logger.error(f"Nmap not found or not executable: {e}")
            raise RuntimeError(f"Nmap not found: {e}") from e
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Nmap verification failed: {e}")
            raise RuntimeError(f"Nmap verification failed: {e}") from e

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
        # Validate target
        is_valid, reason = self.validator.validate_target(target_range)
        if not is_valid:
            raise ValueError(f"Invalid target: {reason}")

        logger.info(f"Starting host discovery scan on {target_range}")

        # Build command
        cmd = [
            self.nmap_path,
            "-sn",  # Ping scan
            "-oX", "-",  # XML output to stdout
            target_range
        ]

        return self._run_command(cmd, f"host_discovery_{target_range}")

    def run_port_scan(self, target: str, ports: str = "-") -> str:
        """
        Run service version detection scan (-sV flag)

        Args:
            target: Single IP address
            ports: Port specification (default: all ports)

        Returns:
            XML output as string
        """
        # Validate target
        is_valid, reason = self.validator.validate_target(target)
        if not is_valid:
            raise ValueError(f"Invalid target: {reason}")

        logger.info(f"Starting port scan on {target}:{ports}")

        # Build command
        cmd = [
            self.nmap_path,
            "-sV",  # Service version detection
            "-p", ports,  # Port specification
            "-oX", "-",  # XML output to stdout
            target
        ]

        return self._run_command(cmd, f"port_scan_{target}")

    def run_os_detection(self, target: str) -> str:
        """
        Run OS fingerprinting scan (-O flag)

        Args:
            target: Single IP address

        Returns:
            XML output as string
        """
        # Validate target
        is_valid, reason = self.validator.validate_target(target)
        if not is_valid:
            raise ValueError(f"Invalid target: {reason}")

        logger.info(f"Starting OS detection scan on {target}")

        # Build command
        cmd = [
            self.nmap_path,
            "-O",  # OS detection
            "-oX", "-",  # XML output to stdout
            target
        ]

        return self._run_command(cmd, f"os_detection_{target}")

    def run_full_scan(self, target_range: str) -> str:
        """
        Run comprehensive scan with all features

        Args:
            target_range: IP address or CIDR range

        Returns:
            XML output as string
        """
        # Validate target
        is_valid, reason = self.validator.validate_target(target_range)
        if not is_valid:
            raise ValueError(f"Invalid target: {reason}")

        logger.info(f"Starting full scan on {target_range}")

        # Build command with comprehensive flags
        cmd = [
            self.nmap_path,
            "-sV",  # Service version detection
            "-O",   # OS detection
            "-A",   # Aggressive scan (OS, version, script scanning, traceroute)
            "--script=default,vuln",  # Default and vulnerability scripts
            "-oX", "-",  # XML output to stdout
            target_range
        ]

        return self._run_command(cmd, f"full_scan_{target_range}")

    def _run_command(self, cmd: List[str], scan_id: str) -> str:
        """
        Execute nmap command with proper error handling

        Args:
            cmd: Command list
            scan_id: Identifier for logging

        Returns:
            XML output as string
        """
        start_time = time.time()

        try:
            logger.debug(f"Running command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.TIMEOUT_SECONDS,
                text=True
            )

            duration = time.time() - start_time
            logger.info(f"Scan {scan_id} completed in {duration:.2f}s")

            if result.returncode != 0:
                logger.warning(f"Scan {scan_id} returned non-zero exit code: {result.returncode}")
                if result.stderr:
                    logger.warning(f"Scan stderr: {result.stderr}")

            # Return stdout (XML output)
            return result.stdout

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error(f"Scan {scan_id} timed out after {duration:.2f}s")
            raise

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Scan {scan_id} failed after {duration:.2f}s: {e}")
            raise