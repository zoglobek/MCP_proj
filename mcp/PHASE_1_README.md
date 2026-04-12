# Master Control Program (MCP) - Phase 1 Scaffolding

Complete foundation and core infrastructure for the MCP network management system.

## 📋 What's Been Built

### ✅ Phase 1.1: Project Scaffolding & Configuration

- **`config.py`** — Comprehensive configuration manager with:
  - Scanner settings (IP range whitelisting, scan frequency)
  - Database configuration (path, backups, retention)
  - API settings (host, port, workers)
  - Authentication config (PAM enabled, password rules)
  - SSH gateway settings
  - Alerting configuration
  - Environment variable override support
  - Full validation on load

- **`requirements.txt`** — Python dependencies including:
  - Flask + CORS for REST API
  - SQLAlchemy 2.0 ORM
  - bcrypt for password hashing
  - APScheduler for task scheduling
  - paramiko for SSH support
  - pytest for testing

- **`main.py`** — Application entry point with:
  - Comprehensive logging setup
  - Environment validation
  - Config initialization
  - Database initialization
  - Admin user creation
  - Flask app startup

- **`Makefile`** — Developer commands:
  - `make install` — Install dependencies
  - `make dev` — Run with debug mode
  - `make docker-up` — Start Docker containers
  - `make test` — Run test suite
  - And more...

- **`run.sh`** — Bash startup script for Linux/Mac

### ✅ Phase 1.2: Database Schema & ORM Layer

**`db/models.py`** — Complete SQLAlchemy models with 10 tables:

1. **`User`** — Multi-user RBAC with roles (admin, scanner, viewer)
   - Bcrypt password hashing
   - Session tracking
   - Audit trail

2. **`Server`** — Discovered hosts
   - IP, hostname, OS fingerprinting
   - Online/offline status tracking
   - Last seen and scan timestamps

3. **`Port`** — Open ports on servers
   - Port number, protocol (TCP/UDP), state
   - Uniqueness constraint per server/port/protocol
   - Relationship to services

4. **`Service`** — Services running on ports
   - Service name, version, banner
   - Confidence scoring
   - CPE for CVE matching
   - Service detection timestamps

5. **`Probe`** — Deep metadata from service probing
   - HTTP headers, SSH banner, SQL version, SMB info, RDP info
   - Success/failure tracking
   - Response time metrics
   - JSON-structured data storage

6. **`CVE`** — Vulnerability tracking
   - CVE ID, severity (CRITICAL/HIGH/MEDIUM/LOW)
   - CVSS scores
   - References and descriptions
   - Linked to services

7. **`ScanJob`** — Scan execution history
   - Scan type (FULL/ZONE/INCREMENTAL/MANUAL)
   - Status tracking (PENDING/RUNNING/COMPLETED/FAILED)
   - Host/service/port discovery counts
   - Duration and error tracking

8. **`UserNote`** — User annotations on servers
   - Labels (production, test, firewall, etc.)
   - Pinning for important notes
   - User tracking

9. **`AuditLog`** — Comprehensive audit trail
   - Login/logout tracking
   - Scan operations
   - Database changes (CRUD)
   - SSH session tracking
   - User creation/modification
   - Resource tracking with timestamps

10. **`SSHSession`** — Browser SSH session management
    - Session tokens for xterm.js gateway
    - Active/idle/closed status
    - Client IP and remote username tracking
    - Idle detection

**`db/merge.py`** — Rescan merge logic with:
- Conflict-free merging of new and existing data
- User edit preservation
- Service version change detection
- Port state tracking (open → closed)
- Comprehensive merge reports

### ✅ Docker & Deployment

- **`Dockerfile`** — Multi-stage Docker image:
  - Python 3.11 slim base
  - nmap and SSH client preinstalled
  - Health checks
  - Volume-ready for persistent data

- **`docker-compose.yml`** — Production-ready orchestration:
  - MCP API backend (port 5000)
  - Nginx reverse proxy (ports 80/443)
  - Shared volumes for data, backups, logs
  - Custom bridge network
  - Health checks on all services

- **`nginx.conf`** — High-performance reverse proxy:
  - Rate limiting (API: 10r/s, General: 100r/s)
  - WebSocket support for SSH terminal
  - Gzip compression
  - SSL/TLS ready
  - Local network access control (configurable)
  - React SPA support

- **`config.json`** — Example configuration with sensible defaults
- **`.env.example`** — Environment variables template

### ✅ Authentication & Security

- **`auth/password.py`** — Password management:
  - bcrypt hashing (12 rounds)
  - Strength validation (length, uppercase, lowercase, digits, special chars)
  - Verification utilities
  - Configurable password rules

### ✅ API Foundation

- **`api/app.py`** — Flask app factory:
  - CORS configuration for LAN access
  - Health check endpoint
  - Info endpoint
  - Context configuration for database and config

## 🏗️ Project Structure

```
mcp/
├── config.py                 # Global configuration manager
├── main.py                   # Entry point
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Container orchestration
├── nginx.conf                # Nginx reverse proxy config
├── config.json               # Configuration file (default values)
├── .env.example              # Environment variables template
├── Makefile                  # Development commands
├── run.sh                     # Startup script
│
├── db/                        # Database layer
│   ├── __init__.py
│   ├── models.py            # SQLAlchemy ORM models (10 tables)
│   └── merge.py             # Rescan merge logic
│
├── api/                       # REST API
│   ├── __init__.py
│   └── app.py               # Flask app factory
│
├── auth/                      # Authentication & authorization
│   ├── __init__.py
│   └── password.py          # Password hashing/verification
│
├── scanner/                   # Network scanning engine (Phase 2)
├── probes/                    # Service probing module (Phase 2)
├── scheduler/                 # Task scheduling (Phase 2)
└── ssh_gateway/               # Browser SSH gateway (Phase 2)
```

## 🚀 Getting Started

### Local Development

```bash
# Install dependencies
make install

# Initialize database
make db-init

# Run development server
make dev

# The app will start at http://localhost:5000
# Default admin: admin / admin (CHANGE THIS!)
```

### Docker Deployment

```bash
# Build Docker images
make docker-build

# Start all services
make docker-up

# Access:
#   - API: http://localhost:5000
#   - Dashboard: http://localhost
#   - Check logs: docker-compose logs -f

# Stop services
make docker-down
```

## 🔧 Configuration

Edit `config.json` or use environment variables:

```bash
export MCP_ENABLED_IP_RANGES="10.0.0.0/8;172.16.0.0/12"
export MCP_SCAN_FREQUENCY_HOURS=12
export MCP_API_PORT=5000
export MCP_DEBUG=false
```

**Key Settings:**
- `scanner.enabled_ip_ranges` — CIDR ranges to scan (whitelist)
- `scanner.scan_frequency_min_hours` — Minimum hours between full scans
- `database.db_path` — SQLite database location
- `database.backup_retention_days` — Keep backups for N days
- `auth.pam_enabled` — Use PAM for system users
- `ssh_gateway.idle_timeout_minutes` — Session timeout

## 📊 Database Schema

All tables use:
- Proper indexing on frequently-queried columns (ip, service_name, port_number)
- Foreign key relationships with cascade delete
- Audit logging (created_at, updated_at)
- Enum types for state/status fields
- Unique constraints to prevent duplicates
- Check constraints for value ranges (e.g., ports 1-65535)

## 🔐 Security Features (Phase 1)

- ✅ Bcrypt password hashing (12 rounds)
- ✅ Role-based access control (RBAC) foundation
- ✅ Comprehensive audit logging
- ✅ Safe scanning mode (whitelisted IP ranges only)
- ✅ Configuration validation on startup
- 🔄 Coming: Multi-user authentication (Phase 2)
- 🔄 Coming: SSH session isolation (Phase 2)
- 🔄 Coming: API rate limiting improvements (Phase 2)

## 📝 Logging

Logs are stored in `./logs/` with timestamps:
```
logs/
├── mcp_20260412_120000.log   # Detailed logs
└── ...
```

Log levels:
- **DEBUG** — Detailed operation tracking
- **INFO** — Major events
- **WARNING** — Configuration issues
- **ERROR** — Failures and exceptions

## ✅ What's Next (Phase 2)

- Network Scanning Engine (nmap integration)
- Service Probing Module (HTTP, SSH, SQL, SMB, RDP)
- REST API Endpoints (servers, services, scans)
- Task Scheduler (recurring scans)
- SSH Gateway (browser-based terminal)
- Web Dashboard (React + Tailwind)
- Multi-user management system
- Alerting system (email, webhooks, Slack)

## 🧪 Testing

```bash
# Run test suite
make test

# Run with coverage report
pytest tests/ -v --cov=. --cov-report=html
```

## 📚 Documentation

- [Architectural Details](../architectural_dt.md) — System design, APIs, data flows
- [Implementation Plan](../IMPLEMENTATION_PLAN.md) — Full roadmap and phases
- [config.json](./config.json) — Configuration reference
- [nginx.conf](./nginx.conf) — Reverse proxy configuration

## 🛠️ Troubleshooting

**Database initialization error:**
```bash
rm data/mcp.db
make db-init
```

**Port 5000 already in use:**
```bash
# Change port in config.json or:
export MCP_API_PORT=5001
make dev
```

**Configuration validation fails:**
```bash
# Check config.json syntax:
python -c "import json; json.load(open('config.json'))"

# Validate config:
python -c "from config import init_config; init_config()"
```

**Docker issues:**
```bash
# Clean rebuild
make docker-down
make clean
make docker-build
make docker-up
```

## 📄 License

Internal use only. MCP - Master Control Program for local sandbox networks.

---

**Phase 1 Status**: ✅ COMPLETE
**Next Phase**: Phase 2 - Network Scanning Engine
**Ready for**: Phase 1.1 and 1.2 integration testing
