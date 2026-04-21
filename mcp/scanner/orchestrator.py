# File: mcp/scanner/orchestrator.py

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from .nmap_wrapper import NmapWrapper
from .parser import NmapXMLParser
from db.models import get_session, Server, Port, Service, ScanJob, ScanType
from db.merge import merge_scan_results

logger = logging.getLogger(__name__)

class ScanOrchestrator:
    """
    Orchestrates the complete scanning workflow:

    1. Host discovery
    2. Port scanning
    3. OS detection
    4. Result parsing
    5. Database storage with merge logic
    """

    def __init__(self):
        self.nmap_wrapper = NmapWrapper()
        self.parser = NmapXMLParser()

    def run_full_scan(self, target_range: str, scan_id: Optional[str] = None) -> Dict:
        """
        Run complete scanning workflow

        Args:
            target_range: IP range to scan (CIDR notation)
            scan_id: Optional scan identifier

        Returns:
            Scan results summary
        """
        if scan_id is None:
            scan_id = f"scan_{int(time.time())}"

        logger.info(f"Starting full scan {scan_id} on {target_range}")

        # Create scan job record
        scan_job = self._create_scan_job(scan_id, target_range, ScanType.FULL_SCAN)

        try:
            # Step 1: Host discovery
            logger.info("Phase 1: Host discovery")
            host_xml = self.nmap_wrapper.run_host_discovery(target_range)

            # Step 2: Full scan on discovered hosts
            logger.info("Phase 2: Full port and OS scanning")
            full_xml = self.nmap_wrapper.run_full_scan(target_range)

            # Step 3: Parse results
            logger.info("Phase 3: Parsing results")
            parsed_results = self.parser.parse(full_xml)

            # Step 4: Store in database
            logger.info("Phase 4: Storing results")
            stored_count = self._store_results(parsed_results, scan_job)

            # Update scan job as completed
            self._complete_scan_job(scan_job, stored_count)

            logger.info(f"Scan {scan_id} completed successfully. Stored {stored_count} hosts.")

            return {
                "scan_id": scan_id,
                "status": "completed",
                "hosts_discovered": len(parsed_results.get("hosts", [])),
                "hosts_stored": stored_count,
                "errors": parsed_results.get("errors", [])
            }

        except Exception as e:
            logger.error(f"Scan {scan_id} failed: {e}")
            self._fail_scan_job(scan_job, str(e))
            raise

    def run_quick_scan(self, target_range: str, scan_id: Optional[str] = None) -> Dict:
        """
        Run quick host discovery scan only

        Args:
            target_range: IP range to scan
            scan_id: Optional scan identifier

        Returns:
            Scan results summary
        """
        if scan_id is None:
            scan_id = f"quick_scan_{int(time.time())}"

        logger.info(f"Starting quick scan {scan_id} on {target_range}")

        # Create scan job record
        scan_job = self._create_scan_job(scan_id, target_range, ScanType.HOST_DISCOVERY)

        try:
            # Host discovery only
            host_xml = self.nmap_wrapper.run_host_discovery(target_range)
            parsed_results = self.parser.parse(host_xml)

            # Store basic host info (no ports/services)
            stored_count = self._store_basic_hosts(parsed_results, scan_job)

            # Complete scan job
            self._complete_scan_job(scan_job, stored_count)

            logger.info(f"Quick scan {scan_id} completed. Found {stored_count} hosts.")

            return {
                "scan_id": scan_id,
                "status": "completed",
                "hosts_discovered": len(parsed_results.get("hosts", [])),
                "hosts_stored": stored_count,
                "errors": parsed_results.get("errors", [])
            }

        except Exception as e:
            logger.error(f"Quick scan {scan_id} failed: {e}")
            self._fail_scan_job(scan_job, str(e))
            raise

    def _create_scan_job(self, scan_id: str, target_range: str, scan_type: ScanType) -> ScanJob:
        """Create scan job record in database"""
        session = get_session()
        try:
            scan_job = ScanJob(
                scan_id=scan_id,
                target_range=target_range,
                scan_type=scan_type,
                status=ScanJob.Status.RUNNING,
                start_time=datetime.utcnow()
            )
            session.add(scan_job)
            session.commit()
            logger.debug(f"Created scan job {scan_id}")
            return scan_job
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def _complete_scan_job(self, scan_job: ScanJob, hosts_count: int):
        """Mark scan job as completed"""
        session = get_session()
        try:
            scan_job.status = ScanJob.Status.COMPLETED
            scan_job.end_time = datetime.utcnow()
            scan_job.results_summary = f"Discovered {hosts_count} hosts"
            session.commit()
            logger.debug(f"Completed scan job {scan_job.scan_id}")
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def _fail_scan_job(self, scan_job: ScanJob, error: str):
        """Mark scan job as failed"""
        session = get_session()
        try:
            scan_job.status = ScanJob.Status.FAILED
            scan_job.end_time = datetime.utcnow()
            scan_job.results_summary = f"Failed: {error}"
            session.commit()
            logger.error(f"Failed scan job {scan_job.scan_id}: {error}")
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def _store_results(self, parsed_results: Dict, scan_job: ScanJob) -> int:
        """
        Store parsed scan results in database with merge logic

        Returns:
            Number of hosts stored/updated
        """
        session = get_session()
        try:
            hosts_stored = 0

            for host_data in parsed_results.get("hosts", []):
                try:
                    # Use merge logic to handle existing records
                    merge_scan_results(session, host_data, scan_job)
                    hosts_stored += 1
                except Exception as e:
                    logger.warning(f"Failed to store host {host_data.get('ip')}: {e}")
                    continue

            session.commit()
            logger.info(f"Stored {hosts_stored} hosts in database")
            return hosts_stored

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store scan results: {e}")
            raise
        finally:
            session.close()

    def _store_basic_hosts(self, parsed_results: Dict, scan_job: ScanJob) -> int:
        """
        Store basic host information (IP and hostname only)

        Returns:
            Number of hosts stored
        """
        session = get_session()
        try:
            hosts_stored = 0

            for host_data in parsed_results.get("hosts", []):
                ip = host_data.get("ip")
                if not ip:
                    continue

                # Check if server already exists
                existing = session.query(Server).filter_by(ip=ip).first()
                if existing:
                    # Update last seen
                    existing.last_seen = datetime.utcnow()
                    existing.last_scan = datetime.utcnow()
                else:
                    # Create new server record
                    server = Server(
                        ip=ip,
                        hostname=host_data.get("hostname"),
                        is_online=True,
                        last_seen=datetime.utcnow(),
                        last_scan=datetime.utcnow()
                    )
                    session.add(server)

                hosts_stored += 1

            session.commit()
            logger.info(f"Stored {hosts_stored} basic host records")
            return hosts_stored

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store basic hosts: {e}")
            raise
        finally:
            session.close()