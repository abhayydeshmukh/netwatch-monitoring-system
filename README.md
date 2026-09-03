# NetWatch 📡 – Network & Linux Server Monitoring System

A clean, lightweight, beginner-friendly system and network monitoring application built with **Python**, **Flask**, **psutil**, and **SQLite**.

This project focuses on clear software architecture, clean procedural code, foundational Linux kernel concepts, and core computer networking principles without over-engineering.

---

## 📑 Table of Contents
1. [Architecture & Workflow](#-architecture--workflow)
2. [Key Features](#-key-features)
3. [Core Technical Concepts Explained](#-core-technical-concepts-explained)
   - [Linux `/proc` Virtual Filesystem](#1-how-linux-monitors-hardware-the-proc-filesystem)
   - [ICMP Protocol & How Ping Works](#2-network-monitoring-icmp-echo-protocol)
   - [SQLite & Embedded Storage](#3-data-persistence-sqlite-architecture)
   - [Flask Web Server & Request Lifecycle](#4-web-presentation-flask--jinja2)
4. [Project Structure & File Walkthrough](#-project-structure--file-walkthrough)
5. [Quick Start Guide (Ubuntu / Linux)](#-quick-start-guide-ubuntu--linux)
6. [Quick Start Guide (Windows)](#-quick-start-guide-windows)
7. [Alerting System](#-alerting-system)
8. [10 Likely Placement Interview Questions & Answers](#-10-likely-placement-interview-questions--answers)

---

## 🏗 Architecture & Workflow

```
 +---------------------------------------------------------+
 |                      NetWatch                           |
 +---------------------------------------------------------+
                             |
       +---------------------+---------------------+
       |                                           |
       v                                           v
[ Network Check ]                         [ System Metrics ]
 ICMP Echo Ping (Layer 3)                 psutil (/proc filesystem)
 - Default Target: 8.8.8.8                - CPU Usage %
 - UP/DOWN Status                         - RAM Usage %
 - Latency (ms)                           - Disk Usage %
       |                                  - System Uptime
       +---------------------+---------------------+
                             |
                             v
                 [ SQLite Database (netwatch.db) ]
                  Persists snapshot with timestamp
                             |
                             v
                 [ Alert Evaluation Engine ]
                  CPU > 80%? | RAM > 80%?
                  Disk > 80%? | Ping DOWN?
                             |
                             v
                 [ Flask Web Server (Port 5000) ]
                  Renders index.html via Jinja2
                  - Live status cards
                  - Warning banners
                  - Recent 10-record history table
```

---

## ✨ Key Features

1. **Network Monitoring**:
   - Pings a configurable IP address (default: `8.8.8.8` Google Public DNS).
   - Displays real-time **UP/DOWN** reachability status.
   - Measures packet round-trip latency in milliseconds (**ms**).

2. **Linux System Health**:
   - **CPU Usage %**: Real-time processor utilization.
   - **RAM Usage %**: Active physical memory usage.
   - **Disk Usage %**: Primary root filesystem storage capacity.
   - **System Uptime**: Formatted duration since last kernel boot.

3. **Persistent SQLite Storage**:
   - Self-contained, zero-configuration local database (`netwatch.db`).
   - Automatically stores historical monitoring records.

4. **Web Dashboard**:
   - Clean, dark-mode developer dashboard.
   - Visual progress bars with dynamic color-coding.
   - History table displaying the latest 10 captured snapshots.
   - Auto-refreshes every 10 seconds (includes manual "Refresh Now" button).

5. **Threshold Alerts**:
   - Prominent alert banner automatically triggers when:
     - CPU usage > 80%
     - RAM usage > 80%
     - Disk usage > 80%
     - Target host is unreachable (Ping DOWN)

---

## 🧠 Core Technical Concepts Explained

### 1. How Linux Monitors Hardware: The `/proc` Filesystem
In Linux, "everything is a file". The Linux kernel exposes internal operating system runtime state and hardware statistics through a pseudo-filesystem mounted at `/proc`. It exists in RAM, not on disk.
- **CPU Metrics (`/proc/stat`)**: Contains raw counters (ticks) of time the CPU spent in various states (`user`, `nice`, `system`, `idle`, `iowait`). The `psutil` library calculates CPU % by sampling ticks across an interval:
  $$\text{CPU \%} = \frac{\Delta \text{Active Time}}{\Delta \text{Total Time}} \times 100$$
- **Memory Metrics (`/proc/meminfo`)**: Contains `MemTotal`, `MemFree`, `Buffers`, and `Cached`. Linux uses idle RAM to buffer disk I/O. `psutil` computes true available memory rather than naively looking at "free" memory.
- **System Uptime (`/proc/uptime`)**: Stores two numbers: total seconds the system has been up and seconds spent in idle mode.
- **Disk Space**: Queries the `statvfs()` system call to inspect total blocks versus free blocks on the storage drive.

### 2. Network Monitoring: ICMP Echo Protocol
- Ping relies on the **Internet Control Message Protocol (ICMP)**.
- Unlike HTTP (port 80) or SSH (port 22), ICMP operates directly on **Layer 3 (Network Layer)** of the OSI model and does **not** have port numbers.
- Ping transmits an **ICMP Type 8 (Echo Request)** packet.
- When the target receives it, it responds with an **ICMP Type 0 (Echo Reply)** packet.
- **Latency (Round-Trip Time / RTT)** is the measured duration from transmitting the request to receiving the reply.
- *Why execute the system `ping` command via `subprocess.run`?* Creating raw ICMP sockets directly in Python requires root (`sudo`) or Administrator privileges. Using the system's native `ping` utility avoids permission issues and ensures safe, cross-platform execution.

### 3. Data Persistence: SQLite Architecture
- **Serverless & Embedded**: Unlike MySQL or PostgreSQL which run as standalone daemon services listening on TCP ports, SQLite is linked directly into the Python application. The database is a single disk file (`netwatch.db`).
- **ACID Compliant**: Atomicity, Consistency, Isolation, and Durability ensure reliable transactions.
- **Parameterized Queries**: We use `cursor.execute("INSERT INTO ... VALUES (?, ?)", (val1, val2))` with `?` placeholders. This separates SQL code from user data, preventing SQL injection.

### 4. Web Presentation: Flask & Jinja2
- **WSGI (Web Server Gateway Interface)**: Flask communicates with web servers through WSGI, the Python standard for routing HTTP requests.
- **Server-Side Rendering (SSR)**: When the browser requests `/`, Flask executes the Python handler function, queries the database, evaluates alert conditions, and injects variables into `index.html` via Jinja2 before sending standard HTML/CSS back to the client.

---

## 📁 Project Structure & File Walkthrough

```
NetWatch/
├── app.py              # Flask server, route handlers, and alert threshold logic
├── monitor.py          # System hardware & ICMP ping collection engine
├── database.py         # SQLite schema initialization and CRUD helper functions
├── templates/
│   └── index.html      # Jinja2 HTML dashboard template (cards, alerts, table)
├── static/
│   └── style.css       # Clean, modern CSS with responsive design & dark theme
├── requirements.txt    # Minimal dependencies (Flask and psutil)
├── .gitignore          # Ignores database files, caches, and venv
└── README.md           # Documentation, concept guide, and interview prep
```

### Detailed File Functions:
- **[`database.py`](database.py)**:
  - `init_db()`: Creates the `metrics` table if it does not exist.
  - `insert_metrics(...)`: Inserts a new monitoring record with current timestamp.
  - `get_latest_metrics(limit=10)`: Returns the most recent $N$ records ordered by ID descending.
  - `get_current_metrics()`: Convenience function to retrieve the single latest record.
- **[`monitor.py`](monitor.py)**:
  - `get_ping_latency(host)`: Executes platform-appropriate ping command, parses stdout using regular expressions, and returns `(status, latency)`.
  - `get_system_uptime()`: Calculates days, hours, and minutes since system boot time.
  - `get_system_metrics()`: Samples CPU %, RAM %, Disk %, and uptime.
  - `collect_and_store_metrics(host)`: Orchestrates collection and stores results into SQLite.
- **[`app.py`](app.py)**:
  - `evaluate_alerts(metrics)`: Checks CPU, RAM, Disk, and Ping against safe thresholds.
  - `@app.route('/')`: Main dashboard endpoint; collects live metrics, queries history, and renders the template.
  - `@app.route('/api/metrics')`: RESTful JSON endpoint for testing or external consumption.

---

## 🚀 Quick Start Guide (Ubuntu / Linux)

Run these commands in your Ubuntu terminal:

### 1. Clone or navigate to the directory
```bash
cd netwatch
```

### 2. Create and activate a Python virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the application
```bash
python3 app.py
```

### 5. Access the dashboard
Open your web browser and navigate to:
```
http://localhost:5000
```
*(To ping a custom host or IP, simply add `?ip=<custom_ip>`, for example: `http://localhost:5000/?ip=1.1.1.1`)*

---

## 🪟 Quick Start Guide (Windows)

### 1. Open PowerShell or Command Prompt
```powershell
cd "NetWatch NSE"
```

### 2. Create and activate a virtual environment (optional but recommended)
```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies & run
```powershell
pip install -r requirements.txt
python app.py
```

---

## ⚠️ Alerting System

NetWatch monitors four primary health indicators and warns you when a metric exceeds safe operating limits:

| Metric | Threshold | Alert Message Displayed |
| :--- | :--- | :--- |
| **Ping Reachability** | Status is `DOWN` | `Network Alert: Ping failed! Target host is UNREACHABLE.` |
| **CPU Usage** | $> 80\%$ | `High CPU Usage Warning: X% exceeds safe threshold (80%).` |
| **RAM Usage** | $> 80\%$ | `High Memory (RAM) Usage Warning: X% exceeds safe threshold (80%).` |
| **Disk Usage** | $> 80\%$ | `High Disk Usage Warning: X% exceeds safe threshold (80%).` |

---


