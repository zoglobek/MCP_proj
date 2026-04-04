# Master Control Program (MCP) - Enhanced Architectural Design
**Version:** 2.0 (Updated with Browser SSH, Database Admin, User Auth, Distributed Scanning)  
**Date:** April 4, 2026  
**Status:** Active Design Document  

This document provides comprehensive technical architecture for the MCP system with all enhanced requirements including browser SSH gateway, database backup/rollback, multi-user auth, zone-based distributed scanning, CVE integration, and React frontend.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture Overview](#system-architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Multi-Container Docker Deployment](#multi-container-docker-deployment)
5. [Frontend Architecture (React)](#frontend-architecture-react)
6. [Browser SSH Gateway](#browser-ssh-gateway)
7. [Distributed Scanning Architecture](#distributed-scanning-architecture)
8. [Database Layer & Transaction Backups](#database-layer--transaction-backups)
9. [User Authentication & Authorization](#user-authentication--authorization)
10. [REST API Specification](#rest-api-specification)
11. [CVE Integration & Vulnerability Detection](#cve-integration--vulnerability-detection)
12. [Alerting & Notification System](#alerting--notification-system)
13. [Configuration Management](#configuration-management)
14. [Performance Targets & Optimization](#performance-targets--optimization)
15. [Security Architecture](#security-architecture)
16. [Extension Points](#extension-points)

---

## Executive Summary

The MCP v2.0 is a production-grade network management and discovery system designed for large isolated networks (/16 - up to 65,536 IPs). Key enhancements:

- **Browser SSH Gateway** — Interactive SSH sessions from web dashboard with login prompts
- **Database Admin UI** — Full CRUD with versioned backups (.tbkp files retained 3 days)
- **Multi-User System** — 10+ concurrent users with role-based access, audit logging per user
- **Distributed Scanning** — Activity-based zone division with intelligent rescanning (high-change zones more frequent)
- **Tech Stack** — Rust core scanner + Python backend + React frontend
- **Deployment** — Multi-container Docker Compose with persistent volumes for backups
- **Performance** — <500ms API responses, distributed 48-zone coverage of /16 network
- **LAN Accessible** — Dashboard available across LAN subnet (not just localhost)

---

## System Architecture Overview

### Layered System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            PRESENTATION LAYER                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ React Web Dashboard (Desktop-Only, LAN-Accessible)                │ │
│  │ • Server inventory table with real-time updates                   │ │
│  │ • Service sidebar with dynamic categorization                    │ │
│  │ • Browser SSH terminal with login management                     │ │
│  │ • Database admin console with query visualization                │ │
│  │ • Time/date clock with timezone awareness + scan countdown       │ │
│  │ • Edit/Refresh/Wipe/Download/Import controls                    │ │
│  │ • Change history and rollback UI                                 │ │
│  │ • User profile & permissions management                          │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                  ↓                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Nginx (HTTPS, LAN-only, IP whitelist enforcement)                │ │
│  │ • TLS termination with self-signed cert                          │ │
│  │ • Static asset serving (JS, CSS, fonts)                          │ │
│  │ • Reverse proxy to Flask API on port 5000                        │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                              │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Flask REST API (Python) - Port 5000                               │ │
│  │ • Request/response serialization                                  │ │
│  │ • Authentication middleware (JWT tokens, session mgmt)            │ │
│  │ • Authorization middleware (RBAC enforcement)                     │ │
│  │ • Rate limiting & IP validation                                   │ │
│  │ • Request logging & tracing                                       │ │
│  │ • Error handling & exception mapping                              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                  ↓                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Business Logic Layer (Python)                                     │ │
│  │ ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │ │
│  │ │ Scan        │ │ Probe        │ │ SSH Gateway  │ │ Scheduler  │ │ │
│  │ │ Orchestor   │ │ Orchestor    │ │ (PTY mgmt)   │ │ (APSched)  │ │ │
│  │ │ (Rust calls)│ │ (Rust calls) │ │              │ │            │ │ │
│  │ └─────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │ │
│  │ ┌─────────────┐ ┌──────────────┐ ┌──────────────┐                │ │
│  │ │ Auth Svc    │ │ DB Txn Mgr   │ │ Alert Svc    │                │ │
│  │ │ (bcrypt)    │ │ (Backup/     │ │ (Email,      │                │ │
│  │ │ (JWT)       │ │  Rollback)   │ │  Webhooks)   │                │ │
│  │ └─────────────┘ └──────────────┘ └──────────────┘                │ │
│  │ ┌─────────────────────────────┐                                  │ │
│  │ │ CVE Integration Service     │                                  │ │
│  │ │ (Offline DB + Online API)   │                                  │ │
│  │ └─────────────────────────────┘                                  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA ACCESS LAYER                              │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ SQLite ORM (SQLAlchemy + Python)                                  │ │
│  │ • Database abstraction & query building                           │ │
│  │ • Transaction management & ACID guarantees                        │ │
│  │ • Connection pooling                                              │ │
│  │ • Migration system for schema updates                             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                  ↓                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ SQLite Database (Persistent Volume)                               │ │
│  │ • servers, ports, services, probes tables                         │ │
│  │ • users, roles, permissions tables                                │ │
│  │ • scan_jobs, scan_zones, change_log tables                        │ │
│  │ • Indexes on frequently queried fields                            │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Backup Directory (Persistent Volume)                              │ │
│  │ • .tbkp files (SQLite snapshots) - 3 day retention                │ │
│  │ • .tbkp metadata (timestamp, change summary)                      │ │
│  │ • Host backup mirror (daily sync from container)                  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      SCANNER & PROBE LAYER                              │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Rust Scanner Core (High-Performance Network Operations)           │ │
│  │ • Nmap wrapper with safe, local-only scanning                    │ │
│  │ • Multi-threaded /24 subnet parallel scanning                    │ │
│  │ • Zone management & activity tracking                            │ │
│  │ • Service detection with version fingerprinting                  │ │
│  │ • Fast protocol probing (SSH banner, HTTP headers, etc.)         │ │
│  │ • Python FFI bindings                                            │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                  ↓                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Python Flask Plugins to Rust Core                                │ │
│  │ • HTTP Probe (headers + content analysis)                        │ │
│  │ • SSH Probe (banner + crypto negotiation)                        │ │
│  │ • SQL Probe (MySQL, MSSQL, PostgreSQL handshakes)                │ │
│  │ • SMB Probe (share enumeration + OS detection)                   │ │
│  │ • RDP Probe (TLS negotiation + version extraction)               │ │
│  │ • DNS/DHCP/SNMP/SMTP/FTP/Telnet Probes                          │ │
│  │ • VNC Probe (version detection)                                  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    SYSTEM INTEGRATION LAYER                             │
│  • Sandbox Network (User-configured IP ranges, whitelisted only)       │
│  • System SSH for gateway sessions                                     │
│  • Host filesystem for backup sync                                     │
│  • External CVE API (NVD, Rapid7) - Rate limited, cached               │
│  • Webhook/Email integration for alerts                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend & Core Services

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Scanner Core** | Rust | Ultra-fast nmap wrapper, parallel /24 scanning, < 50ms probe latency |
| **Python Bindings** | PyO3 or ctypes | Bridge Rust performance to Python API layer |
| **REST API** | Python 3.11 + Flask | Rapid development, async support with gevent |
| **ORM** | SQLAlchemy | Abstraction for SQLite, transaction safety, migrations |
| **Database** | SQLite | Persistent, serverless, ACID transactions, backup-friendly |
| **Scheduling** | APScheduler | Cron-like distributed zone scanning, handles 48 zones across 24h |
| **SSH Gateway** | paramiko + ptyprocess | Interactive pseudo-terminal support, login session management |
| **Authentication** | bcrypt + PyJWT | Password hashing, stateless JWT tokens |
| **CVE Integration** | requests + offline NVD DB | Hybrid local cache + live API queries |

### Frontend

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Framework** | React 18 | Component reusability, state management, real-time updates |
| **HTTP Client** | axios | Interceptor support for auth tokens, timeout handling |
| **Terminal UI** | xterm.js | Browser-based terminal for SSH sessions |
| **Tables** | React Table v8 | Virtualization for 1000s of servers, sorting/filtering |
| **Charts** | Chart.js + react-chartjs-2 | Network statistics, service distribution, scan timelines |
| **UI Kit** | Tailwind CSS + Headless UI | Desktop-optimized, responsive components |
| **State Mgmt** | React Context + Hooks | Lightweight, no external store needed for current scope |
| **Build Tool** | Vite | Fast dev server, optimized production builds |

### Infrastructure & Deployment

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Web Server** | Nginx | Reverse proxy, HTTPS termination, static asset serving |
| **Containerization** | Docker + Docker Compose | Multi-container orchestration, volume persistence |
| **Reverse Proxy** | Nginx (built-in) | Route `/` to frontend, `/api` to Flask backend |
| **TLS** | Self-signed certs | HTTPS for LAN-only access, security by network isolation |

---

## Multi-Container Docker Deployment

### Container Architecture

```yaml
multi-container-deployment:
  containers:
    - name: nginx
      purpose: "Reverse proxy, static asset serving, HTTPS termination"
      ports: ["443:443", "80:80"]  # 80 redirects to 443
      mounts: ["./nginx.conf:/etc/nginx/nginx.conf", "./certs:/etc/nginx/certs"]
      networks: ["mcp-network"]

    - name: api-backend
      purpose: "Flask REST API, business logic, orchestration"
      ports: ["5000:5000"]  # Internal only via nginx reverse proxy
      mounts:
        - "mcp-db:/app/data"          # Persistent SQLite database
        - "mcp-backups:/app/backups"  # .tbkp backup directory
      environment:
        - SCANNER_TYPE=rust           # Rust binary available in container
        - CVE_DB_PATH=/app/data/cve/  # Offline NVD snapshot directory
        - BACKUP_RETENTION_DAYS=3
      networks: ["mcp-network"]
      depends_on: ["nginx"]

    - name: scanner-daemon
      purpose: "Distributed zone scanning + continuous probing"
      image: "same as api-backend"
      command: "python -m mcp.scanner.daemon"
      mounts:
        - "mcp-db:/app/data"
        - "mcp-backups:/app/backups"
      environment:
        - SCANNER_ZONES_COUNT=48
        - ZONE_DIVISION_STRATEGY=activity-based
        - ZONE_PRIORITY_RESCAN=enabled
      networks: ["mcp-network"]
      depends_on: ["api-backend"]

  volumes:
    mcp-db:
      description: "Persistent SQLite database"
      driver: local
      paths: ["/var/lib/mcp/db"]

    mcp-backups:
      description: "Transaction backup directory (.tbkp files)"
      driver: local
      paths: ["/var/lib/mcp/backups"]

  ports:
    https: 443     # User-facing HTTPS access from LAN
    http: 80       # Redirect to HTTPS
    backend: 5000  # Internal API (not exposed)

  networks:
    mcp-network:
      driver: bridge
      subnets: ["172.20.0.0/16"]
```

---

## Frontend Architecture (React)

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  MCP Dashboard | 2026-04-04 14:32:45 UTC | Last Scan: 2h ago   │
│  Next Scan: 30m | User: admin@lab | [⚙️] [🚪]                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌──────────────┐  ┌──────────────────────────────────────────┐ │
│ │   SIDEBAR    │  │         MAIN CONTENT AREA                │ │
│ │              │  │                                          │ │
│ │ [📊 Summary] │  │  Active Servers: 247 / 255               │ │
│ │ [🖥️  Servers] │  │  Services: 32 unique                     │ │
│ │ [🔍 Services]│  │  Offline Servers: 8 (flagged)           │ │
│ │ [🔒 SSH]     │  │                                          │ │
│ │ [🗄️  Database]│  │  ┌────────────────────────────────────┐ │
│ │ [⚠️ Alerts]  │  │  │ Server Inventory Table               │ │
│ │ [📋 Scans]   │  │  │                                      │ │
│ │ [👥 Users]   │  │  │ Search: [_____________] | Filter: ▼ │ │
│ │              │  │  │                                      │ │
│ │              │  │  │ IP | Host | OS | Services | Status  │ │
│ │              │  │  │ ────────────────────────────────────│ │
│ │              │  │  │ 192.168.1.10 | web01 | Ubuntu ... │ │
│ │              │  │  │ ⏷ 192.168.1.11 | db01 | Windows... │ │
│ │              │  │  │       ├─ 3306 MySQL 5.7            │ │
│ │              │  │  │       └─ 5432 PostgreSQL 12         │ │
│ │              │  │  │                                      │ │
│ │ [Edit]       │  │  │ [Refresh] [Wipe] [Download ▼]      │ │
│ │ [Import/Exp] │  │  │                          [CSV]       │ │
│ │              │  │  │                          [JSON]      │ │
│ │              │  │  │                          [YAML]      │ │
│ │              │  │  │                          [Excel]     │ │
│ │              │  │  └────────────────────────────────────┘ │ │
│ │              │  │                                          │ │
│ └──────────────┘  └──────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key React Components

- **NavBar** — Clock, user profile, scan countdown
- **Sidebar** — Service filter buttons, quick stats
- **ServerList** — Virtualized table with export/import
- **SSHTerminal** — xterm.js with login session mgmt
- **DatabaseAdmin** — Query builder + change history + rollback
- **AlertsView** — Real-time notifications + config
- **UsersView** — User management with RBAC

---

## Browser SSH Gateway

### Session Flow

```
Browser Login → PTY Session Created → SSH to Target → Shell Access
     ↓               ↓                      ↓             ↓
User enters   paramiko client      Interactive shell   Command execution
credentials   + ptyprocess         with full I/O       via xterm.js
```

### Implementation

```python
# Flask route manages SSH session lifecycle
# Websocket handles real-time terminal I/O
# 30-minute idle timeout with auto-disconnect
# Session credentials stored only in memory
# Audit log records session start/end, not commands
```

---

## Distributed Scanning Architecture

### Zone Division Strategy (48 zones from /16)

```
/16 Network (10.0.0.0/16) → 256 x /24 subnets
  ├─ High Activity Zones (rescanned every 1 hour)
  ├─ Medium Activity Zones (rescanned every 2 hours)
  └─ Low Activity Zones (rescanned every 4 hours)

24-hour scan cycle distributes all 256 subnets across priority tiers
```

### Activity-Based Priorities

- **HIGH**: >20% server change rate → Scan every 1 hour
- **MEDIUM**: 5-20% change rate → Scan every 2 hours
- **LOW**: <5% change rate → Scan every 4 hours

---

## Database Layer & Transaction Backups

### Backup System

```
Before each write operation:
  1. Create .tbkp snapshot
  2. Record change summary
  3. Store metadata (timestamp, user, changes)
  4. Retain for 3 days
  5. Daily sync to host filesystem

Rollback: Click backup → Restore database → Create audit trail
```

### Core Tables

- **servers** — IP, hostname, OS, last scan, online status
- **ports** — Port, protocol, state, service
- **services** — Service name, version, confidence, banner
- **probes** — Probe results (HTTP headers, SSH banner, etc.)
- **scan_zones** — Zone subnet, priority, last scan, change rate
- **users** — Username, bcrypt password hash, role
- **change_log** — What changed, who changed it, when
- **database_backups** — Backup metadata, retention, rollback tracking

---

## User Authentication & Authorization

### RBAC Roles

- **admin** — Full access: servers, SSH, database, users, backups
- **scanner** — Read/write servers/services, trigger scans
- **viewer** — Read-only: servers, services, alerts, audit logs

### JWT Tokens

- Access token: 15 minutes (short-lived)
- Refresh token: 7 days (long-lived for auto-refresh)
- IP validation: Requests from outside LAN rejected
- Bcrypt passwords: 12-character minimum with salt

---

## REST API Specification (Key Endpoints)

```
POST   /api/auth/login           → Get tokens + user info
GET    /api/servers              → List all (paginated, <500ms)
GET    /api/servers/<id>         → Detail with ports/services
POST   /api/ssh/connect          → Create SSH session
GET    /api/ssh/ws/<id>          → WebSocket terminal I/O
GET    /api/db/schema            → Database schema browser
POST   /api/db/query             → Execute SELECT
POST   /api/db/rollback          → Restore from backup
GET    /api/export               → Download CSV/JSON/YAML/Excel
POST   /api/import               → Bulk load servers
GET    /api/alerts               → Recent alerts + config
GET    /api/cve/check            → Scan for CVEs
```

---

## CVE Integration & Vulnerability Detection

### Hybrid Approach

1. **Offline NVD Database** — Downloaded at startup (~500MB snapshot zip)
2. **Live API Queries** — Optional for real-time CVE updates (rate-limited)
3. **Caching** — Results stored locally to avoid re-querying

### Workflow

```
Service detected (e.g., MySQL 5.7)
   ↓ Query offline DB
Found CVEs locally → Report critical/high severity
   ↓ Not found locally?
Check live API (if enabled) → Cache new CVEs
```

---

## Alerting & Notification System

### Alert Types

- **server_offline** — Was online, now offline (HIGH severity)
- **new_service** — Unknown service detected (MEDIUM)
- **cve_discovered** — Critical CVE in detected software (CRITICAL)
- **port_opened** — New port appeared (MEDIUM)

### Delivery Channels

- Email (SMTP)
- Webhooks (custom HTTP POST)
- Slack (formatted messages)

---

## Configuration Management

### Key Config File (`mcp.yaml`)

```yaml
network:
  scan_range: "10.0.0.0/16"
  allowed_ranges: ["10.0.0.0/16", "10.1.0.0/16"]

scanning:
  zones_count: 48
  zone_division: "activity-based"
  parallel_workers: 8
  zone_scan_intervals: {high_activity: 3600, medium: 7200, low: 14400}

docker:
  backup_retention_days: 3
  backup_directory: "/app/backups"

auth:
  jwt_access_expires_minutes: 15
  jwt_refresh_expires_days: 7
  password_min_length: 12

alerts:
  enabled: true
  check_interval_minutes: 5

web:
  allowed_lans: ["10.0.0.0/16", "192.168.1.0/24"]
```

---

## Performance Targets & Optimization

### API Response Times (Target)

| Endpoint | Target |
|----------|--------|
| `GET /api/servers` | <500ms |
| `GET /api/servers/<id>` | <100ms |
| `POST /api/export` (5k records) | <2s |

### Scan Performance

- Full /16: 1-2 hours (48 parallel /24 zones)
- Single /24: 2-3 minutes (8 parallel /27 sub-zones)
- Service probe per host: <50ms

---

## Security Architecture

### Network Isolation

- Only configured IP ranges scanned (whitelist enforcement)
- LAN-only access (requests from outside LAN blocked)
- No external data transmission or cloud integration
- SSH credentials never stored (user input per-session)

### Credential Protection

- Passwords: Bcrypt hashed + salted
- JWT tokens: HS256 signed, 15-minute window
- API keys: Environment variables only
- Session credentials: Memory-only, cleared on disconnect

---

## Extension Points

### Custom Service Probes

Add new probe types by implementing `BaseProbe` class with:
- `probe_type` name
- `probe(host, port, timeout)` method
- `parse_version(data)` parser

### Custom Filters & React Views

Create React components that:
- Call `/api/services/<name>/servers` endpoint
- Filter by service, display custom metrics
- Add to sidebar via component registry

---

## Deployment Checklist

- [ ] Configure network scan ranges in `mcp.yaml`
- [ ] Generate TLS certificate for Nginx
- [ ] Create Docker volumes for persistent data
- [ ] Set up initial admin user
- [ ] Test IP whitelist enforcement
- [ ] Verify no external network access
- [ ] Configure alerts (email, webhooks)
- [ ] Download offline CVE NVD database
- [ ] Test SSH gateway with target server
- [ ] Configure backup sync to host
- [ ] Enable audit logging
- [ ] Document network topology

---

**End of Architectural Document v2.0**
