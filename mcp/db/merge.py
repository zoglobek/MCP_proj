"""
Database merge logic for handling rescans and data conflicts

During rescans, new data must be merged with existing data while preserving:
- User annotations and notes
- Manual edits and labels
- Scan history
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
import logging

from .models import Server, Port, Service, Probe, ScanJob, UserNote

logger = logging.getLogger("db.merge")


class RescanMergeStrategy:
    """Handles conflict-safe merging of rescan results with existing data"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def merge_scan_results(
        self,
        scan_job_id: int,
        scan_results: Dict[str, Any]
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Merge new scan results with existing database entries.
        
        Args:
            scan_job_id: ID of the ScanJob
            scan_results: New scan results from nmap
            
        Returns:
            Tuple of (servers_affected_count, merge_report)
        """
        logger.info(f"Starting merge for scan job {scan_job_id}")
        
        merge_report = {
            "servers_created": 0,
            "servers_updated": 0,
            "services_added": 0,
            "services_removed": 0,
            "conflicts_resolved": 0,
            "user_notes_preserved": 0,
        }
        
        try:
            # Process each host in scan results
            for host_data in scan_results.get("hosts", []):
                host_ip = host_data.get("ip")
                
                if not host_ip:
                    logger.warning("Host data missing IP address, skipping")
                    continue
                
                # Merge or create server
                server = self._merge_server(host_data)
                if server.id is None:  # Newly created
                    merge_report["servers_created"] += 1
                else:
                    merge_report["servers_updated"] += 1
                
                # Merge ports and services
                ports_merged, services_result = self._merge_ports_and_services(
                    server, host_data
                )
                merge_report["services_added"] += services_result.get("added", 0)
                merge_report["services_removed"] += services_result.get("removed", 0)
                
                # Update server's last_scan timestamp
                server.last_scan = datetime.utcnow()
                server.is_online = True
            
            self.session.commit()
            logger.info(f"Merge completed with report: {merge_report}")
            return len(merge_report), merge_report
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error during merge: {e}")
            raise
    
    def _merge_server(self, host_data: Dict[str, Any]) -> Server:
        """
        Merge or create a server entry.
        
        Preserves existing user notes and edits if server already exists.
        """
        host_ip = host_data.get("ip")
        hostname = host_data.get("hostname")
        os_info = host_data.get("os", {})
        
        # Look for existing server
        server = self.session.query(Server).filter_by(ip=host_ip).first()
        
        if server:
            # Existing server - update with new scan results
            server.is_online = True
            server.last_seen = datetime.utcnow()
            
            # Update OS info if new scan has data
            if os_info.get("name"):
                server.os = os_info.get("name")
                server.os_version = os_info.get("version")
                server.os_accuracy = os_info.get("accuracy")
            
            # Update hostname if discovered
            if hostname and not server.hostname:
                server.hostname = hostname
            
            logger.debug(f"Updated existing server {host_ip}")
            
        else:
            # New server - create entry
            server = Server(
                ip=host_ip,
                hostname=hostname,
                os=os_info.get("name"),
                os_version=os_info.get("version"),
                os_accuracy=os_info.get("accuracy"),
                is_online=True,
                last_seen=datetime.utcnow(),
                last_scan=datetime.utcnow(),
            )
            self.session.add(server)
            self.session.flush()  # Get the ID
            
            logger.info(f"Created new server {host_ip}")
        
        return server
    
    def _merge_ports_and_services(
        self,
        server: Server,
        host_data: Dict[str, Any]
    ) -> Tuple[int, Dict[str, int]]:
        """
        Merge ports and services for a server.
        
        Handles:
        - New ports/services (added)
        - Removed ports/services (marked as closed)
        - Service version changes
        """
        services_result = {"added": 0, "removed": 0}
        ports_merged = 0
        
        # Parse new ports from scan results
        new_ports_set = set()
        for port_data in host_data.get("ports", []):
            port_num = port_data.get("number")
            protocol = port_data.get("protocol", "tcp")
            new_ports_set.add((port_num, protocol))
            
            # Merge this port
            self._merge_port(server, port_data)
            ports_merged += 1
        
        # Check for ports that are no longer open (old ports not in new scan)
        existing_ports = self.session.query(Port).filter_by(server_id=server.id).all()
        for port in existing_ports:
            port_key = (port.port_number, port.protocol.value)
            
            if port_key not in new_ports_set:
                # Port was open before, not in current scan = likely closed
                if port.state.value != "closed":
                    port.state = Port.State.CLOSED
                    port.last_scan = datetime.utcnow()
                    services_result["removed"] += len(port.services)
                    logger.info(f"Marked port {port.port_number} as closed")
        
        return ports_merged, services_result
    
    def _merge_port(self, server: Server, port_data: Dict[str, Any]):
        """Merge a single port and its services"""
        port_num = port_data.get("number")
        protocol = port_data.get("protocol", "tcp")
        state = port_data.get("state", "open")
        
        # Look for existing port
        port = self.session.query(Port).filter_by(
            server_id=server.id,
            port_number=port_num,
            protocol=Port.Protocol(protocol)
        ).first()
        
        if not port:
            # New port
            port = Port(
                server_id=server.id,
                port_number=port_num,
                protocol=Port.Protocol(protocol),
                state=Port.State(state),
                last_scan=datetime.utcnow(),
            )
            self.session.add(port)
            self.session.flush()
            logger.debug(f"Created new port {port_num}/{protocol}")
        
        else:
            # Existing port - update state and timestamp
            port.state = Port.State(state)
            port.last_scan = datetime.utcnow()
        
        # Merge services for this port
        for service_data in port_data.get("services", []):
            self._merge_service(port, service_data)
    
    def _merge_service(self, port: Port, service_data: Dict[str, Any]):
        """Merge a single service entry"""
        service_name = service_data.get("name")
        if not service_name:
            return
        
        # Look for existing service
        service = self.session.query(Service).filter_by(
            port_id=port.id,
            service_name=service_name
        ).first()
        
        if service:
            # Update existing service
            if service_data.get("version"):
                service.version = service_data.get("version")
            if service_data.get("banner"):
                service.banner = service_data.get("banner")
            if service_data.get("confidence"):
                service.confidence = service_data.get("confidence")
            service.last_scan = datetime.utcnow()
            
        else:
            # New service
            service = Service(
                port_id=port.id,
                service_name=service_name,
                version=service_data.get("version"),
                banner=service_data.get("banner"),
                confidence=service_data.get("confidence"),
                cpe=service_data.get("cpe"),
                last_scan=datetime.utcnow(),
            )
            self.session.add(service)
            logger.debug(f"Added service {service_name} on port {port.port_number}")
    
    def mark_server_offline(self, server_id: int):
        """Mark a server as offline (not seen in recent scans)"""
        server = self.session.query(Server).filter_by(id=server_id).first()
        if server:
            server.is_online = False
            self.session.commit()
            logger.info(f"Marked server {server_id} as offline")
    
    def preserve_user_edits(self, server_id: int) -> Dict[str, Any]:
        """
        Retrieve user edits before a merge operation for preservation.
        
        Returns:
            Dictionary of user notes and labels to preserve
        """
        notes = self.session.query(UserNote).filter_by(server_id=server_id).all()
        return {
            "notes": [note.note_text for note in notes],
            "labels": [note.label for note in notes if note.label],
        }


def handle_rescan_conflict(
    existing_data: Dict[str, Any],
    new_data: Dict[str, Any],
    conflict_type: str
) -> Dict[str, Any]:
    """
    Generic conflict resolver for rescan scenarios.
    
    Strategies:
    - For user edits: Keep existing
    - For service versions: Use newer version from scan
    - For timestamps: Use newer timestamp
    """
    
    if conflict_type == "service_version":
        # Use version from new scan if more recent
        if new_data.get("timestamp", datetime.min) > existing_data.get("timestamp", datetime.min):
            return new_data
        return existing_data
    
    elif conflict_type == "user_note":
        # Preserve user notes (never overwrite)
        return existing_data
    
    elif conflict_type == "os_info":
        # Use newer OS info if confidence is higher
        if new_data.get("confidence", 0) > existing_data.get("confidence", 0):
            return new_data
        return existing_data
    
    else:
        # Default: use new data
        return new_data
