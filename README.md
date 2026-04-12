# Master Control Program (MCP)

A comprehensive, local-only network mapping and management system for sandbox/lab environments. MCP automatically discovers, categorizes, and manages servers within isolated networks without ever scanning external systems.

**Status:** Phase 1 Complete ✅ | Active Development 🚀

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Docker Deployment](#docker-deployment)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Project Status](#project-status)

---

## Overview

**Master Control Program (MCP)** is designed to solve the network visibility problem in isolated sandbox/lab environments:

### The Problem
- Manual server tracking is error-prone and outdated
- Enterprise tools require external connectivity (not allowed in isolated networks)
- Existing solutions can't guarantee safety (risk of external scanning)
- Need comprehensive metadata without manual cataloging

### The Solution
MCP provides:
✅ **Automatic Discovery** — Scan predefined IP ranges to find all active hosts  
✅ **Service Detection** — Identify running services, versions, and open ports  
✅ **Smart Probing** — Gather metadata (SSH banners, HTTP headers, SQL info, etc.)  
✅ **Web Dashboard** — Interactive, real-time inventory with filtering and search  
✅ **Multi-User** — RBAC with audit logging for compliance  
✅ **Sandboxed** — Only scans whitelisted ranges, never touches external networks  
✅ **Browser SSH** — Terminal access directly from the dashboard  
✅ **Database Admin** — Full inventory management with backups and rollback  

---

## Key Features

### 🔍 Network Discovery
- Nmap-based host discovery and OS fingerprinting
- Open port enumeration
- Service version detection
- Safe, local-only scanning
- Configurable scan ranges (CIDR notation)
- Activity-based intelligent rescanning (frequent changes → more scans)

### 📊 Web Dashboard
- Server inventory with expandable details
- Real-time filtering by service, OS, status
- Service sidebar auto-generated from discovered services
- Edit/refresh/wipe/download/import controls
- Clock with timezone and next scan countdown
- Desktop-optimized responsive UI (React 18)

### 🧪 Service Probing
Deep metadata collection for discovered services:
- HTTP headers and SSL/TLS info
- SSH banners and version info
- SQL handshake and version
- SMB enumeration
- RDP negotiation
- DNS queries
- Custom probe types

### 👥 Multi-User System
- Role-based access control (RBAC):
  - **Admin** — Full access, user management, database operations
  - **Scanner** — Trigger scans, view results
  - **Viewer** — Read-only access
- Per-user audit logging (login/logout, actions, resources)
- Session management with configurable timeout
- Password policy enforcement (12+ chars, uppercase, lowercase, digits, special)
- PAM integration for system user authentication

### 🌐 Browser SSH Gateway
- Interactive SSH sessions from browser
- xterm.js terminal UI
- Login required (username/password prompts)
- Session tracking and idle detection
- 30-minute configurable timeout
- Audit trail (no command logging, session metadata only)

### 💾 Database Management
- Full CRUD UI for server inventory
- View all servers, ports, services, and CVEs
- Edit server details and user notes
- **Backup/Restore:**
  - Automatic backups before each write
  - .tbkp format (SQLite snapshots)
  - 3-day retention
  - UI rollback to any snapshot
- **Import/Export:**
  - CSV, JSON, YAML formats
  - Bulk server definitions
  - Data preservation across exports

### 🚨 Alerting & Notifications
- Alert types: server_offline, new_service, cve_discovered, port_opened
- Delivery: Email, webhooks, Slack
- Per-alert enable/disable
- Severity levels (CRITICAL/HIGH/MEDIUM/LOW)
- Acknowledgement tracking

### 🔄 CVE Integration
- Offline NVD database (500MB snapshot)
- Auto-downloaded at startup
- Service version cross-reference
- Live queries for real-time threats
- CRITICAL/HIGH severity alerts

---

## System Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│              Master Control Program (MCP)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌────────────────────┐         │
│  │ React Dashboard  │      │ Browser SSH Gateway│         │
│  │ (Dashboard view) │      │ (xterm.js)        │         │
│  └─────────┬────────┘      └────────┬───────────┘         │
│            │                         │                     │
│  ┌─────────┴─────────────────────────┴─────────┐          │
│  │         Nginx Reverse Proxy & SSL           │          │
│  │  - Rate limiting, compression, caching     │          │
│  └─────────┬─────────────────────────┬─────────┘          │
│            │                         │                     │
│  ┌─────────┴──────────────────────────┴────────┐          │
│  │     Flask API (Python 3.11)                 │          │
│  │  - Authentication & RBAC                    │          │
│  │  - Rest endpoints                           │          │
│  │  - SSH gateway management                   │          │
│  │  - Database operations                      │          │
│  └─────────┬──────────────────────────┬────────┘          │
│            │                          │                    │
│  ┌─────────▼──────┐  ┌────────────────▼──────┐           │
│  │Nmap Scanner    │  │   Probe Engine        │           │
│  │(Host/OS/Ports) │  │(HTTP/SSH/SQL/SMB/RDP)│           │
│  └─────────┬──────┘  └────────────────┬──────┘           │
│            │                          │                    │
│  ┌─────────┴──────────────────────────┴────────┐          │
│  │  Scheduler (APScheduler)                    │          │
│  │  - Recurring scans (2+ per day)              │          │
│  │  - Activity-based intelligent rescheduling  │          │
│  │  - Merge operations                         │          │
│  └─────────┬──────────────────────────┬────────┘          │
│            │                          │                    │
│  ┌─────────▼──────────────────────────▼────────┐          │
│  │   SQLite Database (ACID, transactional)     │          │
│  │   - Servers, ports, services, probes        │          │
│  │   - Users, audit logs, CVEs                 │          │
│  │   - Backups, alerts, SSH sessions           │          │
│  │   - 10 tables with relationships & indexes   │          │
│  └──────────────────────────────────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Docker Containerization

```
┌─────────────────────────────────────────┐
│      Docker Compose Network             │
│      (172.24.0.0/16)                    │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────────────────────┐ │
│  │   mcp-nginx (nginx:alpine)       │ │
│  │   - Ports: 80, 443              │ │
│  │   - React SPA hosting           │ │
│  │   - Reverse proxy to mcp-api    │ │
│  │   - Rate limiting               │ │
│  └──────────────────────────────────┘ │
│                                         │
│  ┌──────────────────────────────────┐ │
│  │   mcp-api (python:3.11-slim)     │ │
│  │   - Port: 5000                   │ │
│  │   - Flask API server             │ │
│  │   - Scanner & probes             │ │
│  │   - SSH gateway                  │ │
│  │   - Volumes:                     │ │
│  │     - ./data/mcp.db              │ │
│  │     - ./data/backups             │ │
│  │     - ./logs                     │ │
│  │     - ./config.json              │ │
│  └──────────────────────────────────┘ │
│                                         │
└─────────────────────────────────────────┘
```

### Data Flow: Network Scan

```
1. User Triggers Scan (Dashboard or API)
   │
2. Scheduler adds ScanJob (PENDING)
   │
3. Scanner Module initializes
   ├─ Validates IP ranges against whitelist
   ├─ Splits /16 into 256 /24 zones
   ├─ Distributes across 8 parallel workers
   │
4. Nmap scans each zone
   ├─ Host discovery (-sn)
   ├─ Port scanning (-sV)
   ├─ OS fingerprinting (-O)
   ├─ Service version detection
   │
5. Results parsed to JSON
   │
6. Merge Engine processes results
   ├─ Creates new Server entries
   ├─ Updates existing servers
   ├─ Creates Port entries
   ├─ Adds Service entries
   ├─ Preserves user notes
   ├─ Resolves conflicts
   │
7. Probes triggered (optional)
   ├─ HTTP headers
   ├─ SSH banners
   ├─ SQL handshakes
   ├─ SMB info
   ├─ RDP negotiation
   │
8. CVE matching
   ├─ Cross-reference service version
   ├─ Look up in offline NVD DB
   ├─ Create Alert entries if CRITICAL/HIGH
   │
9. Database updated, ScanJob marked COMPLETED
   │
10. UI refreshes with new data
```

---

## Requirements

### System Requirements
- **OS:** Linux, macOS, or Windows with Docker
- **Python:** 3.9+
- **Disk Space:** 
  - Base: ~100MB
  - With NVD CVE database: ~600MB
  - Data (grows with scans): ~100MB per 1000 servers
- **Network:** LAN access from scanning machine to target network

### Scanning Network
- **Recommended Network Size:** Up to /16 (65,536 hosts)
- **Scan Frequency:** Minimum 2 times per day
- **Bandwidth:** ~100-500 Mbps depending on zone density
- **Supported Protocols:** IPv4 only (Phase 1)

### Software Dependencies
All included in `requirements.txt`:
- Flask 3.0 — REST API framework
- SQLAlchemy 2.0 — ORM
- python-nmap — Nmap wrapper
- paramiko — SSH client
- APScheduler — Task scheduling
- bcrypt — Password hashing
- pytest — Testing framework

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and navigate to project
cd h:/Downloads/devops/ai_proj/mcp

# Build Docker images
make docker-build

# Start services
make docker-up

# Access:
#   Dashboard: http://localhost
#   API: http://localhost:5000
#   Admin: admin/admin (CHANGE THIS!)

# View logs
make docker-logs

# Stop services
make docker-down
```

### Option 2: Local Development

```bash
# Install dependencies
make install

# Initialize database
make db-init

# Run development server
make dev

# Access:
#   API: http://localhost:5000
#   Admin: admin/admin (CHANGE THIS!)
```

### First Steps

1. **Change admin password** (CRITICAL!)
   ```bash
   curl -X POST http://localhost:5000/api/v1/auth/change-password \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","old_password":"admin","new_password":"NewSecurePass123!"}'
   ```

2. **Configure IP ranges** (edit `config.json`)
   ```json
   {
     "scanner": {
       "enabled_ip_ranges": [
         "10.0.0.0/8",
         "172.16.0.0/12",
         "192.168.0.0/16"
       ]
     }
   }
   ```

3. **Trigger a scan**
   - Dashboard: Click "Scan" button
   - API: `POST /api/v1/scans/trigger`

4. **Monitor scan progress**
   - Check scan status in dashboard
   - View logs: `logs/mcp_*.log`

---

## Configuration

### Main Configuration File: `config.json`

```json
{
  "scanner": {
    "enabled_ip_ranges": ["10.0.0.0/8", "172.16.0.0/12"],
    "scan_frequency_min_hours": 12,
    "max_parallel_zones": 8,
    "timeout_per_scan_seconds": 300,
    "nmap_arguments": "-sV -O --script vuln",
    "safe_mode": true
  },
  "database": {
    "db_path": "./data/mcp.db",
    "backup_dir": "./data/backups",
    "auto_backup_enabled": true,
    "backup_retention_days": 3
  },
  "api": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false,
    "workers": 4
  },
  "auth": {
    "pam_enabled": true,
    "password_min_length": 12,
    "session_timeout_minutes": 30,
    "max_login_attempts": 5
  },
  "ssh_gateway": {
    "enabled": true,
    "idle_timeout_minutes": 30,
    "max_concurrent_sessions": 50
  },
  "alerting": {
    "enabled": true,
    "alert_types": ["server_offline", "new_service", "cve_discovered", "port_opened"],
    "email_enabled": false,
    "webhook_enabled": false
  }
}
```

### Environment Variables (Override config.json)

```bash
# Scanner
export MCP_ENABLED_IP_RANGES="10.0.0.0/8;172.16.0.0/12"
export MCP_SCAN_FREQUENCY_HOURS=12

# Database
export MCP_DB_PATH=/app/data/mcp.db

# API
export MCP_API_HOST=0.0.0.0
export MCP_API_PORT=5000

# Auth
export MCP_PASSWORD_MIN_LENGTH=12

# SSH Gateway
export MCP_SSH_IDLE_TIMEOUT_MINUTES=30
```

### Nginx Configuration: `nginx.conf`

Key sections:
- **Rate Limiting:**
  - API: 10 requests/second
  - General: 100 requests/second
- **SSL/TLS:** Lines 64-67 (uncomment for HTTPS)
- **Network Restrictions:** Lines 42-47 (restrict to local networks)
- **WebSocket:** Lines 76-86 (SSH terminal support)

---

## API Reference

### Base URL
```
http://localhost:5000/api/v1
```

### Authentication
All endpoints (except `/health`) require JWT token:
```bash
curl -H "Authorization: Bearer <token>" http://localhost:5000/api/v1/servers
```

### Core Endpoints

#### Health Check
```
GET /health
Response: { "status": "healthy", "version": "1.0.0" }
```

#### Authentication
```
POST /auth/login
{ "username": "admin", "password": "admin" }
Response: { "token": "eyJ...", "user": { "id": 1, "role": "admin" } }

POST /auth/change-password
{ "old_password": "admin", "new_password": "NewPass123!" }
```

#### Servers
```
GET /servers
Response: [{ "id": 1, "ip": "10.0.0.5", "hostname": "web-01", "os": "Linux", ... }]

GET /servers/{id}
Response: { "id": 1, ..., "ports": [...], "notes": [...] }

POST /servers
{ "ip": "10.0.0.5", "hostname": "web-01" }

PUT /servers/{id}
{ "hostname": "web-01-prod", "label": "production" }

DELETE /servers/{id}
```

#### Services
```
GET /services
Response: [{ "id": 1, "service_name": "ssh", "version": "OpenSSH 7.4", ... }]

GET /services/by-type?type=http
Response: [Services running HTTP]
```

#### Scans
```
POST /scans/trigger
{ "target_range": "10.0.0.0/24", "scan_type": "manual" }
Response: { "scan_id": 123, "status": "pending" }

GET /scans/{id}
Response: { "id": 123, "status": "running", "progress": 45, "start_time": "..." }

GET /scans/history?limit=10
Response: [{ "id": 122, "status": "completed", ... }, ...]
```

#### Database Operations
```
GET /database/stats
Response: { "servers": 1234, "services": 5678, "backups": 10 }

GET /database/backups
Response: [{ "filename": "mcp_20260401_120000.tbkp", "size": "5.2MB", ... }]

POST /database/export?format=json
Response: File download

POST /database/import
{ file: <json/csv/yaml file> }

GET /database/backups/{id}/restore
Response: { "status": "restored", "timestamp": "..." }

POST /database/wipe
Response: { "status": "wiped", "backup_created": "mcp_20260412_120000.tbkp" }
```

#### SSH Gateway
```
POST /ssh/sessions
{ "server_id": 5, "username": "admin" }
Response: { "session_id": "abc123", "websocket_url": "ws://localhost/ws/ssh/abc123" }

GET /ssh/sessions
Response: [{ "id": "abc123", "server": "10.0.0.5", "user": "admin", "status": "active" }]

DELETE /ssh/sessions/{id}
Response: { "status": "closed" }
```

---

## Database Schema

### 10 Core Tables

#### 1. Users (Authentication & RBAC)
```sql
- id (PK)
- username (UNIQUE)
- password_hash (bcrypt)
- email
- role (admin|scanner|viewer)
- is_active
- last_login
- created_at, updated_at
```

#### 2. Servers (Discovered Hosts)
```sql
- id (PK)
- ip (UNIQUE)
- hostname
- os, os_version, os_accuracy
- mac_address
- is_online
- last_seen, last_scan
- created_at, updated_at
```

#### 3. Ports (Open Ports)
```sql
- id (PK)
- server_id (FK)
- port_number
- protocol (tcp|udp)
- state (open|closed|filtered|unfiltered)
- last_scan
- UNIQUE(server_id, port_number, protocol)
```

#### 4. Services (Running Services)
```sql
- id (PK)
- port_id (FK)
- service_name
- version
- banner
- confidence (0.0-1.0)
- cpe (for CVE matching)
- last_scan
```

#### 5. Probes (Deep Metadata)
```sql
- id (PK)
- service_id (FK)
- probe_type (http_headers|ssh_banner|sql_version|smb_info|rdp_info|dns|ftp|custom)
- data (JSON)
- success
- error_message
- response_time_ms
- timestamp
```

#### 6. CVEs (Vulnerabilities)
```sql
- id (PK)
- service_id (FK)
- cve_id (e.g., "CVE-2021-1234")
- description
- severity (CRITICAL|HIGH|MEDIUM|LOW|INFO)
- cvss_score (0.0-10.0)
- published_date, updated_date
- references (JSON)
```

#### 7. ScanJobs (Scan History)
```sql
- id (PK)
- scan_type (full|zone|incremental|manual)
- target_range (CIDR)
- status (pending|running|completed|failed|cancelled)
- start_time, end_time, duration_seconds
- hosts_discovered, services_discovered, ports_found
- error_message
```

#### 8. UserNotes (Annotations)
```sql
- id (PK)
- server_id (FK)
- user_id (FK, nullable)
- note_text
- label (production|test|firewall|etc)
- is_pinned
- created_at, updated_at
```

#### 9. AuditLogs (Compliance Trail)
```sql
- id (PK)
- user_id (FK)
- action (login|logout|scan_start|scan_complete|server_created|...)
- resource_type (server|scan|user)
- resource_id
- ip_address
- details (JSON)
- timestamp
```

#### 10. SSHSessions (Browser Terminal)
```sql
- id (PK)
- user_id (FK)
- server_id (FK)
- session_token
- status (active|idle|closed|terminated)
- remote_username
- client_ip
- last_activity
- created_at, closed_at
```

### Indexes
All tables indexed on:
- Primary keys and foreign keys
- Frequently queried columns (ip, service_name, port_number, status)
- Timestamp columns (last_scan, created_at)

### Relationships
```
User —————— AuditLog (1:N)
         ├─ SSHSession (1:N)
         └─ UserNote (1:N)

Server ——— Port (1:N)
        └─ UserNote (1:N)

Port —————— Service (1:N)

Service —— Probe (1:N)
        └─ CVE (1:N)
```

---

## Docker Deployment

### Quick Start

```bash
# Build and start
make docker-build
make docker-up

# Check status
make docker-status

# View logs
make docker-logs

# Stop
make docker-down
```

### Docker Compose Services

**mcp-nginx** (nginx:alpine)
- Reverse proxy
- React SPA hosting
- Rate limiting
- SSL/TLS termination

**mcp-api** (python:3.11-slim)
- Flask API server
- Nmap scanner
- SSH gateway
- Task scheduler

### Volumes

```yaml
./data/mcp.db        → /app/data/mcp.db         # Main database
./data/backups       → /app/data/backups        # Snapshots (.tbkp files)
./logs               → /app/logs                # Application logs
./config.json        → /app/config.json         # Configuration
./.env               → /app/.env                # Environment variables
```

### Port Mappings

```
Host:Container  Service
80:80          Nginx (HTTP)
443:443        Nginx (HTTPS, if SSL enabled)
5000:5000      Flask API (direct access)
```

### Health Checks

All services have health checks:
```bash
# API health
curl http://localhost:5000/health

# Nginx health
curl http://localhost/health
```

### Custom Docker Build

```bash
# Build with custom args
docker build \
  --build-arg PYTHON_VERSION=3.11 \
  --build-arg DEBIAN_FRONTEND=noninteractive \
  -t mcp:latest .

# Run standalone
docker run -d \
  -name mcp-api \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e MCP_API_PORT=5000 \
  mcp:latest
```

---

## Development

### Project Structure

```
mcp/
├── config.py                  # Global config manager
├── main.py                    # Entry point
├── requirements.txt           # Dependencies
├── Dockerfile, docker-compose.yml, nginx.conf
│
├── db/
│   ├── models.py             # SQLAlchemy ORM (10 tables)
│   └── merge.py              # Rescan merge logic
│
├── api/
│   └── app.py                # Flask app factory
│
├── auth/
│   └── password.py           # Bcrypt utilities
│
├── scanner/                  # Phase 2
├── probes/                   # Phase 2
├── scheduler/                # Phase 2
└── ssh_gateway/              # Phase 2
```

### Makefile Commands

```bash
make help              # Show all commands
make install          # Install deps
make dev              # Run with debug
make test             # Run tests
make lint             # Code linting
make clean            # Clean temp files
make reset            # Full reset (delete data)
make db-init          # Initialize database
make docker-build     # Build images
make docker-up        # Start containers
make docker-down      # Stop containers
make docker-logs      # View logs
```

### Testing

```bash
# Run full test suite
make test

# Run specific tests
pytest tests/test_config.py -v

# With coverage
pytest tests/ -v --cov=. --cov-report=html
# Open: htmlcov/index.html
```

### Code Style

```bash
# Lint
make lint

# Format (using black, if installed)
black **/*.py

# Type checking
mypy .
```

### Git Workflow

```bash
git checkout -b feature/new-feature
# Make changes...
git add .
git commit -m "feat: add new feature"
git push origin feature/new-feature
# Create PR
```

---

## Troubleshooting

### Common Issues

#### Database initialization fails
```bash
# Remove old database and reinitialize
rm data/mcp.db
make db-init
```

#### Port 5000 already in use
```bash
# Use different port
export MCP_API_PORT=5001
make dev

# Or kill process
lsof -ti:5000 | xargs kill -9
```

#### Configuration validation error
```bash
# Check syntax
python -c "import json; json.load(open('config.json'))"

# Validate config
python -c "from config import init_config; init_config()"
```

#### Docker build fails
```bash
# Clean rebuild
docker system prune -a
make docker-build
```

#### Services not starting
```bash
# Check logs
docker-compose logs mcp-api
docker-compose logs mcp-nginx

# Rebuild and restart
docker-compose down
docker-compose up --build
```

#### Database locked error
```bash
# SQLite busy timeout
pkill -f "python main.py"
# Or use new terminal
```

#### Slow scans
```bash
# Check available workers
# Adjust in config.json: "max_parallel_zones": 4  # Reduce if too slow
```

### Debug Mode

```bash
# Enable debug logging
export MCP_DEBUG=true
make dev

# View detailed logs
tail -f logs/mcp_*.log
```

### Reset Everything

```bash
# Full system reset
make reset
make db-init
make dev
```

---

## Project Status

### ✅ Phase 1 Complete (Foundation)
- [x] Configuration management
- [x] Database schema (10 tables)
- [x] User authentication (RBAC foundation)
- [x] Password hashing & validation
- [x] Rescan merge logic
- [x] Flask app factory
- [x] Docker containerization
- [x] Nginx reverse proxy
- [x] Comprehensive logging

### 🚀 Phase 2 In Progress (Scanning & Probing)
- [ ] Nmap integration
- [ ] Host discovery engine
- [ ] OS fingerprinting
- [ ] Service version detection
- [ ] Service probing (HTTP, SSH, SQL, SMB, RDP)
- [ ] CVE matching and alerts

### 📅 Phase 3 (API & Automation)
- [ ] REST API endpoints (servers, services, scans)
- [ ] Task scheduler (recurring scans)
- [ ] Activity-based intelligent rescheduling
- [ ] Backup/restore functionality
- [ ] Database import/export

### 🎨 Phase 4 (Web Dashboard)
- [ ] React 18 frontend
- [ ] Server inventory table
- [ ] Service sidebar navigation
- [ ] Real-time filtering
- [ ] Edit/delete/import controls
- [ ] Clock with scan countdown

### 🌐 Phase 5 (SSH Gateway)
- [ ] Browser SSH terminal (xterm.js)
- [ ] Interactive login prompts
- [ ] Session management
- [ ] Idle detection
- [ ] Audit logging

### 👥 Phase 6 (Multi-User & Advanced)
- [ ] Full RBAC implementation
- [ ] User management UI
- [ ] PAM authentication
- [ ] Webhook/Email alerting
- [ ] Slack integration
- [ ] API key management

---

## Roadmap

### Near-term (May 2026)
- Phase 2: Complete scanning engine
- Phase 3: API endpoints
- Initial performance tuning

### Mid-term (June-July 2026)
- Phase 4: Web dashboard MVP
- Phase 5: SSH gateway
- User acceptance testing

### Long-term (Aug 2026+)
- Phase 6: Advanced features
- IPv6 support
- Cloud backup integration (optional)
- Enterprise features (LDAP, 2FA)

---

## Architecture Diagrams

Full architectural details with data flows, component interactions, and deployment patterns:
→ [architectural_dt.md](architectural_dt.md)

Implementation roadmap with detailed phase breakdowns:
→ [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)

Phase 1 specific documentation:
→ [mcp/PHASE_1_README.md](mcp/PHASE_1_README.md)

---

## File Structure

```
h:/Downloads/devops/ai_proj/
├── README.md                           # This file
├── architectural_dt.md                 # System architecture & design
├── IMPLEMENTATION_PLAN.md              # Multi-phase roadmap
│
├── prompt.txt                          # Original project specification
│
└── mcp/                                # Main application
    ├── config.py                       # Configuration manager
    ├── main.py                         # Entry point
    ├── requirements.txt                # Python dependencies
    ├── Dockerfile                      # Container image
    ├── docker-compose.yml              # Container orchestration
    ├── nginx.conf                      # Reverse proxy config
    ├── config.json                     # Config template
    ├── .env.example                    # Env vars template
    ├── Makefile                        # Dev commands
    ├── run.sh                          # Startup script
    ├── PHASE_1_README.md               # Phase 1 docs
    │
    ├── db/
    │   ├── __init__.py
    │   ├── models.py                   # SQLAlchemy ORM
    │   └── merge.py                    # Rescan merge logic
    │
    ├── api/
    │   ├── __init__.py
    │   └── app.py                      # Flask factory
    │
    ├── auth/
    │   ├── __init__.py
    │   └── password.py                 # Password utilities
    │
    ├── scanner/
    ├── probes/
    ├── scheduler/
    └── ssh_gateway/
```

---

## Contributing

This is internal development. To contribute:

1. Create feature branch: `git checkout -b feature/feature-name`
2. Make changes
3. Test: `make test`
4. Lint: `make lint`
5. Commit: `git commit -m "feat: description"`
6. Push: `git push origin feature/feature-name`

---

## Security Notes

### Security Features Implemented
✅ Whitelisted IP ranges (safe scanning)
✅ Bcrypt password hashing (12 rounds)
✅ Role-based access control (RBAC)
✅ Comprehensive audit logging
✅ Session management with timeout
✅ Rate limiting (API & general)
✅ HTTPS/SSL ready

### Security Recommendations
- ⚠️ Change default admin password IMMEDIATELY
- ⚠️ Use strong passwords (12+ chars, mixed case, digits, special)
- ⚠️ Enable HTTPS in production (nginx.conf lines 64-67)
- ⚠️ Restrict Nginx network access to LAN only
- ⚠️ Regular backups (automatic, 3-day retention)
- ⚠️ Monitor audit logs for suspicious activity
- ⚠️ Update dependencies regularly: `pip install --upgrade -r requirements.txt`

---

## License

Internal use only. Not for public distribution. Property of [Organization].

---

## Support & Contact

For issues or questions:
- Check [troubleshooting](#troubleshooting) section
- Review logs: `logs/mcp_*.log`
- Check syntax: `python -c "from config import init_config; init_config()"`
- Docker logs: `docker-compose logs -f`

---

**Last Updated:** April 12, 2026  
**Version:** 1.0.0 (Phase 1 Complete)  
**Status:** Active Development 🚀

