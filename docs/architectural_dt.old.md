# Master Control Program (MCP) - Architectural Details

**Version:** 1.0  
**Date:** April 4, 2026  
**Status:** Active Design Document  

This document provides deep technical architecture for the MCP system, including component relationships, data flows, database schemas, API specifications, and integration patterns.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Component Interaction Model](#component-interaction-model)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Database Schema & Relationships](#database-schema--relationships)
5. [Module Structure & Dependencies](#module-structure--dependencies)
6. [REST API Specification](#rest-api-specification)
7. [Configuration Management](#configuration-management)
8. [Error Handling & Recovery](#error-handling--recovery)
9. [Scalability & Performance](#scalability--performance)
10. [Security Architecture](#security-architecture)
11. [Extension Points & Customization](#extension-points--customization)

---

## System Architecture

### High-Level System Decomposition

```
┌────────────────────────────────────────────────────────────────┐
│                    MCP System Boundary                         │
│                   (Local, Air-Gapped Network)                  │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │             User & External Interfaces                 │   │
│  ├────────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │  ┌──────────────────┐    ┌──────────────────────┐    │   │
│  │  │  Web Dashboard   │    │   CLI Tools          │    │   │
│  │  │  (Nginx HTTPS)   │    │   (Python scripts)   │    │   │
│  │  └────────┬─────────┘    └──────────┬───────────┘    │   │
│  │           │                        │                 │   │
│  └───────────┼────────────────────────┼─────────────────┘   │
│              │                        │                     │
│              │ HTTP/JSON              │ CLI/JSON            │
│              │                        │                     │
│  ┌───────────▼────────────────────────▼─────────────────┐   │
│  │        REST API Layer (Flask)                       │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │  Auth & IP Validation Middleware           │    │   │
│  │  │  Logging & Request Tracing                 │    │   │
│  │  │  Error Handling & Rate Limiting            │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  │                                                      │   │
│  │  Routes:                                            │   │
│  │  • /api/servers/*, /api/services/*, etc.           │   │
│  └──────────────────────┬─────────────────────────────┘   │
│                         │                                 │
│  ┌──────────────────────▼─────────────────────────────┐   │
│  │       Business Logic Layer                        │   │
│  │  ┌─────────────┐ ┌──────────────┐ ┌────────────┐  │   │
│  │  │  Scan       │ │  Probe       │ │ Scheduler  │  │   │
│  │  │  Orchestr.  │ │  Orchestr.   │ │ & Jobs     │  │   │
│  │  └─────────────┘ └──────────────┘ └────────────┘  │   │
│  │                                                    │   │
│  └──────────────────────┬─────────────────────────────┘   │
│                         │                                 │
│  ┌──────────────────────▼─────────────────────────────┐   │
│  │       Data & Integration Layer                    │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │   │
│  │  │ SQLite   │ │  Nmap    │ │ Probe Modules    │   │   │
│  │  │ Database │ │ Wrapper  │ │ (SSH, HTTP, etc) │   │   │
│  │  └──────────┘ └──────────┘ └──────────────────┘   │   │
│  │                                                    │   │
│  └──────────────────────┬─────────────────────────────┘   │
│                         │                                 │
│  ┌──────────────────────▼─────────────────────────────┐   │
│  │    External System Calls (System Boundary)        │   │
│  │  ┌──────────┐ ┌──────────────────────────────┐    │   │
│  │  │ nmap CLI │ │ Network Sockets              │    │   │
│  │  │ (subprocess)│ (Probe connections)         │    │   │
│  │  └──────────┘ └──────────────────────────────┘    │   │
│  │                                                    │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
└────────────────────────────────────────────────────────────┘
         ↓
         └─→ Sandbox Network (IP Range: user-configured)
              /24, /16, etc. — Isolated Lab/Sandbox Only
```

### Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Presentation Layer                                     │
│  ├─ Web Dashboard (HTML/CSS/JS)                         │
│  └─ CLI & API Consumers                                 │
├─────────────────────────────────────────────────────────┤
│  API Layer                                              │
│  ├─ REST Endpoints (/api/servers, /api/services, etc)  │
│  ├─ Request Validation & Auth                          │
│  └─ Response Formatting & Error Handling               │
├─────────────────────────────────────────────────────────┤
│  Business Logic Layer                                   │
│  ├─ Scan Orchestration                                 │
│  ├─ Service Probe Orchestration                        │
│  ├─ Scheduling & Background Jobs                       │
│  └─ Data Merge & Conflict Resolution                   │
├─────────────────────────────────────────────────────────┤
│  Data Access Layer (DAO/Repository Pattern)            │
│  ├─ ORM Models (SQLAlchemy)                            │
│  ├─ Database Queries                                   │
│  ├─ Transactional Management                           │
│  └─ Connection Pooling                                 │
├─────────────────────────────────────────────────────────┤
│  System Integration Layer                               │
│  ├─ Nmap Wrapper & Parser                              │
│  ├─ Probe Modules (SSH, HTTP, SQL, SMB, RDP)          │
│  └─ External Tool Management                           │
├─────────────────────────────────────────────────────────┤
│  Data Layer (Persistence)                               │
│  └─ SQLite Database                                     │
└─────────────────────────────────────────────────────────┘
```

---

## Component Interaction Model

### Core Components

#### 1. **Scan Engine**
- **Purpose:** Discover hosts and services in the sandbox network
- **Inputs:** IP range whitelist (config), number of parallel threads
- **Outputs:** Structured scan results (JSON)
- **External Dependencies:** nmap CLI
- **Interface:** 
  - `ScanEngine.validate_target_range(range: str) → bool`
  - `ScanEngine.discover_hosts(range: str) → List[Host]`
  - `ScanEngine.scan_ports(host: str, ports: List[int]) → List[Port]`
  - `ScanEngine.detect_os(host: str) → OSInfo`

#### 2. **Probe Orchestrator**
- **Purpose:** Gather service-specific metadata
- **Inputs:** Discovered services (from database)
- **Outputs:** Structured probe results (JSON)
- **External Dependencies:** Network sockets (SSH, HTTP, SQL, SMB, RDP)
- **Interface:**
  - `ProbeOrchestrator.get_probe_for_service(service: str) → BaseProbe`
  - `ProbeOrchestrator.run_probe(host: str, port: int, service: str) → ProbeResult`
  - `ProbeOrchestrator.probe_batch(services: List[Service]) → List[ProbeResult]`

#### 3. **Database Layer (ORM)**
- **Purpose:** Persist and retrieve network inventory
- **Interface:**
  - `ServerDAO.create(ip, hostname, os) → Server`
  - `ServerDAO.find_by_ip(ip: str) → Server`
  - `ServerDAO.find_all(filter, sort, limit) → List[Server]`
  - `ServiceDAO.find_by_name(service: str) → List[Services]`
  - `MergeStrategy.merge_rescan_results(old_data, new_data) → MergedData`

#### 4. **Scheduler**
- **Purpose:** Coordinate automatic scanning and probing
- **Inputs:** Configuration (interval, cron expression)
- **Outputs:** Job execution events, status updates
- **Interface:**
  - `Scheduler.schedule_scan(interval: int)`
  - `Scheduler.trigger_immediate_scan()`
  - `Scheduler.get_job_status() → JobStatus`
  - `Scheduler.on_scan_complete(callback: Callable)`

#### 5. **REST API**
- **Purpose:** Expose all functionality via HTTP
- **Inputs:** HTTP requests (GET, POST, PUT, DELETE)
- **Outputs:** JSON responses
- **Interface:** Detailed in [REST API Specification](#rest-api-specification)

#### 6. **Web Dashboard**
- **Purpose:** User-friendly interface for visualization and management
- **Technologies:** HTML5, CSS3, Vanilla JavaScript
- **Features:** See [Web Dashboard](#web-dashboard) section

### Component Communication

```
User Interface (Web/CLI)
    ↓
REST API Layer
    │
    ├→ Auth Middleware (IP validation)
    ├→ Request Validation
    └→ Route Handler
         ↓
    Business Logic Layer
         ├→ Scan Orchestrator
         │   ├→ Nmap Wrapper (subprocess)
         │   ├→ Parser (XML → JSON)
         │   └→ Database DAO (persist results)
         │
         ├→ Probe Orchestrator
         │   ├→ Probe Modules (SSH, HTTP, etc)
         │   └→ Database DAO (persist probe data)
         │
         ├→ Scheduler
         │   ├→ APScheduler (background jobs)
         │   └→ Callbacks to Scan/Probe Orchestrators
         │
         └→ Dashboard Service
             ├→ Database DAO (read queries)
             └→ Aggregation & Formatting

Response
    ↓
JSON Response
    ↓
Frontend Rendering
```

---

## Data Flow Diagrams

### Scan Workflow

```
┌─────────────────────────────────┐
│ User Triggers Scan              │
│ (Manual or Scheduled)           │
└──────────────┬──────────────────┘
               │
               ▼
        ┌─────────────────┐
        │ Validate Config │
        │ (IP whitelist)  │
        └────────┬────────┘
                 │
                 ▼
        ┌──────────────────────────┐
        │ Run Nmap Host Discovery  │
        │ (SYN ping sweep, -sn)    │
        └────────┬─────────────────┘
                 │
                 ├─ Timeout/Error?
                 │  └─→ Log & Retry (3x)
                 │
                 ▼
        ┌──────────────────────────┐
        │ Parse Nmap XML Results   │
        │ Extract: IP, MAC, state  │
        └────────┬─────────────────┘
                 │
                 ▼
        ┌──────────────────────────┐
        │ For Each Live Host:      │
        │ Run Port Scan (-sV)      │
        └────────┬─────────────────┘
                 │
                 ├─ Timeout/Error?
                 │  └─→ Mark partial, continue
                 │
                 ▼
        ┌──────────────────────────┐
        │ Extract Port/Service Info│
        │ Merge with nmap output   │
        └────────┬─────────────────┘
                 │
                 ▼
        ┌──────────────────────────┐
        │ For Selected Hosts:      │
        │ Run OS Detection (-O)    │
        └────────┬─────────────────┘
                 │
                 ▼
        ┌──────────────────────────┐
        │ Database Transaction:    │
        │ - Merge with old data    │
        │ - Preserve user notes    │
        │ - Insert/update records  │
        │ - Commit atomically      │
        └────────┬─────────────────┘
                 │
                 ├─ Success?
                 │  └─→ Trigger probes
                 │
                 └─→ Failure?
                    └─→ Rollback & Log

        ┌──────────────────────────┐
        │ Update Dashboard:        │
        │ - Notify via WebSocket   │
        │ - Update UI statistics   │
        │ - Refresh service sidebar│
        └──────────────────────────┘
```

### Probe Workflow

```
┌──────────────────────────────────────┐
│ Scan Complete (Automatic or Manual)  │
└──────────────┬───────────────────────┘
               │
               ▼
        ┌────────────────────────────┐
        │ Get All New/Updated        │
        │ Services from DB           │
        └────────┬───────────────────┘
                 │
                 ▼
        ┌────────────────────────────┐
        │ For Each Service:          │
        │ Map Service → Probe Type   │
        │ (HTTP→http_probe, etc)     │
        └────────┬───────────────────┘
                 │
                 ▼
        ┌────────────────────────────┐
        │ Queue Probe Jobs           │
        │ (Async, max N concurrent)  │
        └────────┬───────────────────┘
                 │
                 ├─→ HTTP Probe
                 │   ├─ Connect to :80, :443, :8080, etc
                 │   ├─ Send HTTP GET /
                 │   ├─ Capture response headers
                 │   └─ Extract: Server, X-Powered-By, etc
                 │
                 ├─→ SSH Probe
                 │   ├─ Connect to :22
                 │   ├─ Capture SSH banner
                 │   └─ Extract: version, key exchange methods
                 │
                 ├─→ SQL Probe (MySQL, MSSQL, PostgreSQL)
                 │   ├─ Connect to port
                 │   ├─ Attempt handshake
                 │   └─ Extract: server version, auth methods
                 │
                 ├─→ SMB Probe
                 │   ├─ Connect to :445, :139
                 │   ├─ Query NetBIOS info
                 │   └─ Extract: OS, workgroup, shares
                 │
                 └─→ RDP Probe
                     ├─ Connect to :3389
                     ├─ Attempt TLS negotiation
                     └─ Extract: version, security props
                 │
                 ▼ (All probes complete or timeout)
        ┌────────────────────────────┐
        │ Database Transaction:      │
        │ - Store probe results      │
        │ - Update services table    │
        │ - Timestamp probe result   │
        │ - Commit atomically        │
        └────────┬───────────────────┘
                 │
                 ▼
        ┌────────────────────────────┐
        │ Update Dashboard:          │
        │ - Show new probe data      │
        │ - Update service details   │
        └────────────────────────────┘
```

### Data Merge Strategy (Rescan)

```
Rescan triggers for existing data

Old Database State:
┌─────────────────────────────────────┐
│ Server: 10.0.0.5                    │
│  ├─ OS: Linux (detected 2 days ago) │
│  ├─ Ports: 22, 80, 443              │
│  │  ├─ Port 22: OpenSSH 7.4         │
│  │  └─ Port 80: Apache 2.4.6        │
│  └─ Notes: "Main web server"        │
│  └─ Label: "Production"             │
└─────────────────────────────────────┘

New Scan Result:
┌─────────────────────────────────────┐
│ Host: 10.0.0.5                      │
│  ├─ OS: Linux (Ubuntu 18.04)        │
│  ├─ Ports: 22, 80, 443, 8888        │
│  │  ├─ Port 22: OpenSSH 7.4         │
│  │  └─ Port 80: Apache 2.4.6        │
│  │  └─ Port 8888: unknown           │
└─────────────────────────────────────┘

Merge Algorithm:
1. Match by IP → same server
2. For each field:
   - User-editable (notes, label) → KEEP old
   - System-generated (OS, ports) → UPDATE to new
   - NEW ports from scan → ADD
   - MISSING ports from old → KEEP (may be filtered in nmap)
3. Update last_scan timestamp
4. Preserve all historical data (via timestamp)

Result:
┌─────────────────────────────────────┐
│ Server: 10.0.0.5                    │
│  ├─ OS: Linux (Ubuntu 18.04)        │ ← UPDATED
│  ├─ Ports: 22, 80, 443, 8888        │ ← NEW PORT ADDED
│  │  ├─ Port 22: OpenSSH 7.4         │
│  │  ├─ Port 80: Apache 2.4.6        │
│  │  └─ Port 8888: unknown (new)     │
│  ├─ Notes: "Main web server"        │ ← PRESERVED
│  ├─ Label: "Production"             │ ← PRESERVED
│  └─ last_scan: 2026-04-04 14:30:00  │ ← UPDATED
└─────────────────────────────────────┘
```

---

## Database Schema & Relationships

### SQLite Schema

```sql
-- Core Tables

CREATE TABLE servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT UNIQUE NOT NULL,
    hostname TEXT,
    mac_address TEXT,
    os TEXT,
    os_version TEXT,
    confidence_os INTEGER DEFAULT 0,  -- 0-100 confidence score
    last_scan DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    
    -- Indexes for common queries
    INDEX idx_ip (ip),
    INDEX idx_last_scan (last_scan),
    INDEX idx_os (os)
);

CREATE TABLE ports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    port_number INTEGER NOT NULL,
    protocol TEXT NOT NULL,  -- 'tcp', 'udp'
    state TEXT NOT NULL,     -- 'open', 'closed', 'filtered', 'unknown'
    state_reason TEXT,       -- 'syn-ack', 'reset', 'no-response', etc
    last_scan DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
    UNIQUE(server_id, port_number, protocol),
    INDEX idx_server_port (server_id, port_number),
    INDEX idx_state (state)
);

CREATE TABLE services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    port_id INTEGER NOT NULL,
    service_name TEXT NOT NULL,  -- 'ssh', 'http', 'mysql', 'smb', etc
    version TEXT,                -- '7.4p1', '2.4.6', etc
    banner TEXT,                 -- Full service banner (truncated)
    confidence INTEGER DEFAULT 0, -- 0-100 confidence from nmap
    last_scan DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (port_id) REFERENCES ports(id) ON DELETE CASCADE,
    INDEX idx_service_name (service_name),
    INDEX idx_server_service (service_name)
);

CREATE TABLE probes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL,
    probe_type TEXT NOT NULL,  -- 'http_headers', 'ssh_banner', 'sql_version', 'smb_info', 'rdp_info'
    data JSON NOT NULL,        -- Structured probe result (JSON)
    status TEXT DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed', 'failed', 'timeout'
    error_message TEXT,
    confidence INTEGER DEFAULT 0,
    last_attempted DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    UNIQUE(service_id, probe_type),
    INDEX idx_probe_type (probe_type),
    INDEX idx_status (status)
);

CREATE TABLE scan_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT UNIQUE NOT NULL,  -- UUID
    status TEXT DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed', 'failed'
    start_time DATETIME,
    end_time DATETIME,
    duration_seconds INTEGER,
    
    hosts_discovered INTEGER DEFAULT 0,
    ports_found INTEGER DEFAULT 0,
    services_identified INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    
    scan_range TEXT,  -- e.g., "10.0.0.0/24"
    triggered_by TEXT,  -- 'manual', 'scheduled', 'api'
    error_message TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_status (status),
    INDEX idx_start_time (start_time)
);

CREATE TABLE user_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    note_text TEXT NOT NULL,
    label TEXT,  -- e.g., 'production', 'development', 'critical'
    last_updated_by TEXT,  -- user or 'system'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
    UNIQUE(server_id),
    INDEX idx_label (label)
);

CREATE TABLE scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,  -- 'os', 'hostname', etc
    old_value TEXT,
    new_value TEXT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
    INDEX idx_server_history (server_id, changed_at)
);

-- Configuration / Metadata Tables

CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    data_type TEXT DEFAULT 'string',  -- 'string', 'integer', 'json'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_key (key)
);
```

### Relationship Diagram

```
┌──────────────┐
│   servers    │
├──────────────┤
│ id (PK)      │───┐
│ ip           │   │
│ hostname     │   │
│ os           │   │
│ os_version   │   │ 1─────N ┌──────────────┐
│ last_scan    │   │         │   ports      │
│ created_at   │   │         ├──────────────┤
└──────────────┘   │         │ id (PK)      │───┐
      │            │         │ server_id (FK)  │
      │            │         │ port_number  │   │
      │            └─────────│ protocol     │   │ 1─────N ┌──────────────┐
      │                      │ state        │   │         │  services    │
      │                      │ last_scan    │   │         ├──────────────┤
      │                      │ created_at   │   │         │ id (PK)      │───┐
      │                      └──────────────┘   │         │ port_id (FK) │   │
      │                            │            └─────────│ service_name │   │ 1─────N ┌──────────────┐
      │                            │                      │ version      │   │         │   probes     │
      │                            │                      │ banner       │   │         ├──────────────┤
      │                            │                      └──────────────┘   │         │ id (PK)      │
      │                            │                            │            └─────────│ service_id(FK)
      │                            │                            │                      │ probe_type   │
      │                            │                            │                      │ data (JSON)  │
      │                            │                            │                      │ status       │
      │                            │                            │                      └──────────────┘
      │                            │                            │
      │ 1─────N                    │                            │
      └────────────────────────────┼────────────────────────────┘
                                   │
                           ┌───────▼───────┐
                           │ user_notes    │
                           ├───────────────┤
                           │ id (PK)       │
                           │ server_id(FK) │
                           │ note_text     │
                           │ label         │
                           └───────────────┘

                    ┌────────────────────┐
                    │   scan_jobs        │
                    ├────────────────────┤
                    │ id (PK)            │
                    │ scan_id (unique)   │
                    │ status             │
                    │ start_time         │
                    │ hosts_discovered   │
                    └────────────────────┘

                    ┌────────────────────┐
                    │ scan_history       │
                    ├────────────────────┤
                    │ id (PK)            │
                    │ server_id (FK)     │
                    │ field_name         │
                    │ old_value          │
                    │ new_value          │
                    │ changed_at         │
                    └────────────────────┘
```

### Multi-Tenant Query Examples

```sql
-- Get all servers
SELECT * FROM servers WHERE is_active = 1 ORDER BY ip;

-- Get servers with specific service
SELECT DISTINCT s.*, svc.service_name, svc.version
FROM servers s
JOIN ports p ON s.id = p.server_id
JOIN services svc ON p.id = svc.port_id
WHERE svc.service_name = 'ssh' AND p.state = 'open'
ORDER BY s.ip;

-- Get servers with open ports and their services
SELECT s.ip, s.hostname, p.port_number, svc.service_name, svc.version
FROM servers s
JOIN ports p ON s.id = p.server_id
JOIN services svc ON p.id = svc.port_id
WHERE p.state = 'open'
ORDER BY s.ip, p.port_number;

-- Get probe results for all SSH services
SELECT s.ip, s.hostname, pr.probe_type, pr.data
FROM servers s
JOIN ports p ON s.id = p.server_id
JOIN services svc ON p.id = svc.port_id
JOIN probes pr ON svc.id = pr.service_id
WHERE svc.service_name = 'ssh' AND pr.status = 'completed'
ORDER BY s.ip;

-- Find servers by label
SELECT s.*, un.note_text, un.label
FROM servers s
LEFT JOIN user_notes un ON s.id = un.server_id
WHERE un.label = 'production'
ORDER BY s.ip;

-- Get scan statistics
SELECT 
    COUNT(DISTINCT s.id) as total_servers,
    COUNT(DISTINCT CASE WHEN p.state = 'open' THEN p.id END) as open_ports,
    COUNT(DISTINCT svc.id) as services_identified,
    MAX(s.last_scan) as last_scan_time
FROM servers s
LEFT JOIN ports p ON s.id = p.server_id
LEFT JOIN services svc ON p.id = svc.port_id
WHERE s.is_active = 1;
```

---

## Module Structure & Dependencies

### Directory Organization

```
mcp/
├── config.py                    # Global configuration, env vars
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── Makefile                     # Quick commands
│
├── scanner/                     # Network scanning module
│   ├── __init__.py
│   ├── nmap_wrapper.py         # Nmap subprocess wrapper
│   ├── parser.py               # XML parser & result formatting
│   ├── validator.py            # IP range & target validation
│   ├── orchestrator.py         # Scan workflow coordination
│   └── storage.py              # Scan result persistence
│
├── probes/                      # Service-specific probing module
│   ├── __init__.py
│   ├── base.py                 # BaseProbe abstract class
│   ├── http_probe.py           # HTTP/HTTPS headers
│   ├── ssh_probe.py            # SSH banner
│   ├── sql_probe.py            # SQL handshake (MySQL, MSSQL, PostgreSQL)
│   ├── smb_probe.py            # SMB enumeration
│   ├── rdp_probe.py            # RDP negotiation
│   ├── orchestrator.py         # Probe workflow & scheduling
│   └── storage.py              # Probe result persistence
│
├── db/                          # Database & ORM layer
│   ├── __init__.py
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schema.py               # Database initialization & schema
│   ├── dao.py                  # Data Access Objects (repository pattern)
│   ├── merge.py                # Rescan merge logic
│   ├── migrations/             # Schema version control (optional)
│   │   ├── v1_initial.sql
│   │   └── v2_add_probes.sql
│   └── seeders.py              # Demo data for testing
│
├── scheduler/                   # Background job scheduling
│   ├── __init__.py
│   ├── scheduler.py            # APScheduler integration
│   ├── jobs.py                 # Job definitions (scan, probe, etc)
│   └── triggers.py             # Trigger logic, callbacks
│
├── api/                         # REST API layer
│   ├── __init__.py
│   ├── app.py                  # Flask app factory
│   ├── middleware.py           # Auth, validation, logging, CORS
│   ├── exceptions.py           # Custom exceptions & handlers
│   └── routes/
│       ├── __init__.py
│       ├── servers.py          # GET/POST /servers
│       ├── services.py         # GET /services
│       ├── scans.py            # POST /scan, GET /scan/status
│       ├── probes.py           # GET /probes, POST /probes/re-probe
│       ├── dashboard.py        # GET /dashboard/summary
│       └── health.py           # GET /health
│
├── ui/                          # Frontend (HTML/CSS/JS)
│   ├── index.html              # Main dashboard page
│   ├── css/
│   │   ├── style.css           # Main styles
│   │   └── responsive.css      # Mobile & responsive
│   └── js/
│       ├── app.js              # Core app logic
│       ├── api-client.js       # API wrapper & HTTP client
│       ├── table.js            # Server table rendering
│       └── sidebar.js          # Service sidebar & filtering
│
├── nginx/                       # Nginx configuration
│   ├── nginx.conf              # Main configuration
│   ├── ssl/                    # SSL certificates (self-signed)
│   │   ├── mcp.crt
│   │   └── mcp.key
│   └── conf.d/
│       └── mcp.conf            # MCP-specific config
│
├── docker/                      # Docker deployment
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── deploy/                      # Deployment scripts
│   ├── start.sh                # Startup script
│   ├── stop.sh                 # Shutdown script
│   ├── backup.sh               # Database backup
│   ├── mcp.service             # Systemd service file
│   └── health-check.sh         # Health check script
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_scanner.py         # Scanner module tests
│   ├── test_probes.py          # Probe module tests
│   ├── test_db.py              # Database & ORM tests
│   ├── test_api.py             # REST API endpoint tests
│   ├── test_scheduler.py       # Scheduler tests
│   ├── fixtures/               # Test data & mock files
│   │   ├── sample_nmap.xml
│   │   ├── test_servers.json
│   │   └── mock_probes.json
│   └── conftest.py             # Pytest configuration & fixtures
│
├── docs/                        # Documentation
│   ├── README.md               # Project overview
│   ├── SETUP.md                # Installation & setup
│   ├── API_SPEC.md             # REST API documentation
│   ├── USER_GUIDE.md           # User manual
│   ├── DEV_GUIDE.md            # Developer guide
│   └── SECURITY.md             # Security model & threat analysis
│
└── logs/                        # Runtime logs (gitignored)
    ├── app.log
    ├── scanner.log
    └── probes.log
```

### Module Dependencies Graph

```
config.py (global configuration)
    ↓
    ├─→ scanner/
    │   ├─→ nmap_wrapper.py (subprocess, external nmap)
    │   ├─→ parser.py (lxml, nmap XML parsing)
    │   ├─→ validator.py (ipaddress module)
    │   ├─→ orchestrator.py
    │   └─→ storage.py ─→ db/dao.py ─→ db/models.py ─→ db/schema.py
    │
    ├─→ probes/
    │   ├─→ base.py (abstract class)
    │   ├─→ http_probe.py (requests, socket)
    │   ├─→ ssh_probe.py (paramiko or socket)
    │   ├─→ sql_probe.py (pymysql, pyodbc, psycopg2)
    │   ├─→ smb_probe.py (impacket or socket)
    │   ├─→ rdp_probe.py (socket, TLS)
    │   ├─→ orchestrator.py
    │   └─→ storage.py ─→ db/dao.py
    │
    ├─→ db/
    │   ├─→ models.py (SQLAlchemy)
    │   ├─→ dao.py (query builders)
    │   ├─→ merge.py (data merging logic)
    │   └─→ schema.py (sqlite3)
    │
    ├─→ scheduler/
    │   ├─→ scheduler.py (APScheduler)
    │   ├─→ jobs.py ─→ scanner/, probes/
    │   └─→ triggers.py ─→ db/
    │
    └─→ api/
        ├─→ app.py (Flask)
        ├─→ middleware.py
        ├─→ routes/
        │   ├─→ servers.py ─→ db/dao.py
        │   ├─→ services.py ─→ db/dao.py
        │   ├─→ scans.py ─→ scanner/, scheduler/
        │   ├─→ probes.py ─→ db/dao.py, probes/
        │   └─→ dashboard.py ─→ db/dao.py (aggregation queries)
        └─→ ui/ (HTML/CSS/JS) ─→ api/ (REST calls)
```

### Key Classes & Interfaces

```python
# scanner/nmap_wrapper.py
class NmapWrapper:
    def __init__(self, config: Config)
    def validate_target_range(self, range: str) → bool:
    def discover_hosts(self, range: str, timeout: int = 300) → List[Host]:
    def scan_ports(self, host: str, ports: List[int] = []) → List[Port]:
    def detect_os(self, host: str) → OSInfo:
    def parse_xml_output(self, xml_file: str) → dict:

# probes/base.py
class BaseProbe(ABC):
    @abstractmethod
    def probe(self, host: str, port: int, timeout: int = 30) → ProbeResult:
    def _connect(self, host: str, port: int, timeout: int):
    def _parse_result(self, raw_data: bytes) → dict:

# db/models.py
class Server(Base):
    id: int
    ip: str
    hostname: Optional[str]
    os: Optional[str]
    ports: Relationship[List[Port]]
    services: Relationship[List[Service]]
    
class Port(Base):
    id: int
    server_id: int
    port_number: int
    services: Relationship[List[Service]]
    
class Service(Base):
    id: int
    port_id: int
    service_name: str
    probes: Relationship[List[Probe]]

# scheduler/jobs.py
class ScanJob:
    @staticmethod
    def run_scan(scan_range: str, callback=None) → ScanResult:

class ProbeJob:
    @staticmethod
    def run_probes(service_ids: List[int]) → List[ProbeResult]:

# api/app.py
class MCPApp:
    def __init__(self, config: Config):
    def create_app(self) → Flask:
    def initialize_routes(self):
    def register_middleware(self):
```

---

## REST API Specification

### API Endpoints Overview

```
GET    /api/servers                    # List all servers
GET    /api/servers/<id>               # Get server details
POST   /api/servers/<id>/notes         # Add/update notes
POST   /api/servers/<id>/label         # Set label

GET    /api/services                   # List unique services
GET    /api/services/<name>            # Get servers running service
GET    /api/services/<name>/probes     # Get probe data for service

GET    /api/probes                     # List all probes (filtered)
POST   /api/probes/re-probe/<id>       # Trigger re-probe

POST   /api/scan                       # Trigger immediate scan
GET    /api/scan/status                # Get current scan status
GET    /api/scan/history               # Get past scans

GET    /api/dashboard/summary          # Network statistics

GET    /health                         # Health check
```

### Detailed Endpoint Specifications

#### 1. GET /api/servers

**Description:** List all discovered servers with pagination and filtering

**Query Parameters:**
```
?page=1                    # Page number (default: 1)
&limit=50                  # Results per page (default: 50, max: 1000)
&filter=os:linux           # Filter by OS
&filter=service:ssh        # Filter by service
&filter=label:production   # Filter by label
&sort=ip:asc               # Sort column & direction
&search=10.0.0             # Keyword search (IP, hostname)
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total": 42,
    "page": 1,
    "limit": 50,
    "items": [
      {
        "id": 1,
        "ip": "10.0.0.5",
        "hostname": "web-01.lab",
        "os": "Linux",
        "os_version": "Ubuntu 18.04",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "last_scan": "2026-04-04T14:30:00Z",
        "is_active": true,
        "ports_count": 3,
        "services_count": 3,
        "open_ports": [22, 80, 443],
        "notes": "Main web server",
        "label": "production",
        "created_at": "2026-03-15T10:00:00Z"
      },
      ...
    ]
  }
}
```

**Error (400 Bad Request):**
```json
{
  "success": false,
  "error": "Invalid filter syntax",
  "code": "INVALID_FILTER"
}
```

#### 2. GET /api/servers/<id>

**Description:** Get detailed information about a server

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "ip": "10.0.0.5",
    "hostname": "web-01.lab",
    "os": "Linux",
    "os_version": "Ubuntu 18.04",
    "mac_address": "aa:bb:cc:dd:ee:ff",
    "confidence_os": 95,
    "last_scan": "2026-04-04T14:30:00Z",
    "is_active": true,
    "notes": "Main web server",
    "label": "production",
    "ports": [
      {
        "id": 10,
        "port_number": 22,
        "protocol": "tcp",
        "state": "open",
        "state_reason": "syn-ack",
        "last_scan": "2026-04-04T14:30:00Z",
        "services": [
          {
            "id": 100,
            "service_name": "ssh",
            "version": "7.4p1",
            "banner": "OpenSSH_7.4p1 Debian-10+deb9u7",
            "confidence": 100,
            "probes": [
              {
                "id": 500,
                "probe_type": "ssh_banner",
                "status": "completed",
                "data": {
                  "version": "7.4p1",
                  "algorithms": ["diffie-hellman-group14-sha1", ...],
                  "key_types": ["ssh-rsa", ...]
                },
                "confidence": 100,
                "last_attempted": "2026-04-04T14:31:00Z"
              }
            ]
          }
        ]
      },
      ...
    ],
    "created_at": "2026-03-15T10:00:00Z"
  }
}
```

#### 3. POST /api/servers/<id>/notes

**Description:** Add or update user notes for a server

**Request Body:**
```json
{
  "note_text": "Updated: This server needs security patching",
  "label": "needs-attention"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "notes": "Updated: This server needs security patching",
    "label": "needs-attention",
    "updated_at": "2026-04-04T14:35:00Z"
  }
}
```

#### 4. GET /api/services

**Description:** List unique services discovered

**Query Parameters:**
```
?page=1
&limit=50
&sort=count:desc    # Sort by server count
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total": 15,
    "items": [
      {
        "service_name": "ssh",
        "count": 42,
        "versions": [
          {"version": "7.4p1", "count": 38},
          {"version": "8.0p1", "count": 4}
        ],
        "ports": [22]
      },
      {
        "service_name": "http",
        "count": 38,
        "versions": [
          {"version": "2.4.6", "count": 35},
          {"version": "2.2.15", "count": 3}
        ],
        "ports": [80, 8080, 8888]
      },
      ...
    ]
  }
}
```

#### 5. GET /api/services/<name>

**Description:** Get all servers running a specific service

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "service_name": "ssh",
    "count": 42,
    "servers": [
      {
        "id": 1,
        "ip": "10.0.0.5",
        "hostname": "web-01.lab",
        "port": 22,
        "version": "7.4p1",
        "banner": "OpenSSH_7.4p1 Debian-10+deb9u7",
        "confidence": 100
      },
      ...
    ]
  }
}
```

#### 6. POST /api/scan

**Description:** Trigger an immediate network scan

**Request Body (optional):**
```json
{
  "scan_range": "10.0.0.0/24",  # Optional: override default range
  "aggressive": false             # Optional: use aggressive nmap flags
}
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "data": {
    "scan_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "in_progress",
    "started_at": "2026-04-04T14:40:00Z",
    "scan_range": "10.0.0.0/24",
    "message": "Scan started in background"
  }
}
```

#### 7. GET /api/scan/status

**Description:** Get current scan status

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "scan_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "in_progress",
    "progress": 45,              # Percentage (0-100)
    "started_at": "2026-04-04T14:40:00Z",
    "elapsed_seconds": 120,
    "hosts_discovered": 18,
    "ports_found": 45,
    "services_identified": 28,
    "current_phase": "port_scanning",
    "current_target": "10.0.0.15"
  }
}
```

**When scan is complete (200 OK):**
```json
{
  "success": true,
  "data": {
    "scan_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "completed_at": "2026-04-04T14:55:00Z",
    "duration_seconds": 900,
    "hosts_discovered": 42,
    "ports_found": 128,
    "services_identified": 89,
    "errors": 0
  }
}
```

#### 8. GET /api/scan/history

**Description:** Get past scans

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total": 100,
    "items": [
      {
        "scan_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "completed",
        "started_at": "2026-04-04T14:40:00Z",
        "completed_at": "2026-04-04T14:55:00Z",
        "duration_seconds": 900,
        "hosts_discovered": 42,
        "ports_found": 128,
        "services_identified": 89,
        "triggered_by": "scheduled"
      },
      ...
    ]
  }
}
```

#### 9. GET /api/dashboard/summary

**Description:** Network statistics & overview

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_servers": 42,
      "active_servers": 40,
      "offline_servers": 2,
      "total_ports": 128,
      "open_ports": 95,
      "closed_ports": 33,
      "filtered_ports": 0,
      "unique_services": 15,
      "unique_service_versions": 42,
      "last_scan": "2026-04-04T14:55:00Z",
      "next_scheduled_scan": "2026-04-04T15:55:00Z"
    },
    "os_distribution": [
      {"os": "Linux", "count": 28},
      {"os": "Windows", "count": 12},
      {"os": "Unknown", "count": 2}
    ],
    "top_services": [
      {"service": "ssh", "count": 42},
      {"service": "http", "count": 38},
      {"service": "mysql", "count": 12},
      {"service": "smb", "count": 8},
      {"service": "rdp", "count": 5}
    ],
    "probe_status": {
      "completed": 85,
      "pending": 3,
      "failed": 2,
      "timeout": 0
    }
  }
}
```

#### 10. GET /health

**Description:** Health check endpoint

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-04T14:56:00Z",
  "checks": {
    "database": "ok",
    "nmap": "ok",
    "scheduler": "ok",
    "uptime_seconds": 3600
  }
}
```

### Error Response Format

All errors follow a consistent format:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": null  # Optional: additional context
}
```

Common Error Codes:
- `INVALID_REQUEST` — Malformed request or invalid parameters
- `INVALID_FILTER` — Invalid filter syntax
- `NOT_FOUND` — Resource not found
- `UNAUTHORIZED` — IP not whitelisted
- `RATE_LIMITED` — Too many requests
- `SCAN_IN_PROGRESS` — Cannot start scan, one already running
- `DATABASE_ERROR` — Database operation failed
- `EXTERNAL_TOOL_ERROR` — Nmap or probe tool failed
- `INTERNAL_ERROR` — Unexpected server error

### Rate Limiting

```
GET    /api/servers         # 100 requests/minute
POST   /api/scan            # 10 requests/minute
POST   /api/probes/re-probe # 50 requests/minute
Other  *                    # 500 requests/minute
```

Headers on all responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 92
X-RateLimit-Reset: 2026-04-04T15:00:00Z
```

---

## Configuration Management

### Configuration Hierarchy

```
1. Environment Variables (highest priority)
   MCP_IP_WHITELIST=10.0.0.0/8
   MCP_SCAN_INTERVAL=3600
   MCP_DATABASE_PATH=/data/mcp.db

2. Configuration File (.env, config.yaml, config.json)
   [scanning]
   ip_whitelist = 10.0.0.0/8
   timeout = 300

3. Application Defaults (in config.py)
   DEFAULT_SCAN_INTERVAL = 3600
   DEFAULT_TIMEOUT = 300
```

### config.py Structure

```python
# config.py

import os
from dataclasses import dataclass
from typing import List

@dataclass
class ScanConfig:
    """Scanning configuration"""
    ip_whitelist: List[str]      # e.g., ['10.0.0.0/8', '192.168.1.0/24']
    timeout: int = 300           # Seconds per scan
    ports: List[int] = None      # Specific ports to scan (None = common ports)
    parallel_hosts: int = 10     # Concurrent host scans
    parallel_probes: int = 20    # Concurrent probe jobs
    aggressive: bool = False     # Use aggressive nmap flags

@dataclass
class SchedulerConfig:
    """Scheduler configuration"""
    scan_interval: int = 3600    # Seconds between scans (1 hour)
    probe_cache_hours: int = 24  # Cache probe results for N hours
    max_concurrent_scans: int = 1

@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_path: str = './data/mcp.db'
    pool_size: int = 5
    max_overflow: int = 10
    echo_sql: bool = False       # Log all SQL queries

@dataclass
class APIConfig:
    """REST API configuration"""
    host: str = '127.0.0.1'
    port: int = 5000
    debug: bool = False
    allowed_ips: List[str] = None  # Whitelist (None = localhost only)
    rate_limit: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

@dataclass
class NginxConfig:
    """Nginx configuration"""
    listen_port: int = 8080
    use_ssl: bool = False
    ssl_cert: str = './nginx/ssl/mcp.crt'
    ssl_key: str = './nginx/ssl/mcp.key'
    upstream_backend: str = '127.0.0.1:5000'

class Config:
    """Main configuration loader"""
    
    def __init__(self):
        self.scan = self._load_scan_config()
        self.scheduler = self._load_scheduler_config()
        self.database = self._load_database_config()
        self.api = self._load_api_config()
        self.nginx = self._load_nginx_config()
        
        # Validate critical fields
        self._validate()
    
    def _load_scan_config(self) -> ScanConfig:
        """Load from env or file"""
        ...
    
    def _validate(self):
        """Ensure config is valid"""
        # Validate IP whitelist
        for ip_range in self.scan.ip_whitelist:
            try:
                ipaddress.ip_network(ip_range)
            except ValueError:
                raise ConfigError(f"Invalid IP range: {ip_range}")

# Usage in application:
config = Config()
print(config.scan.ip_whitelist)
print(config.scheduler.scan_interval)
```

### Environment Variables Reference

```bash
# Scanning
MCP_IP_WHITELIST=10.0.0.0/8,192.168.1.0/24
MCP_SCAN_TIMEOUT=300
MCP_SCAN_PARALLEL_HOSTS=10
MCP_SCAN_AGGRESSIVE=false

# Scheduler
MCP_SCAN_INTERVAL=3600
MCP_PROBE_CACHE_HOURS=24
MCP_MAX_CONCURRENT_SCANS=1

# Database
MCP_DATABASE_PATH=/data/mcp.db
MCP_DATABASE_POOL_SIZE=5
MCP_DATABASE_ECHO_SQL=false

# API
MCP_API_HOST=127.0.0.1
MCP_API_PORT=5000
MCP_API_DEBUG=false
MCP_API_ALLOWED_IPS=127.0.0.1,192.168.1.0/24
MCP_RATE_LIMIT=true

# Nginx
MCP_NGINX_PORT=8080
MCP_NGINX_SSL=false
MCP_NGINX_SSL_CERT=/etc/nginx/ssl/mcp.crt
MCP_NGINX_SSL_KEY=/etc/nginx/ssl/mcp.key

# Logging
MCP_LOG_LEVEL=INFO
MCP_LOG_FILE=/var/log/mcp/app.log
```

---

## Error Handling & Recovery

### Error Classification & Response

```
┌─────────────────────────────────────────────────────────┐
│ Error Type                                              │
├─────────────────────────────────────────────────────────┤
│ Configuration Error                                     │
│ ├─ Action: Fail fast at startup, exit with code 1     │
│ ├─ Example: Invalid IP whitelist, missing nmap         │
│ └─ Log: ERROR level                                    │
│                                                         │
│ Input Validation Error                                 │
│ ├─ Action: Reject request, return 400 Bad Request     │
│ ├─ Example: Malformed IP range, invalid filter syntax │
│ └─ Log: WARN level                                    │
│                                                         │
│ Runtime Error (Recoverable)                            │
│ ├─ Action: Retry with backoff, continue operations    │
│ ├─ Example: Network timeout, probe connection refused │
│ └─ Log: WARN level (first attempt), ERROR (final)    │
│                                                         │
│ Runtime Error (Non-Recoverable)                        │
│ ├─ Action: Log, skip item, continue overall operation │
│ ├─ Example: Permission denied, nmap parse failure     │
│ └─ Log: ERROR level                                    │
│                                                         │
│ Database Error                                         │
│ ├─ Action: Rollback transaction, retry operation      │
│ ├─ Example: Constraint violation, connection error    │
│ └─ Log: ERROR level (may escalate to system)          │
│                                                         │
│ External Tool Error                                    │
│ ├─ Action: Graceful failure, continue with other data │
│ ├─ Example: nmap crash, probe crash                   │
│ └─ Log: ERROR level                                    │
└─────────────────────────────────────────────────────────┘
```

### Retry Strategy

```python
# Retry logic with exponential backoff

from tenacity import retry, stop_after_attempt, wait_exponential

class ScanOrchestraor:
    
    @retry(
        stop=stop_after_attempt(3),  # Retry up to 3 times
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 2, 4, 8 seconds
        reraise=True  # Re-raise after all retries exhausted
    )
    def run_nmap_scan(self, host: str) → dict:
        """Run nmap with automatic retries"""
        try:
            result = self.nmap_wrapper.scan_ports(host)
            logger.info(f"Scan succeeded for {host}")
            return result
        except TimeoutError:
            logger.warning(f"Scan timeout for {host}, retrying...")
            raise
        except Exception as e:
            logger.error(f"Scan failed for {host}: {e}")
            raise

    def partial_scan_handler(self, host: str):
        """Handle partial scan failures gracefully"""
        try:
            # Try full scan
            result = self.run_nmap_scan(host)
        except Exception:
            # Fall back to basic connectivity check
            logger.warning(f"Full scan failed for {host}, marking as \"unknown\"")
            result = {
                'host': host,
                'status': 'error',
                'error': 'Scan failed, manual verification needed'
            }
        return result
```

### Database Transaction Management

```python
# Transaction handling

from contextlib import contextmanager

@contextmanager
def database_transaction(session):
    """Atomic transaction with automatic rollback"""
    try:
        yield session
        session.commit()
        logger.info("Transaction committed successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"Transaction rolled back: {e}")
        raise

# Usage:
def store_scan_results(results: dict):
    """Store scan results atomically"""
    with database_transaction(db.session) as session:
        # All inserts/updates here
        
        scan_job = ScanJob(...)
        session.add(scan_job)
        
        for host in results['hosts']:
            server = Server(...)
            session.add(server)
            
            for port in host['ports']:
                port_obj = Port(...)
                session.add(port_obj)
        
        # If any error occurs above, entire transaction rolls back
```

### Health Monitoring

```python
# Health check implementation

class HealthMonitor:
    
    def check_health(self) -> HealthStatus:
        """Comprehensive health check"""
        checks = {
            'database': self._check_database(),
            'nmap': self._check_nmap(),
            'scheduler': self._check_scheduler(),
            'disk_space': self._check_disk_space(),
            'network': self._check_network()
        }
        
        # Overall status: healthy if all checks pass
        status = 'healthy' if all(checks.values()) else 'degraded'
        
        return HealthStatus(
            status=status,
            checks=checks,
            timestamp=datetime.now()
        )
    
    def _check_database(self) → bool:
        try:
            db.session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False
    
    def _check_nmap(self) → bool:
        try:
            result = subprocess.run(['nmap', '--version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_scheduler(self) → bool:
        # Check if scheduler is running and jobs are queued
        return self.scheduler.is_running()
```

---

## Scalability & Performance

### Optimization Strategies

#### 1. Database Optimization

```
Indexing Strategy:
├─ indexes on frequently queried columns
│  ├─ servers.ip (WHERE clause, exact match)
│  ├─ services.service_name (WHERE, filtering)
│  ├─ ports.state (WHERE, filtering)
│  └─ scan_jobs.start_time (ORDER BY, pagination)
│
├─ composite indexes for common queries
│  ├─ (server_id, port_number) on ports
│  ├─ (service_name, version) on services
│  └─ (server_id, last_scan) on servers
│
└─ avoid indexes on low-cardinality columns
   └─ is_active (only 2 values: true/false)

Query Optimization:
├─ Use pagination (no unbounded queries)
├─ Use projection (SELECT specific columns, not *)
├─ Use joins efficiently (avoid N+1 queries)
├─ Implement query caching for aggregations
└─ Monitor slow queries (log queries > 1 second)
```

#### 2. Scan Concurrency

```
Parallel Architecture:
┌──────────────────────────────────────────────┐
│ Host Discovery (single, linear)              │
│ ├─ Ping sweep: 10.0.0.0/24 (~60 seconds)    │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│ Port Scanning (parallel)                     │
│ ├─ Host 1 ──┐                                │
│ ├─ Host 2 ──┼─ parallel_hosts=10 threads    │
│ ├─ Host 3 ──┤ (~120 seconds for 40 hosts)   │
│ └─ Host N ──┘                                │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│ OS Detection (parallel)                      │
│ └─ Similar to port scanning                  │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│ Probing (parallel)                           │
│ ├─ Service 1 ┐                               │
│ ├─ Service 2 ├─ parallel_probes=20 threads  │
│ ├─ Service 3 │ (~60 seconds for 100+ services)
│ └─ Service N ┘                               │
└──────────────────────────────────────────────┘
```

#### 3. Caching Strategy

```
Cache Layers:
┌────────────────────────────────────────┐
│ Application Cache (in-memory)          │
│ ├─ TTL: 5 minutes                      │
│ ├─ Data: dashboard summary, service list
│ └─ Invalidation: on scan complete     │
│                                        │
├─ Probe Cache (database-backed)        │
│ ├─ TTL: 24 hours (configurable)       │
│ ├─ Data: probe results (SSH banner, etc)
│ └─ Invalidation: manual or time-based │
│                                        │
└─ Query Result Cache                   │
  ├─ TTL: 1 minute                      │
  ├─ Data: paginated server lists       │
  └─ Invalidation: on DB write         │
```

#### 4. Dashboard Performance

```
Frontend Optimizations:
├─ Pagination: 50 rows/page (reduces DOM)
├─ Lazy Loading: expandable rows fetch on click
├─ Virtual Scrolling: render only visible rows (100+ servers)
├─ API Polling: 30-second intervals (not on every keystroke)
├─ Debouncing: search/filter with 500ms delay
├─ Minification: CSS, JS bundling and compression
└─ Caching: browser cache + service worker for offline mode

Network Optimization:
├─ Gzip compression: 80-90% size reduction
├─ CDN for static assets: (if not local-only)
├─ HTTP/2 persistent connections
└─ Response size: paginate, filter server-side
```

### Performance Benchmarks (Target)

```
Scan Time (100 hosts, /24 network):
├─ Host Discovery: ~60 seconds
├─ Port Scanning: ~120 seconds
├─ OS Detection: ~60 seconds
└─ Total: ~240 seconds (4 minutes)

Probe Time (50 services):
├─ Parallel probes (20 concurrent): ~30-60 seconds
└─ Total: ~60 seconds

API Response Time:
├─ GET /servers (1000 servers): < 500ms
├─ GET /services: < 200ms
├─ GET /dashboard/summary: < 100ms
└─ POST /scan: < 2 seconds (async job)

Database Query Time:
├─ Simple SELECT: < 10ms
├─ Complex JOIN: < 100ms
├─ Aggregation: < 200ms
└─ Full table scan: < 500ms (with limit)

Dashboard Load Time:
├─ Initial HTML: < 1s
├─ JS + CSS: < 2s (cached)
├─ Data fetch (AJAX): < 1s
├─ First table render: < 2s
└─ Interactive in: < 5s
```

---

## Security Architecture

### Authentication & Authorization

```
┌─────────────────────────────────────────────────┐
│ Access Control Strategy                         │
├─────────────────────────────────────────────────┤
│ Layer 1: IP Whitelisting                        │
│ ├─ Allowed: 127.0.0.1 (localhost)              │
│ ├─ Allowed: 192.168.1.0/24 (LAN)               │
│ └─ Blocked: All other IPs (403 Forbidden)      │
│                                                 │
│ Layer 2: Simple Token (Optional)                │
│ ├─ Token stored in .env (not versioned)        │
│ ├─ Token passed as X-API-Token header          │
│ ├─ Token validated on every request            │
│ └─ Token rotation every 30 days (manual)       │
│                                                 │
│ Layer 3: Dashboard (Form-based)                 │
│ ├─ No login required (IP whitelist sufficient)  │
│ ├─ CSRF token on all POST requests             │
│ └─ Session cookie (HttpOnly, Secure flags)     │
└─────────────────────────────────────────────────┘
```

### Network Security

```
Scanning Safety:
├─ Whitelist-only scanning (explicit ranges)
│  └─ Config validation at startup & on every scan
│
├─ Safe nmap flags (no aggressive probing)
│  ├─ -sn (ping sweep, no ports)
│  ├─ -sV (service version, safe)
│  ├─ -O (OS detection, safe)
│  └─ Disabled: -sS (SYN stealth), --script, -A (aggressive)
│
├─ Timeouts on all network operations
│  ├─ Host discovery: 300s max
│  ├─ Port scan: 300s max per host
│  ├─ Probe: 30s max per host:port
│  └─ Prevents hanging threads
│
└─ Network separation
   └─ Sandbox network isolated from public network

Data Protection:
├─ Database encryption (optional, SQLite doesn't support natively)
│  └─ Consider: Full-disk encryption for /data partition
│
├─ Transit encryption
│  ├─ HTTPS for dashboard (self-signed cert)
│  ├─ No external data transmission
│  └─ Local-only communication
│
└─ Access logs
   ├─ All API requests logged with timestamp, IP, endpoint
   ├─ Scan activities logged with parameters & results
   ├─ Probe activities logged with success/failure
   └─ Audit trail for compliance
```

### Input Validation

```
Validation Rules:
├─ IP ranges (whitelist scanning)
│  ├─ Must be valid CIDR notation: 10.0.0.0/8
│  ├─ Cannot be default route: 0.0.0.0/0
│  ├─ Cannot be multicast: 224.0.0.0/4
│  └─ Must be private IP space (RFC 1918)
│
├─ API parameters (search, filter, pagination)
│  ├─ Page numbers: integer, >= 1
│  ├─ Limit: integer, 1-1000
│  ├─ Filter strings: sanitized, no SQL injection
│  └─ Sort field: must be from allowed list
│
├─ User input (notes, labels)
│  ├─ Max length: 500 characters
│  ├─ No script tags: sanitized for XSS
│  ├─ No SQL keywords: parameterized queries
│  └─ Unicode: allowed (UTF-8)
│
└─ File uploads (if future feature)
   ├─ Whitelist file extensions (.json, .yaml, .csv)
   ├─ Max file size: 10MB
   ├─ Scan for malware (ClamAV)
   └─ Store in sandboxed directory
```

### Output Sanitization

```
Data Sanitization:
├─ Banner information (SSH, HTTP, SQL)
│  ├─ Truncate to 256 characters
│  ├─ Escape special characters
│  ├─ Remove sensitive keywords (passwords, tokens)
│  └─ Example: "OpenSSH_7.4p1" (safe) vs redacted tokens
│
├─ Web output (HTML escaping)
│  ├─ All user input escaped when rendered
│  ├─ No {{{unescaped}}} template variables
│  ├─ Content-Security-Policy header enabled
│  └─ X-Frame-Options: DENY (clickjacking protection)
│
└─ Log files (PII redaction)
   ├─ Passwords never logged
   ├─ API tokens redacted (****)
   ├─ Hostnames sanitized if sensitive
   └─ Log rotation & retention: 30 days
```

### Threat Model

```
Threat: Unauthorized network scanning

Mitigation:
├─ IP whitelist enforced at Nginx + API layer
├─ Scanning restricted to configured CIDR ranges
├─ Audit log of all scan requests
├─ Rate limiting: max 10 scans/minute
└─ Alert on unusual scan patterns

---

Threat: Data breach (exported scan data)

Mitigation:
├─ Database stored locally (no cloud sync)
├─ HTTPS for dashboard (encryption in transit)
├─ No data export feature (prevents data theft)
├─ File permissions: 600 on database file
├─ Database path: /data/mcp.db (restricted directory)
├─ Backups encrypted (if automated backups used)
└─ Audit log of all data access

---

Threat: Resource exhaustion (DoS)

Mitigation:
├─ Rate limiting on all API endpoints
├─ Max concurrent scans: 1 (configurable)
├─ Query pagination (no unbounded data transfer)
├─ Timeout on all external tool calls
├─ CPU/memory monitoring (systemd resource limits)
└─ Max database connection pool: 5

---

Threat: Privilege escalation

Mitigation:
├─ Run as non-root user (systemd User=mcp)
├─ File permissions: 644 on config, 600 on secrets
├─ No sudo required (nmap can run unprivileged for basic scans)
└─ SELinux policy (if deployed on RHEL/CentOS)

---

Threat: Malicious input (injection attacks)

Mitigation:
├─ IP CIDR validation (regex + ipaddress module)
├─ SQL injection: parameterized queries via ORM
├─ XSS: HTML escaping on all user output
├─ Command injection: no shell=True in subprocess calls
└─ CSRF: tokens on all POST endpoints
```

---

## Extension Points & Customization

### Adding New Probe Types

```python
# 1. Create new probe class inheriting from BaseProbe

from probes.base import BaseProbe, ProbeResult

class DnsProbe(BaseProbe):
    """Custom DNS probe to detect DNS servers"""
    
    PROBE_TYPE = 'dns_query'
    TIMEOUT = 5
    
    def probe(self, host: str, port: int = 53, timeout: int = None) → ProbeResult:
        """Query DNS server and extract version/info"""
        timeout = timeout or self.TIMEOUT
        
        try:
            # Use dns.resolver to query NS records
            answers = dns.resolver.query(host, 'NS')
            
            data = {
                'dns_servers': [str(ans) for ans in answers],
                'queryable': True
            }
            
            return ProbeResult(
                probe_type=self.PROBE_TYPE,
                status='completed',
                data=data,
                confidence=100
            )
        
        except Exception as e:
            return ProbeResult(
                probe_type=self.PROBE_TYPE,
                status='failed',
                error_message=str(e),
                confidence=0
            )

# 2. Register probe in orchestrator

from probes.orchestrator import ProbeOrchestrator

ProbeOrchestrator.register_probe('dns', DnsProbe)

# 3. Probe will now be triggered automatically for services named 'dns'
```

### Adding Custom Scan Filters

```python
# Create custom NmapWrapper subclass

class CustomNmapWrapper(NmapWrapper):
    """Extended nmap wrapper with custom filters"""
    
    def scan_web_servers(self, host: str) → List[Port]:
        """Scan only common web server ports"""
        web_ports = [80, 443, 8080, 8443, 8888, 3000, 5000]
        return self.scan_ports(host, ports=web_ports)
    
    def scan_database_servers(self, host: str) → List[Port]:
        """Scan only database ports"""
        db_ports = [3306, 5432, 1433, 27017, 6379]
        return self.scan_ports(host, ports=db_ports)
    
    def aggressive_scan(self, host: str) → HostInfo:
        """Run aggressive scan with OS detection, version detection, etc"""
        # Use more aggressive nmap flags
        cmd = f"nmap -A -T4 {host}"
        return self.parse_nmap_output(self._run_nmap(cmd))
```

### Adding Custom Scheduler Jobs

```python
# Define new scheduled job

from scheduler.scheduler import Scheduler
from scheduler.jobs import Job

class HealthCheckJob(Job):
    """Periodic health check job"""
    
    def run(self):
        """Check system health and alert if degraded"""
        health_monitor = HealthMonitor()
        health = health_monitor.check_health()
        
        if health.status != 'healthy':
            self._send_alert(f"System health degraded: {health.checks}")
        
        logger.info(f"Health check complete: {health.status}")

# Register job with scheduler

scheduler = Scheduler()
scheduler.add_job(
    HealthCheckJob(),
    'interval',
    seconds=3600,  # Every hour
    name='health_check'
)
```

### Adding Custom API Endpoints

```python
# Create new route module

# api/routes/custom.py

from flask import Blueprint, request, jsonify
from db.dao import ServerDAO

custom_bp = Blueprint('custom', __name__, url_prefix='/api/custom')

@custom_bp.route('/servers/by-os/<os>', methods=['GET'])
def get_servers_by_os(os: str):
    """Custom endpoint: get servers by OS"""
    dao = ServerDAO()
    servers = dao.find_by_os(os)
    
    return jsonify({
        'success': True,
        'data': {
            'os': os,
            'count': len(servers),
            'servers': [s.to_dict() for s in servers]
        }
    })

# Register in api/app.py

app.register_blueprint(custom_bp)
```

### Plugin Architecture (Future)

```
Proposed plugin system:

plugins/
├── __init__.py
├── base.py                      # PluginBase abstract class
├── http_probe_advanced.py       # Extended HTTP probe plugin
├── waf_detection.py             # WAF detection plugin
└── load_plugins.py              # Plugin loader

class PluginBase(ABC):
    """Base class for all plugins"""
    
    def __init__(self):
        self.name = None
        self.version = None
        self.author = None
    
    @abstractmethod
    def initialize(self, app, config):
        """Called on plugin load"""
        pass
    
    @abstractmethod
    def shutdown(self):
        """Called on plugin unload"""
        pass

class WAFDetectionPlugin(PluginBase):
    """Detect WAF/IDS on web servers"""
    
    def initialize(self, app, config):
        self.name = 'WAF Detection'
        self.version = '1.0'
        app.register_blueprint(self.get_routes())
        ProbeOrchestrator.register_probe('waf_detect', WAFDetectProbe)
    
    def get_routes(self):
        """Register custom API routes"""
        bp = Blueprint('waf_detection', __name__)
        
        @bp.route('/api/servers/<id>/waf-status', methods=['GET'])
        def waf_status(id):
            ...
        
        return bp
```

---

## Appendix

### Technology Stack Rationale

| Component | Technology | Reason |
|-----------|-----------|--------|
| Backend | Python 3.8+ | Portable, rich ecosystem (nmap, flask, sqlalchemy) |
| Web Framework | Flask | Lightweight, minimal overhead, easy to customize |
| Database | SQLite | No server needed, file-based, built into Python |
| ORM | SQLAlchemy | Type-safe, query building, migration support |
| Task Scheduler | APScheduler | In-process, cron support, no external dependencies |
| Web Server | Nginx | Lightweight, efficient, good for local deployments |
| Frontend | Vanilla JS | No build tools needed, small footprint |
| Scanning | nmap | Industry standard, reliable, extensive options |
| Testing | pytest | Fixtures, parametrization, good community |

### Related Standards & Best Practices

- [OWASP Top 10](https://owasp.org/www-project-top-ten/) — Security
- [REST API Best Practices](https://restfulapi.net/) — API design
- [SQLite Best Practices](https://www.sqlite.org/bestpractice.html) — Database
- [12 Factor App](https://12factor.net/) — Application architecture
- [OpenAPI 3.0](https://spec.openapis.org) — API documentation format

---

**End of Architectural Details Document**

Version 1.0 | April 4, 2026
