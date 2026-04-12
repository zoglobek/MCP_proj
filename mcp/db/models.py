"""
SQLAlchemy ORM models for MCP database

Tables:
- users (authentication & authorization)
- servers (discovered hosts)
- ports (open ports on servers)
- services (services running on ports)
- probes (service metadata from probing)
- scan_jobs (scan execution history)
- user_notes (user-editable annotations)
- change_log (audit trail)
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, DateTime, Boolean, 
    Text, JSON, ForeignKey, Enum, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import enum

Base = declarative_base()


class User(Base):
    """User accounts for RBAC and authentication"""
    
    __tablename__ = 'users'
    __table_args__ = (
        UniqueConstraint('username', name='uq_username'),
        Index('idx_username_active', 'username', 'is_active'),
    )
    
    class Role(enum.Enum):
        ADMIN = "admin"
        SCANNER = "scanner"  # Can trigger scans
        VIEWER = "viewer"    # Read-only access
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash
    email = Column(String(255), nullable=True)
    role = Column(Enum(Role), default=Role.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    ssh_sessions = relationship("SSHSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role.value})>"


class Server(Base):
    """Discovered servers/hosts on the network"""
    
    __tablename__ = 'servers'
    __table_args__ = (
        UniqueConstraint('ip', name='uq_server_ip'),
        Index('idx_server_ip', 'ip'),
        Index('idx_server_hostname', 'hostname'),
        Index('idx_server_last_scan', 'last_scan'),
    )
    
    id = Column(Integer, primary_key=True)
    ip = Column(String(15), nullable=False, unique=True)  # IPv4 only
    hostname = Column(String(255), nullable=True)
    os = Column(String(255), nullable=True)  # e.g., "Linux", "Windows Server 2019"
    os_version = Column(String(255), nullable=True)
    os_accuracy = Column(Float, nullable=True)  # 0.0-1.0 confidence
    mac_address = Column(String(17), nullable=True)
    is_online = Column(Boolean, default=True, nullable=False)
    last_seen = Column(DateTime, nullable=True)
    last_scan = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    ports = relationship("Port", back_populates="server", cascade="all, delete-orphan")
    notes = relationship("UserNote", back_populates="server", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Server(id={self.id}, ip={self.ip}, hostname={self.hostname})>"


class Port(Base):
    """Open ports on discovered servers"""
    
    __tablename__ = 'ports'
    __table_args__ = (
        UniqueConstraint('server_id', 'port_number', 'protocol', name='uq_server_port_protocol'),
        Index('idx_port_server', 'server_id'),
        Index('idx_port_number', 'port_number'),
        Index('idx_port_state', 'state'),
    )
    
    class State(enum.Enum):
        OPEN = "open"
        CLOSED = "closed"
        FILTERED = "filtered"
        UNFILTERED = "unfiltered"
    
    class Protocol(enum.Enum):
        TCP = "tcp"
        UDP = "udp"
    
    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey('servers.id'), nullable=False)
    port_number = Column(Integer, nullable=False)
    protocol = Column(Enum(Protocol), default=Protocol.TCP, nullable=False)
    state = Column(Enum(State), default=State.OPEN, nullable=False)
    last_scan = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    server = relationship("Server", back_populates="ports")
    services = relationship("Service", back_populates="port", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint('port_number >= 1 AND port_number <= 65535', name='ck_port_range'),
    ) + __table_args__
    
    def __repr__(self):
        return f"<Port(id={self.id}, port={self.port_number}/{self.protocol.value}, state={self.state.value})>"


class Service(Base):
    """Services detected on ports"""
    
    __tablename__ = 'services'
    __table_args__ = (
        Index('idx_service_port', 'port_id'),
        Index('idx_service_name', 'service_name'),
        Index('idx_service_version', 'version'),
    )
    
    id = Column(Integer, primary_key=True)
    port_id = Column(Integer, ForeignKey('ports.id'), nullable=False)
    service_name = Column(String(255), nullable=False)  # e.g., "ssh", "http", "mysql"
    version = Column(String(255), nullable=True)  # e.g., "OpenSSH 7.4"
    banner = Column(Text, nullable=True)  # Raw service banner
    confidence = Column(Float, nullable=True)  # 0.0-1.0 confidence from nmap
    cpe = Column(String(255), nullable=True)  # CPE string for CVE matching
    last_scan = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    port = relationship("Port", back_populates="services")
    probes = relationship("Probe", back_populates="service", cascade="all, delete-orphan")
    cves = relationship("CVE", back_populates="service", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Service(id={self.id}, service={self.service_name}, version={self.version})>"


class Probe(Base):
    """Service probing results (deep metadata collection)"""
    
    __tablename__ = 'probes'
    __table_args__ = (
        Index('idx_probe_service', 'service_id'),
        Index('idx_probe_type', 'probe_type'),
    )
    
    class ProbeType(enum.Enum):
        HTTP_HEADERS = "http_headers"
        SSH_BANNER = "ssh_banner"
        SQL_VERSION = "sql_version"
        SMB_INFO = "smb_info"
        RDP_INFO = "rdp_info"
        DNS_QUERY = "dns_query"
        FTP_BANNER = "ftp_banner"
        CUSTOM = "custom"
    
    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    probe_type = Column(Enum(ProbeType), nullable=False)
    data = Column(JSON, nullable=False)  # Structured metadata as JSON
    success = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    service = relationship("Service", back_populates="probes")
    
    def __repr__(self):
        return f"<Probe(id={self.id}, type={self.probe_type.value}, success={self.success})>"


class CVE(Base):
    """CVE vulnerabilities associated with services"""
    
    __tablename__ = 'cves'
    __table_args__ = (
        Index('idx_cve_id', 'cve_id'),
        Index('idx_cve_service', 'service_id'),
        Index('idx_cve_severity', 'severity'),
    )
    
    class Severity(enum.Enum):
        CRITICAL = "CRITICAL"
        HIGH = "HIGH"
        MEDIUM = "MEDIUM"
        LOW = "LOW"
        INFO = "INFO"
    
    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    cve_id = Column(String(20), nullable=False)  # e.g., "CVE-2021-1234"
    description = Column(Text, nullable=True)
    severity = Column(Enum(Severity), nullable=False)
    cvss_score = Column(Float, nullable=True)  # 0.0-10.0
    published_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    references = Column(JSON, nullable=True)  # URLs to CVE details
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    service = relationship("Service", back_populates="cves")
    
    def __repr__(self):
        return f"<CVE(id={self.id}, cve_id={self.cve_id}, severity={self.severity.value})>"


class ScanJob(Base):
    """Scan execution history and metadata"""
    
    __tablename__ = 'scan_jobs'
    __table_args__ = (
        Index('idx_scan_status', 'status'),
        Index('idx_scan_start_time', 'start_time'),
    )
    
    class Status(enum.Enum):
        PENDING = "pending"
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"
    
    class ScanType(enum.Enum):
        FULL = "full"           # All IP ranges
        ZONE = "zone"           # Single /24 zone
        INCREMENTAL = "incremental"  # Activity-based
        MANUAL = "manual"       # User-triggered
    
    id = Column(Integer, primary_key=True)
    scan_type = Column(Enum(ScanType), default=ScanType.FULL, nullable=False)
    target_range = Column(String(18), nullable=False)  # CIDR notation
    status = Column(Enum(Status), default=Status.PENDING, nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    hosts_discovered = Column(Integer, default=0, nullable=False)
    services_discovered = Column(Integer, default=0, nullable=False)
    ports_found = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<ScanJob(id={self.id}, type={self.scan_type.value}, status={self.status.value})>"


class UserNote(Base):
    """User-editable notes and labels on servers"""
    
    __tablename__ = 'user_notes'
    __table_args__ = (
        Index('idx_note_server', 'server_id'),
        Index('idx_note_user', 'user_id'),
    )
    
    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey('servers.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Null = system note
    note_text = Column(Text, nullable=False)
    label = Column(String(50), nullable=True)  # e.g., "production", "test", "firewall"
    is_pinned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    server = relationship("Server", back_populates="notes")
    
    def __repr__(self):
        return f"<UserNote(id={self.id}, server_id={self.server_id}, label={self.label})>"


class AuditLog(Base):
    """Audit trail for RBAC and database changes"""
    
    __tablename__ = 'audit_logs'
    __table_args__ = (
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_action', 'action'),
        Index('idx_audit_timestamp', 'timestamp'),
    )
    
    class Action(enum.Enum):
        LOGIN = "login"
        LOGOUT = "logout"
        SCAN_START = "scan_start"
        SCAN_COMPLETE = "scan_complete"
        SERVER_CREATED = "server_created"
        SERVER_UPDATED = "server_updated"
        SERVER_DELETED = "server_deleted"
        DATABASE_EXPORTED = "database_exported"
        DATABASE_IMPORTED = "database_imported"
        DATABASE_WIPED = "database_wiped"
        NOTE_ADDED = "note_added"
        NOTE_UPDATED = "note_updated"
        USER_CREATED = "user_created"
        USER_UPDATED = "user_updated"
        SSH_SESSION_OPENED = "ssh_session_opened"
        SSH_SESSION_CLOSED = "ssh_session_closed"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(Enum(Action), nullable=False)
    resource_type = Column(String(50), nullable=True)  # e.g., "server", "scan", "user"
    resource_id = Column(Integer, nullable=True)
    ip_address = Column(String(15), nullable=True)  # Client IP
    details = Column(JSON, nullable=True)  # Additional context
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action.value})>"


class DatabaseBackup(Base):
    """Metadata for database backups"""
    
    __tablename__ = 'database_backups'
    __table_args__ = (
        Index('idx_backup_timestamp', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)  # .tbkp file
    size_bytes = Column(Integer, nullable=False)
    servers_count = Column(Integer, nullable=False)
    services_count = Column(Integer, nullable=False)
    backup_reason = Column(String(255), nullable=True)  # e.g., "before_wipe", "scheduled"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<DatabaseBackup(id={self.id}, filename={self.filename})>"


class SSHSession(Base):
    """Browser SSH session tracking"""
    
    __tablename__ = 'ssh_sessions'
    __table_args__ = (
        Index('idx_ssh_user', 'user_id'),
        Index('idx_ssh_server', 'server_id'),
    )
    
    class SessionStatus(enum.Enum):
        ACTIVE = "active"
        IDLE = "idle"
        CLOSED = "closed"
        TERMINATED = "terminated"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    server_id = Column(Integer, ForeignKey('servers.id'), nullable=False)
    session_token = Column(String(255), nullable=False, unique=True)
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False)
    remote_username = Column(String(255), nullable=False)
    client_ip = Column(String(15), nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="ssh_sessions")
    
    def __repr__(self):
        return f"<SSHSession(id={self.id}, user={self.user_id}, server={self.server_id})>"


class Alert(Base):
    """Alert configuration and alert history"""
    
    __tablename__ = 'alerts'
    __table_args__ = (
        Index('idx_alert_type', 'alert_type'),
        Index('idx_alert_severity', 'severity'),
    )
    
    class AlertType(enum.Enum):
        SERVER_OFFLINE = "server_offline"
        NEW_SERVICE = "new_service"
        CVE_DISCOVERED = "cve_discovered"
        PORT_OPENED = "port_opened"
        PORT_CLOSED = "port_closed"
        SERVICE_VERSION_CHANGED = "service_version_changed"
    
    class Severity(enum.Enum):
        CRITICAL = "CRITICAL"
        HIGH = "HIGH"
        MEDIUM = "MEDIUM"
        LOW = "LOW"
        INFO = "INFO"
    
    id = Column(Integer, primary_key=True)
    alert_type = Column(Enum(AlertType), nullable=False)
    server_id = Column(Integer, ForeignKey('servers.id'), nullable=True)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=True)
    severity = Column(Enum(Severity), default=Severity.MEDIUM, nullable=False)
    message = Column(Text, nullable=False)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Alert(id={self.id}, type={self.alert_type.value}, severity={self.severity.value})>"


# Database connection and session management
def init_db(db_path: str):
    """Initialize database and create all tables"""
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Create a new database session"""
    Session = sessionmaker(bind=engine)
    return Session()
