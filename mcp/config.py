"""
Configuration loader and validator for MCP
Handles user-configurable settings, IP ranges, secrets, and environment variables
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from ipaddress import IPv4Network, AddressValueError
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScannerConfig:
    """Scanner-specific configuration"""
    enabled_ip_ranges: List[str] = field(default_factory=list)
    scan_frequency_min_hours: int = 12  # 2 scans per day minimum
    max_parallel_zones: int = 8
    timeout_per_scan_seconds: int = 300
    nmap_arguments: str = "-sV -O --script vuln"
    safe_mode: bool = True  # Only scan whitelisted ranges


@dataclass
class DatabaseConfig:
    """Database-specific configuration"""
    db_path: str = "./data/mcp.db"
    backup_dir: str = "./data/backups"
    auto_backup_enabled: bool = True
    backup_retention_days: int = 3
    max_db_connections: int = 10


@dataclass
class APIConfig:
    """API server configuration"""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    workers: int = 4
    timeout_seconds: int = 30


@dataclass
class AuthConfig:
    """Authentication and authorization configuration"""
    pam_enabled: bool = True
    password_min_length: int = 12
    password_require_upper: bool = True
    password_require_lower: bool = True
    password_require_digits: bool = True
    password_require_special: bool = True
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15


@dataclass
class SSHGatewayConfig:
    """SSH gateway configuration for browser sessions"""
    enabled: bool = True
    idle_timeout_minutes: int = 30
    max_concurrent_sessions: int = 50
    auth_required: bool = True


@dataclass
class AlertingConfig:
    """Alert configuration"""
    enabled: bool = True
    alert_types: List[str] = field(
        default_factory=lambda: [
            "server_offline", "new_service", "cve_discovered", "port_opened"
        ]
    )
    email_enabled: bool = False
    webhook_enabled: bool = False
    slack_enabled: bool = False


class MCPConfig:
    """Main configuration class - loads and validates all settings"""

    def __init__(self, config_file: Optional[str] = None, env_prefix: str = "MCP_"):
        """
        Initialize configuration from file and environment variables.
        
        Args:
            config_file: Path to JSON config file. Defaults to ./config.json
            env_prefix: Prefix for environment variables
        """
        self.env_prefix = env_prefix
        self.config_file = config_file or self._get_config_file_path()
        
        # Initialize component configs
        self.scanner = ScannerConfig()
        self.database = DatabaseConfig()
        self.api = APIConfig()
        self.auth = AuthConfig()
        self.ssh_gateway = SSHGatewayConfig()
        self.alerting = AlertingConfig()
        
        # Load configuration from file and environment
        self._load_from_file()
        self._load_from_env()
        self._validate_all()
        
    def _get_config_file_path(self) -> str:
        """Get config file path from environment or use default"""
        env_config = os.getenv(f"{self.env_prefix}CONFIG_FILE", "./config.json")
        return env_config
    
    def _load_from_file(self):
        """Load configuration from JSON file"""
        if not os.path.exists(self.config_file):
            logger.warning(f"Config file not found at {self.config_file}. Using defaults.")
            return
        
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Load scanner config
            if 'scanner' in config_data:
                self._load_scanner_config(config_data['scanner'])
            
            # Load database config
            if 'database' in config_data:
                self._load_database_config(config_data['database'])
            
            # Load API config
            if 'api' in config_data:
                self._load_api_config(config_data['api'])
            
            # Load auth config
            if 'auth' in config_data:
                self._load_auth_config(config_data['auth'])
            
            # Load SSH gateway config
            if 'ssh_gateway' in config_data:
                self._load_ssh_gateway_config(config_data['ssh_gateway'])
            
            # Load alerting config
            if 'alerting' in config_data:
                self._load_alerting_config(config_data['alerting'])
            
            logger.info(f"Configuration loaded from {self.config_file}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            raise
    
    def _load_scanner_config(self, scanner_data: Dict[str, Any]):
        """Load scanner-specific configuration"""
        if 'enabled_ip_ranges' in scanner_data:
            self.scanner.enabled_ip_ranges = scanner_data['enabled_ip_ranges']
        if 'scan_frequency_min_hours' in scanner_data:
            self.scanner.scan_frequency_min_hours = scanner_data['scan_frequency_min_hours']
        if 'max_parallel_zones' in scanner_data:
            self.scanner.max_parallel_zones = scanner_data['max_parallel_zones']
        if 'timeout_per_scan_seconds' in scanner_data:
            self.scanner.timeout_per_scan_seconds = scanner_data['timeout_per_scan_seconds']
        if 'nmap_arguments' in scanner_data:
            self.scanner.nmap_arguments = scanner_data['nmap_arguments']
        if 'safe_mode' in scanner_data:
            self.scanner.safe_mode = scanner_data['safe_mode']
    
    def _load_database_config(self, db_data: Dict[str, Any]):
        """Load database-specific configuration"""
        if 'db_path' in db_data:
            self.database.db_path = db_data['db_path']
        if 'backup_dir' in db_data:
            self.database.backup_dir = db_data['backup_dir']
        if 'auto_backup_enabled' in db_data:
            self.database.auto_backup_enabled = db_data['auto_backup_enabled']
        if 'backup_retention_days' in db_data:
            self.database.backup_retention_days = db_data['backup_retention_days']
        if 'max_db_connections' in db_data:
            self.database.max_db_connections = db_data['max_db_connections']
    
    def _load_api_config(self, api_data: Dict[str, Any]):
        """Load API server configuration"""
        if 'host' in api_data:
            self.api.host = api_data['host']
        if 'port' in api_data:
            self.api.port = api_data['port']
        if 'debug' in api_data:
            self.api.debug = api_data['debug']
        if 'workers' in api_data:
            self.api.workers = api_data['workers']
        if 'timeout_seconds' in api_data:
            self.api.timeout_seconds = api_data['timeout_seconds']
    
    def _load_auth_config(self, auth_data: Dict[str, Any]):
        """Load authentication configuration"""
        if 'pam_enabled' in auth_data:
            self.auth.pam_enabled = auth_data['pam_enabled']
        if 'password_min_length' in auth_data:
            self.auth.password_min_length = auth_data['password_min_length']
        if 'password_require_upper' in auth_data:
            self.auth.password_require_upper = auth_data['password_require_upper']
        if 'password_require_lower' in auth_data:
            self.auth.password_require_lower = auth_data['password_require_lower']
        if 'password_require_digits' in auth_data:
            self.auth.password_require_digits = auth_data['password_require_digits']
        if 'password_require_special' in auth_data:
            self.auth.password_require_special = auth_data['password_require_special']
        if 'session_timeout_minutes' in auth_data:
            self.auth.session_timeout_minutes = auth_data['session_timeout_minutes']
        if 'max_login_attempts' in auth_data:
            self.auth.max_login_attempts = auth_data['max_login_attempts']
        if 'lockout_duration_minutes' in auth_data:
            self.auth.lockout_duration_minutes = auth_data['lockout_duration_minutes']
    
    def _load_ssh_gateway_config(self, ssh_data: Dict[str, Any]):
        """Load SSH gateway configuration"""
        if 'enabled' in ssh_data:
            self.ssh_gateway.enabled = ssh_data['enabled']
        if 'idle_timeout_minutes' in ssh_data:
            self.ssh_gateway.idle_timeout_minutes = ssh_data['idle_timeout_minutes']
        if 'max_concurrent_sessions' in ssh_data:
            self.ssh_gateway.max_concurrent_sessions = ssh_data['max_concurrent_sessions']
        if 'auth_required' in ssh_data:
            self.ssh_gateway.auth_required = ssh_data['auth_required']
    
    def _load_alerting_config(self, alerting_data: Dict[str, Any]):
        """Load alerting configuration"""
        if 'enabled' in alerting_data:
            self.alerting.enabled = alerting_data['enabled']
        if 'alert_types' in alerting_data:
            self.alerting.alert_types = alerting_data['alert_types']
        if 'email_enabled' in alerting_data:
            self.alerting.email_enabled = alerting_data['email_enabled']
        if 'webhook_enabled' in alerting_data:
            self.alerting.webhook_enabled = alerting_data['webhook_enabled']
        if 'slack_enabled' in alerting_data:
            self.alerting.slack_enabled = alerting_data['slack_enabled']
    
    def _load_from_env(self):
        """Load configuration from environment variables (overrides file config)"""
        # Scanner env vars
        if os.getenv(f"{self.env_prefix}ENABLED_IP_RANGES"):
            ranges = os.getenv(f"{self.env_prefix}ENABLED_IP_RANGES").split(';')
            self.scanner.enabled_ip_ranges = ranges
        
        if os.getenv(f"{self.env_prefix}SCAN_FREQUENCY_HOURS"):
            self.scanner.scan_frequency_min_hours = int(
                os.getenv(f"{self.env_prefix}SCAN_FREQUENCY_HOURS")
            )
        
        # Database env vars
        if os.getenv(f"{self.env_prefix}DB_PATH"):
            self.database.db_path = os.getenv(f"{self.env_prefix}DB_PATH")
        
        # API env vars
        if os.getenv(f"{self.env_prefix}API_HOST"):
            self.api.host = os.getenv(f"{self.env_prefix}API_HOST")
        
        if os.getenv(f"{self.env_prefix}API_PORT"):
            self.api.port = int(os.getenv(f"{self.env_prefix}API_PORT"))
        
        if os.getenv(f"{self.env_prefix}DEBUG"):
            self.api.debug = os.getenv(f"{self.env_prefix}DEBUG").lower() == "true"
    
    def _validate_all(self):
        """Validate all configuration settings"""
        self._validate_scanner_config()
        self._validate_database_config()
        self._validate_api_config()
        self._validate_auth_config()
    
    def _validate_scanner_config(self):
        """Validate scanner configuration"""
        if not self.scanner.enabled_ip_ranges:
            raise ValueError("At least one IP range must be configured in scanner.enabled_ip_ranges")
        
        for ip_range in self.scanner.enabled_ip_ranges:
            try:
                IPv4Network(ip_range, strict=False)
            except AddressValueError:
                raise ValueError(f"Invalid IP range: {ip_range}")
        
        if self.scanner.scan_frequency_min_hours < 1:
            raise ValueError("scan_frequency_min_hours must be at least 1")
        
        if self.scanner.max_parallel_zones < 1:
            raise ValueError("max_parallel_zones must be at least 1")
        
        if self.scanner.timeout_per_scan_seconds < 30:
            raise ValueError("timeout_per_scan_seconds must be at least 30")
        
        logger.info(f"Scanner config validated: {len(self.scanner.enabled_ip_ranges)} ranges enabled")
    
    def _validate_database_config(self):
        """Validate database configuration"""
        # Create db directory if it doesn't exist
        db_dir = os.path.dirname(self.database.db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
        
        # Create backup directory if it doesn't exist
        Path(self.database.backup_dir).mkdir(parents=True, exist_ok=True)
        
        if self.database.backup_retention_days < 1:
            raise ValueError("backup_retention_days must be at least 1")
        
        logger.info(f"Database config validated: {self.database.db_path}")
    
    def _validate_api_config(self):
        """Validate API configuration"""
        if self.api.port < 1 or self.api.port > 65535:
            raise ValueError("API port must be between 1 and 65535")
        
        if self.api.workers < 1:
            raise ValueError("API workers must be at least 1")
        
        if self.api.timeout_seconds < 1:
            raise ValueError("API timeout must be at least 1 second")
        
        logger.info(f"API config validated: {self.api.host}:{self.api.port}")
    
    def _validate_auth_config(self):
        """Validate authentication configuration"""
        if self.auth.password_min_length < 8:
            raise ValueError("password_min_length must be at least 8")
        
        if self.auth.session_timeout_minutes < 1:
            raise ValueError("session_timeout_minutes must be at least 1")
        
        if self.auth.max_login_attempts < 1:
            raise ValueError("max_login_attempts must be at least 1")
        
        logger.info("Auth config validated")
    
    def is_ip_range_allowed(self, ip_range: str) -> bool:
        """Check if an IP range is in the whitelist"""
        try:
            requested = IPv4Network(ip_range, strict=False)
            for allowed in self.scanner.enabled_ip_ranges:
                allowed_net = IPv4Network(allowed, strict=False)
                if requested.subnet_of(allowed_net):
                    return True
            return False
        except AddressValueError:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (for logging/debugging)"""
        return {
            "scanner": {
                "enabled_ip_ranges": self.scanner.enabled_ip_ranges,
                "scan_frequency_min_hours": self.scanner.scan_frequency_min_hours,
                "max_parallel_zones": self.scanner.max_parallel_zones,
                "timeout_per_scan_seconds": self.scanner.timeout_per_scan_seconds,
                "safe_mode": self.scanner.safe_mode,
            },
            "database": {
                "db_path": self.database.db_path,
                "backup_dir": self.database.backup_dir,
                "auto_backup_enabled": self.database.auto_backup_enabled,
                "backup_retention_days": self.database.backup_retention_days,
            },
            "api": {
                "host": self.api.host,
                "port": self.api.port,
                "debug": self.api.debug,
                "workers": self.api.workers,
            },
            "auth": {
                "pam_enabled": self.auth.pam_enabled,
                "password_min_length": self.auth.password_min_length,
                "session_timeout_minutes": self.auth.session_timeout_minutes,
            },
            "ssh_gateway": {
                "enabled": self.ssh_gateway.enabled,
                "idle_timeout_minutes": self.ssh_gateway.idle_timeout_minutes,
                "max_concurrent_sessions": self.ssh_gateway.max_concurrent_sessions,
            },
        }


# Global config instance
_config: Optional[MCPConfig] = None


def get_config() -> MCPConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = MCPConfig()
    return _config


def init_config(config_file: Optional[str] = None, env_prefix: str = "MCP_") -> MCPConfig:
    """Initialize the global configuration"""
    global _config
    _config = MCPConfig(config_file=config_file, env_prefix=env_prefix)
    return _config
