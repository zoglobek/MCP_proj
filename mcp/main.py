"""
Master Control Program (MCP) - Main Entry Point

Initializes configuration, database, logging, and starts the Flask API server
with Nginx reverse proxy for the web dashboard.
"""

import os
import sys
import logging
import logging.config
from pathlib import Path
from datetime import datetime

from config import init_config, get_config
from db.models import init_db, get_session, User
from api.app import create_app


# Configure logging
def setup_logging(log_level: str = "INFO"):
    """Setup comprehensive logging"""
    
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"mcp_{timestamp}.log"
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(filename)s:%(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": str(log_file),
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "file"],
        },
        "loggers": {
            "scanner": {"level": "DEBUG"},
            "api": {"level": "DEBUG"},
            "db": {"level": "DEBUG"},
            "auth": {"level": "DEBUG"},
            "ssh_gateway": {"level": "DEBUG"},
            "scheduler": {"level": "DEBUG"},
        },
    }
    
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger("mcp")
    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger


def create_admin_user(session, username: str = "admin", password: str = "admin") -> User:
    """Create default admin user if it doesn't exist"""
    from auth.password import hash_password
    
    # Check if admin already exists
    admin = session.query(User).filter_by(username=username).first()
    if admin:
        return admin
    
    # Create admin user
    admin = User(
        username=username,
        password_hash=hash_password(password),
        email="admin@localhost",
        role=User.Role.ADMIN,
        is_active=True,
    )
    session.add(admin)
    session.commit()
    
    return admin


def validate_environment():
    """Validate runtime environment and requirements"""
    logger = logging.getLogger("mcp")
    
    # Check Python version
    if sys.version_info < (3, 9):
        logger.error(f"Python 3.9+ required. Current: {sys.version}")
        sys.exit(1)
    
    # Check for required directories
    required_dirs = ["./data", "./logs", "./backups"]
    for dir_path in required_dirs:
        Path(dir_path).mkdir(exist_ok=True)
    
    logger.info("Environment validation passed")


def main():
    """Main entry point for MCP"""
    
    # Setup logging first
    logger = setup_logging()
    logger.info("=" * 80)
    logger.info("Master Control Program (MCP) - Starting")
    logger.info("=" * 80)
    
    try:
        # Validate environment
        logger.info("Validating runtime environment...")
        validate_environment()
        
        # Initialize configuration
        logger.info("Loading configuration...")
        config_file = os.getenv("MCP_CONFIG_FILE", "./config.json")
        config = init_config(config_file=config_file)
        logger.info(f"Configuration loaded: {config.to_dict()}")
        
        # Validate scanner config
        logger.info("Validating scanner configuration...")
        if config.security.get("safe_mode", True):
            logger.warning("Safe mode ENABLED - only whitelisted IP ranges will be scanned")
            logger.info(f"Enabled IP ranges: {config.scanner.enabled_ip_ranges}")
        
        # Initialize database
        logger.info(f"Initializing database at {config.database.db_path}...")
        engine = init_db(config.database.db_path)
        session = get_session(engine)
        
        # Create admin user if needed
        logger.info("Checking for admin user...")
        admin_user = create_admin_user(session, username="admin", password="admin")
        logger.info(f"Admin user ready: {admin_user.username}")
        
        # Create Flask application
        logger.info("Creating Flask application...")
        app = create_app(config, engine, session)
        
        # Log startup information
        logger.info("=" * 80)
        logger.info("MCP STARTUP INFORMATION")
        logger.info("=" * 80)
        logger.info(f"API Server: {config.api.host}:{config.api.port}")
        logger.info(f"Database: {config.database.db_path}")
        logger.info(f"Safe Mode: {config.scanner.safe_mode}")
        logger.info(f"Scan Frequency: Every {config.scanner.scan_frequency_min_hours} hours")
        logger.info(f"Max Parallel Zones: {config.scanner.max_parallel_zones}")
        logger.info(f"Default Admin User: admin / admin (CHANGE THIS PASSWORD!)")
        logger.info("=" * 80)
        logger.info("Starting Flask application...")
        
        # Run the application
        app.run(
            host=config.api.host,
            port=config.api.port,
            debug=config.api.debug,
            use_reloader=False,  # Important for production
            threaded=True,
        )
        
    except Exception as e:
        logger.exception(f"Fatal error during startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
