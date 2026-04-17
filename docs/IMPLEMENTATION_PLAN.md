# Master Control Program (MCP) - Implementation Roadmap

**Status:** Active  
**Last Updated:** March 31, 2026  
**Project Goal:** Build a self-contained, local-only network management dashboard that maps a sandbox network, identifies servers and services, and displays everything in a clean Nginx-hosted UI.

---

## Problem Frame & Scope

### The Problem
The user needs visibility into a local, isolated sandbox network without:
- Scanning external networks or public IPs
- Transmitting data to cloud services
- Exposing the dashboard externally
- Manual server cataloging

### Success Criteria
- ✅ Discover all active hosts within a predefined IP range
- ✅ Identify open ports and running services
- ✅ Store metadata in a persistent local database
- ✅ Provide a responsive web dashboard for viewing and managing the inventory
- ✅ Support automatic service categorization via sidebar menu
- ✅ Allow scheduled rescans with automatic database merging
- ✅ Support optional service probing for deeper metadata collection

### Scope Boundaries
- **Included:** Local scanning, SQLite DB, Nginx dashboard, service probing, scheduling
- **Excluded:** Advanced penetration testing, exploit execution, cloud integration, remote access
- **Security Constraint:** Everything runs locally; no external network access allowed

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│          Master Control Program (MCP)               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐      ┌─────────────────┐        │
│  │ CLI Interface│─────→│ Scheduler Module│        │
│  └──────────────┘      └────────┬────────┘        │
│                                 │                  │
│  ┌──────────────────────────────▼─────┐           │
│  │  Network Scanning Engine (nmap)    │           │
│  │  - Host discovery                  │           │
│  │  - Port enumeration                │           │
│  │  - OS fingerprinting               │           │
│  │  - Service version detection       │           │
│  └──────────────────┬──────────────────┘           │
│                     │                              │
│  ┌──────────────────▼──────────────────┐           │
│  │  Service Probing Module             │           │
│  │  - HTTP headers, SSH banner         │           │
│  │  - SQL handshake, SMB info, RDP     │           │
│  └──────────────────┬──────────────────┘           │
│                     │                              │
│  ┌──────────────────▼──────────────────┐           │
│  │  Database Layer (SQLite)            │           │
│  │  - servers, ports, services, probes │           │
│  │  - merge logic for rescans          │           │
│  │  - user notes & labels              │           │
│  └──────────────────┬──────────────────┘           │
│                     │                              │
│  ┌──────────────────▼──────────────────┐           │
│  │  Web API (REST endpoints)           │           │
│  │  - /servers, /services, /probes     │           │
│  │  - /scan (trigger), /status         │           │
│  └──────────────────┬──────────────────┘           │
│                     │                              │
│  ┌──────────────────▼──────────────────┐           │
│  │  Nginx + Web Dashboard              │           │
│  │  - Server table + filtering         │           │
│  │  - Service sidebar + autocomplete   │           │
│  │  - Edit notes & labels              │           │
│  │  - Real-time updates                │           │
│  └──────────────────────────────────────┘           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation & Core Infrastructure
**Duration:** 1-2 weeks  
**Goal:** Set up project structure, database, and basic scanning

#### 1.1 Project Scaffolding & Configuration
- **Objective:** Initialize the project with all baseline dependencies and configuration
- **Tasks:**
  - Choose tech stack (Python + Flask for backend recommended for portability)
  - Initialize project structure with separate modules: `scanner/`, `db/`, `api/`, `ui/`, `probes/`, `scheduler/`
  - Create `config.py` for user-configurable IP ranges (whitelist format: e.g., `10.0.0.0/8`, `192.168.1.0/24`)
  - Set up `requirements.txt` with dependencies: Flask, nmap-python, APScheduler, Jinja2
  - Create startup script that validates config before running
- **Files to Create:**
  - `config.py` — Configuration loader & validator
  - `requirements.txt` — Python dependencies
  - `main.py` — Application entry point
  - `Makefile` or `run.sh` — Quick startup commands
- **Test Scenarios:**
  - ✅ Application starts without errors
  - ✅ Config file is validation (IP ranges are valid CIDR)
  - ✅ Required directories exist

#### 1.2 SQLite Database Schema & ORM Layer
- **Objective:** Design and implement the persistence layer
- **Tables:**
  - `servers` — id, ip, hostname, os, os_version, last_scan, created_at
  - `ports` — id, server_id, port_number, state (open/closed/filtered), protocol (tcp/udp), last_scan
  - `services` — id, port_id, service_name, version, banner, confidence, last_scan
  - `probes` — id, service_id, probe_type (http_headers, ssh_banner, sql_version, smb_info, rdp_info), data (JSON), timestamp
  - `scan_jobs` — id, scan_id, start_time, end_time, status, results_summary
  - `user_notes` — id, server_id, note_text, label, updated_at
- **Tasks:**
  - Design schema with proper indexing on frequently queried fields (ip, service_name, port_number)
  - Implement ORM models using SQLAlchemy (if Python) or raw SQL with migration system
  - Add conflict-safe merge logic for rescans (update existing records, ignore duplicates)
  - Implement database initialization script
- **Files to Create:**
  - `db/schema.py` — Table definitions & schema initialization
  - `db/models.py` — ORM models
  - `db/merge.py` — Rescan merge logic
  - `db/migrations/` — Version control for schema changes (optional but recommended)
- **Test Scenarios:**
  - ✅ Database initializes correctly
  - ✅ Records can be created, updated, deleted
  - ✅ Merge logic preserves user notes during rescans
  - ✅ Duplicate service entries are not created on rescan

---

### Phase 2: Network Scanning Engine
**Duration:** 1-2 weeks  
**Goal:** Implement robust host and service discovery

#### 2.1 Nmap Integration & Scanning Module
- **Objective:** Build a safe, local-only scanning wrapper around nmap
- **Tasks:**
  - Create `scanner/nmap_wrapper.py` to wrap nmap subprocess calls
  - Implement scanning for allowed IP ranges only (validate against whitelist)
  - Parse nmap XML output into structured JSON
  - Handle incomplete/inconsistent results gracefully (e.g., OS detection fails but ports succeed)
  - Implement timeout handling (60-300 seconds per scan, configurable)
  - Log all scan activities for auditability
- **Key Functions:**
  - `validate_target_range(range)` — Verify range is in whitelist
  - `run_host_discovery_scan(range)` — `-sn` (ping sweep)
  - `run_port_scan(host, ports)` — `-sV` (service version detection)
  - `run_os_detection_scan(host)` — `-O` (OS fingerprinting)
  - `parse_nmap_xml(xml_data)` — Convert output to JSON
- **Files to Create:**
  - `scanner/nmap_wrapper.py` — Nmap CLI interface
  - `scanner/parser.py` — XML parsing & validation
  - `scanner/validator.py` — IP range & target validation
- **Test Scenarios:**
  - ✅ Scanner rejects targets outside the whitelist
  - ✅ Valid IP ranges are accepted and scanned
  - ✅ Nmap XML output is parsed correctly
  - ✅ Incomplete results (e.g., missing OS) don't crash the system
  - ✅ Timeouts are handled gracefully

#### 2.2 Scan Orchestration & Result Storage
- **Objective:** Execute scans and atomically store results in the database
- **Tasks:**
  - Create orchestrator that chains: host discovery → port scan → OS detection
  - Implement transactional database writes (all-or-nothing per scan)
  - Store scan metadata: start time, end time, results summary
  - Deduplicate results against existing database records
  - Log errors and partial failures without stopping the entire scan
- **Files to Create:**
  - `scanner/orchestrator.py` — Scan workflow coordination
  - `scanner/storage.py` — Atomic database writes & merge
- **Test Scenarios:**
  - ✅ Scan results are stored atomically
  - ✅ Duplicate rescans don't create duplicate records
  - ✅ Partial scan failures are logged and don't corrupt the database
  - ✅ User notes are preserved during rescan merges

---

### Phase 3: Service Probing Module
**Duration:** 1-2 weeks  
**Goal:** Gather deeper metadata from detected services

#### 3.1 Service-Specific Probing Logic
- **Objective:** Implement optional probing for common services
- **Probe Types to Support:**
  - **HTTP/HTTPS:** Fetch headers, detect web server type, grab banner
  - **SSH:** Connect and retrieve SSH banner (version, algorithm support)
  - **SQL (MySQL, MSSQL, PostgreSQL):** Attempt handshake, extract version
  - **SMB:** Query share information, OS version
  - **RDP:** Attempt TLS negotiation, extract version
- **Tasks:**
  - Create individual probe modules for each service type
  - Implement connection pooling & timeout handling (5-30 second timeouts per probe)
  - Graceful failure modes (probe timeout ≠ service offline)
  - Obfuscate or redact sensitive data (e.g., banner information that reveals exploits)
  - Log all probes for audit trail
- **Files to Create:**
  - `probes/http_probe.py` — HTTP/HTTPS header grabbing
  - `probes/ssh_probe.py` — SSH banner collection
  - `probes/sql_probe.py` — SQL handshake parsing
  - `probes/smb_probe.py` — SMB enumeration
  - `probes/rdp_probe.py` — RDP negotiation
  - `probes/base.py` — Common probe interface & utilities
- **Test Scenarios:**
  - ✅ HTTP probe retrieves server headers
  - ✅ SSH probe captures banner without logging in
  - ✅ SQL probe detects version without querying databases
  - ✅ All probes timeout gracefully after N seconds
  - ✅ Probe failures don't crash the scanner

#### 3.2 Probe Orchestration & Storage
- **Objective:** Trigger probes for detected services and store results
- **Tasks:**
  - Implement probe scheduler that runs after scans
  - For each discovered service, spawn appropriate probe
  - Store probe results in `probes` table with timestamp
  - Allow manual trigger and batch re-probe
  - Implement probe status tracking (pending, in-progress, completed, failed)
- **Files to Create:**
  - `probes/orchestrator.py` — Probe workflow & scheduling
  - API endpoint to trigger re-probes
- **Test Scenarios:**
  - ✅ Probes trigger automatically after scan
  - ✅ Probe results are stored correctly
  - ✅ Manual re-probe can be triggered via API
  - ✅ Probe failures don't block future scans

---

### Phase 4: REST API & Backend Services
**Duration:** 1-2 weeks  
**Goal:** Expose database and scanning functionality via REST API

#### 4.1 REST API Endpoints
- **Objective:** Create endpoints for dashboard and CLI access
- **Endpoints:**
  - `GET /api/servers` — List all servers (with filtering, sorting, pagination)
  - `GET /api/servers/<id>` — Server detail (ports, services, probes, notes)
  - `GET /api/services` — List unique services detected
  - `GET /api/services/<name>` — Servers running a specific service
  - `POST /api/scan` — Trigger a scan immediately
  - `GET /api/scan/status` — Current scan status
  - `GET /api/scan/history` — Past scan results
  - `POST /api/servers/<id>/notes` — Add/update user notes
  - `POST /api/servers/<id>/label` — Assign labels
  - `GET /api/dashboard/summary` — Overall network statistics
- **Tasks:**
  - Implement Flask routes for all endpoints
  - Add request validation (IP ranges, filtering params)
  - Implement response pagination (default 100 items, max 1000)
  - Add CORS headers if UI is on different port
  - Implement error handling with proper HTTP status codes
  - Add request logging for audit trail
- **Files to Create:**
  - `api/app.py` — Flask application initialization
  - `api/routes/servers.py` — `/servers` endpoints
  - `api/routes/services.py` — `/services` endpoints
  - `api/routes/scans.py` — `/scan` endpoints
  - `api/routes/dashboard.py` — `/dashboard` endpoints
  - `api/middleware.py` — Auth, logging, error handling
- **Test Scenarios:**
  - ✅ GET /servers returns paginated list
  - ✅ POST /scan triggers a scan and returns job ID
  - ✅ GET /services groups servers by service type
  - ✅ POST /servers/{id}/notes saves user data
  - ✅ Filtering by service name returns correct results
  - ✅ Invalid pagination params are rejected

#### 4.2 Authentication & Access Control
- **Objective:** Restrict API access to local machine/LAN only
- **Tasks:**
  - Implement IP-based access control (whitelist local IPs, LAN CIDR)
  - Optional: Simple token-based auth for convenience (no exposed secrets)
  - Log all access attempts
  - Return 403 Forbidden for unauthorized IPs
- **Files to Create:**
  - `api/auth.py` — IP validation & token handling
- **Test Scenarios:**
  - ✅ Requests from 127.0.0.1 are allowed
  - ✅ Requests from LAN are allowed
  - ✅ Requests from unknown IPs are rejected with 403
  - ✅ Access attempts are logged

---

### Phase 5: Web Dashboard (Nginx + Frontend)
**Duration:** 2-3 weeks  
**Goal:** Build a responsive, user-friendly interface

#### 5.1 Nginx Configuration & Static Serving
- **Objective:** Set up Nginx as the frontend server
- **Tasks:**
  - Create Nginx config that:
    - Listens on localhost:8080 or configurable port
    - Proxies `/api/*` to Flask backend
    - Serves static HTML/CSS/JS files
    - Compresses responses (gzip)
    - Sets security headers (X-Frame-Options, CSP)
    - Restricts access to local IPs only
  - Create self-signed SSL certificate for HTTPS (optional but recommended)
- **Files to Create:**
  - `nginx/nginx.conf` — Nginx configuration
  - `nginx/ssl/` — SSL certificates (if using HTTPS)
- **Test Scenarios:**
  - ✅ Nginx serves HTML files
  - ✅ API requests are proxied to Flask
  - ✅ Gzip compression works
  - ✅ SSL cert is valid (if using HTTPS)

#### 5.2 Frontend UI - Server Table & Search
- **Objective:** Display discovered servers with visualization and filtering
- **Features:**
  - Table displaying all servers: IP, hostname, OS, last scan, actions
  - Expandable rows showing: ports, services, versions, probes, notes
  - Search/filter by IP, hostname, OS, service name, port
  - Sort by IP, last scan time, OS
  - Pagination (50 rows per page)
  - Edit-in-place for user notes and labels
  - Quick actions: view details, assign label, trigger re-probe
- **Tech Stack:** HTML5, CSS3, Vanilla JavaScript (or lightweight Vue/React if preferred)
- **Tasks:**
  - Design clean, responsive layout (mobile-friendly)
  - Implement table pagination
  - Add search/filter logic (client-side or API-side)
  - Implement expandable rows with port/service details
  - Add inline editing for notes
  - Implement real-time updates (poll API every 30 seconds or WebSocket)
- **Files to Create:**
  - `ui/index.html` — Main dashboard page
  - `ui/css/style.css` — Styling
  - `ui/js/app.js` — Core application logic
  - `ui/js/api-client.js` — API wrapper
  - `ui/js/table.js` — Table rendering & interaction
- **Test Scenarios:**
  - ✅ Table displays all servers
  - ✅ Search filters results correctly
  - ✅ Expandable rows show port/service details
  - ✅ Edit notes locally and save via API
  - ✅ Page remains responsive with 100+ servers

#### 5.3 Frontend UI - Service Sidebar & Navigation
- **Objective:** Auto-generate sidebar menu from discovered services for quick filtering
- **Features:**
  - Left sidebar showing unique service names (sorted alphabetically)
  - Service button showing count of servers running it
  - Clicking service filters main table to that service only
  - "All Services" button to reset filter
  - Sidebar updates after each scan
  - Collapsible service categories (optional: group by type like "Web Servers", "Databases")
- **Tasks:**
  - Add sidebar HTML structure
  - Implement service list fetching from API
  - Add click handlers to filter main table
  - Auto-refresh service list after scan completion
  - Add visual indicator for active filter
- **Files to Create:**
  - `ui/js/sidebar.js` — Service sidebar logic
- **Test Scenarios:**
  - ✅ Sidebar displays all unique services
  - ✅ Clicking service filters table correctly
  - ✅ Service counts are accurate
  - ✅ Sidebar updates after scan

#### 5.4 Frontend UI - Dashboard Statistics & Status
- **Objective:** Provide at-a-glance network overview
- **Features:**
  - Total servers, online/offline count
  - Top 5 most common services
  - Last scan time and next scheduled scan
  - Scan job queue and status
  - System health indicators (disk space, DB size)
- **Tasks:**
  - Add stats dashboard section
  - Fetch data from `/api/dashboard/summary`
  - Update stats in real-time
- **Test Scenarios:**
  - ✅ Stats display correctly
  - ✅ Stats update after scan

---

### Phase 6: Scheduling & Automation
**Duration:** 1 week  
**Goal:** Implement background scanning and automatic updates

#### 6.1 Scan Scheduler
- **Objective:** Execute rescans on a schedule without user intervention
- **Tasks:**
  - Use APScheduler (Python) or similar
  - Implement configurable scan schedules: hourly, daily, weekly, custom cron
  - Prevent concurrent scans (queue if a scan is already running)
  - Notify dashboard of scan start/end via WebSocket or polling
  - Store scan job records for history
  - Implement scan retry logic (if scan fails, retry up to 3 times with exponential backoff)
- **Configuration:**
  - `config.py` should include: `SCAN_INTERVAL` (e.g., 3600 seconds for hourly)
  - CLI option: `--scan-interval <seconds>`
  - UI option: Configure schedule from dashboard
- **Files to Create:**
  - `scheduler/scheduler.py` — APScheduler integration
  - `scheduler/jobs.py` — Scan job definitions
- **Test Scenarios:**
  - ✅ Scheduler triggers scans at configured interval
  - ✅ Concurrent scans are prevented
  - ✅ Scan failures are retried
  - ✅ Dashboard shows scan status in real-time

#### 6.2 Automatic Service Probing
- **Objective:** Run probes automatically after each scan
- **Tasks:**
  - Trigger probe orchestrator automatically after scan completion
  - For new services, spawn appropriate probes
  - For known services, only re-probe if data is > N days old
  - Store probe results and update dashboard
- **Files to Create:**
  - Updates to `probes/orchestrator.py`
- **Test Scenarios:**
  - ✅ Probes trigger automatically after scan
  - ✅ Probes are cached and don't re-run unnecessarily

#### 6.3 Dashboard UI Updates
- **Objective:** Show live scan and probe status
- **Tasks:**
  - Implement last scan timestamp and countdown to next scan
  - Show active probe jobs
  - Add "Scan Now" button for manual trigger
  - Implement WebSocket or polling for real-time updates
- **Test Scenarios:**
  - ✅ Dashboard shows scan status in real-time
  - ✅ "Scan Now" button triggers immediate scan

---

### Phase 7: Testing, Documentation & Hardening
**Duration:** 2 weeks  
**Goal:** Ensure reliability, security, and maintainability

#### 7.1 Unit & Integration Testing
- **Objective:** Comprehensive test coverage for all modules
- **Test Strategy:**
  - **Unit Tests:** Database models, nmap parser, probe modules, API routes
  - **Integration Tests:** End-to-end scan workflow, database merge logic, API + DB interactions
  - **Edge Cases:** Empty networks, timeouts, malformed nmap output, concurrent scans
- **Tools:** pytest (Python)
- **Coverage Goal:** Minimum 80% line coverage
- **Files to Create:**
  - `tests/test_scanner.py` — Nmap wrapper & parser tests
  - `tests/test_db.py` — Database & merge logic tests
  - `tests/test_probes.py` — Probe module tests
  - `tests/test_api.py` — REST API endpoint tests
  - `tests/test_scheduler.py` — Scheduler tests
  - `tests/fixtures/` — Mock nmap XML, test data
- **Test Scenarios:**
  - All scenarios from previous phases formalized as tests

#### 7.2 Documentation
- **Objective:** Comprehensive docs for deployment and usage
- **Files to Create:**
  - `README.md` — Project overview, quick start, architecture
  - `SETUP.md` — Installation, configuration, dependencies
  - `API_SPEC.md` — REST API documentation (paths, request/response examples)
  - `USER_GUIDE.md` — How to use the dashboard
  - `DEV_GUIDE.md` — Architecture, how to extend probes/modules
  - `SECURITY.md` — Security model, threat analysis, limitations
- **Documentation Should Cover:**
  - System architecture & module overview
  - Configuration options & defaults
  - How to add custom probes
  - How to whitelist IP ranges
  - Troubleshooting common issues
  - Performance tuning tips

#### 7.3 Security Hardening
- **Objective:** Harden against common vulnerabilities
- **Tasks:**
  - Validate all user inputs (IP ranges, filter params)
  - Sanitize output to prevent XSS in dashboard
  - Add CSRF protection to form submissions
  - Implement rate limiting on API endpoints
  - Ensure database queries use parameterized statements (prevent SQL injection)
  - Set secure HTTP headers (CSP, X-Frame-Options, X-Content-Type-Options)
  - Document security model and known limitations
- **Files to Create/Update:**
  - `api/middleware.py` — Input validation, rate limiting
  - `SECURITY.md` — Security documentation
- **Test Scenarios:**
  - ✅ SQL injection attempts are blocked
  - ✅ XSS payloads are escaped
  - ✅ CSRF tokens are validated
  - ✅ Rate limits are enforced

#### 7.4 Deployment & Operations
- **Objective:** Provide production-ready deployment setup
- **Tasks:**
  - Create Docker image (optional but recommended)
  - Create systemd service file (if deploying on Linux)
  - Create startup script with health checks
  - Document backup strategy for SQLite DB
  - Document log rotation
  - Provide monitoring/alerting setup (optional)
- **Files to Create:**
  - `Dockerfile` — Container image definition
  - `docker-compose.yml` — Multi-container orchestration (optional)
  - `deploy/mcp.service` — Systemd service file
  - `deploy/start.sh` — Startup script
  - `deploy/backup.sh` — Database backup script
- **Test Scenarios:**
  - ✅ Docker image builds and runs
  - ✅ Systemd service starts/stops correctly
  - ✅ Backup script creates valid database backups

---

## Dependencies & Sequencing

### Critical Path
1. **Phase 1** (Foundation) → Must complete before anything else
2. **Phase 2** (Scanning) → Prerequisite for getting any data
3. **Phase 3** (Probing) → Optional but valuable; can be added after Phase 2
4. **Phase 4** (API) → Required for Phase 5 to function
5. **Phase 5** (Dashboard) → Most user-facing; parallelizable with Phase 3
6. **Phase 6** (Automation) → Can be added incrementally after Phase 2
7. **Phase 7** (Testing & Docs) → Should be distributed throughout; final pass before release

### Potential Parallelization
- Phase 3 (Probing) can be developed in parallel with Phase 4 (API)
- Phase 5 (Dashboard) can start once Phase 4 API is at 50% complete
- Phase 6 (Scheduling) can start after Phase 2 basic scanning works

### Dependencies Matrix
```
Phase 1 (Foundation)
    ↓
Phase 2 (Scanning) ──→ Phase 4 (API) ──→ Phase 5 (Dashboard)
    ├──→ Phase 3 (Probing) ─────┘
    └──→ Phase 6 (Automation)
         ↓
    Phase 7 (Testing & Ops)
```

---

## External Dependencies & Tools

### Required Tools
- **nmap** — Network scanning engine (must be installed on system)
- **Python 3.8+** — Backend runtime
- **SQLite3** — Database (built into Python)
- **Nginx** — Web server for dashboard
- **Node.js (optional)** — For frontend build tools (minification, bundling)

### Python Packages
- **Flask** — Web framework
- **SQLAlchemy** — ORM
- **APScheduler** — Background job scheduling
- **python-nmap** — Nmap Python bindings
- **requests** — HTTP client for probing
- **pytest** — Testing framework
- **pytest-cov** — Code coverage

### Optional Tools
- **Docker** — Containerization for easy deployment
- **Redis** — Optional caching layer for frequent queries
- **Prometheus** — Optional metrics collection

---

## Known Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Nmap not installed on system | Blocker | Document installation steps; fail fast with clear error message |
| Large networks (1000+ hosts) | Performance | Implement pagination, caching, async scanning, consider scan batching |
| Duplicate/conflicting data on rescan | Data quality | Implement merge logic that preserves user notes; validate constraints |
| Probes timeout frequently | User experience | Make probes async; allow skipping failed probes; retry with backoff |
| SQL injection via user input | Security | Use parameterized queries; validate all input; sanitize output |
| Unauthorized access to dashboard | Security | Implement IP-based access control; document in SECURITY.md |
| Database corruption | Availability | Implement transaction management; provide backup/restore tools |
| Scan interferes with network | Operational | Document safe scan settings; use low aggression levels; provide pause/resume |

---

## Success Metrics

- ✅ Scanner discovers 100% of hosts in test range within 5 minutes
- ✅ Dashboard loads in <2 seconds with 100+ servers
- ✅ Service probing detects correct versions for 95%+ of services
- ✅ Database merge logic preserves user notes during rescans
- ✅ Scheduled scans run reliably every N hours without manual intervention
- ✅ API response times <1s for all endpoints with <1000 servers
- ✅ Zero data corruption across 100+ scan cycles
- ✅ Deploy and run successfully with provided Docker/scripts

---

## Next Steps

1. **Validate Architecture** — Review this plan with stakeholders; adjust if needed
2. **Set Up Phase 1** — Initialize project structure and dependencies
3. **Begin Phase 2** — Implement nmap scanning wrapper and database layer
4. **Iterate & Test** — Complete phases in order; test continuously
5. **Document & Deploy** — Complete Phase 7 with full documentation and deployment scripts

---

## Questions for Clarification (Before Starting)

- [ ] What is the expected network size? (number of hosts)
- [ ] What is the maximum scan frequency? (hourly, daily, weekly?)
- [ ] Should the system support multiple users or just local access?
- [ ] Are there specific services you want to probe for? (HTTP, SSH, SQL, SMB, RDP, others?)
- [ ] Do you need historical trending (e.g., service uptime over time)?
- [ ] Should the dashboard be mobile-responsive?
- [ ] Do you have preferences on tech stack (Python, Node, Go, etc.)?
- [ ] Should this support Docker deployment?
