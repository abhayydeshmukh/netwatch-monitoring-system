"""
monitor.py - NetWatch System & Network Metric Collector
=========================================================
This module collects real-time health metrics from the host operating system
and monitors network reachability using ICMP ping.

Key Concepts Explained:
-----------------------
1. How ICMP Ping Works (Networking):
   - Ping relies on the Internet Control Message Protocol (ICMP), which operates
     at the Network Layer (Layer 3) of the OSI model.
   - Unlike HTTP or SSH, ICMP does not use port numbers (TCP/UDP Layer 4).
   - The sender transmits an ICMP "Echo Request" (Type 8) packet to the target IP.
   - If reachable and permitted by firewalls, the target replies with an
     ICMP "Echo Reply" (Type 0).
   - Round-Trip Time (RTT / Latency): The duration (in milliseconds) from when
     the request was transmitted until the response packet was received.
   - Why use the system 'ping' command? Raw ICMP socket creation in Python requires
     root/administrator privileges. Running the OS native ping command via
     'subprocess.run' safely avoids this restriction.

2. How psutil Collects Linux Metrics (Operating System):
   - On Linux, the kernel exposes system state via virtual filesystems,
     primarily '/proc':
     * CPU Usage: '/proc/stat' records time spent by CPU in different modes
       (user, system, idle, iowait). psutil samples these ticks over an interval
       and calculates: (active_time / total_time) * 100.
     * RAM Usage: '/proc/meminfo' reports MemTotal, MemFree, Buffers, and Cached.
       psutil calculates actual used memory accounting for kernel caches.
     * Disk Usage: System calls like statvfs() query filesystem superblock for
       free vs total disk blocks.
     * Uptime: '/proc/uptime' contains total seconds elapsed since kernel boot.
"""

import os
import platform
import re
import subprocess
import time
from datetime import timedelta

import psutil  # type: ignore[import-unresolved]
import database

# Import database module for saving snapshots
import database

# Default target for network connectivity check (Google Public DNS)
DEFAULT_TARGET_IP = "8.8.8.8"


def get_ping_latency(host=DEFAULT_TARGET_IP, timeout=2):
    """
    Pings a target host and measures round-trip latency.
    
    Cross-platform implementation:
    - Linux / Unix: Uses 'ping -c 1 -W <timeout> <host>'
      (-c 1 = send 1 packet, -W 2 = 2-second timeout)
    - Windows: Uses 'ping -n 1 -w <timeout_ms> <host>'
      (-n 1 = send 1 packet, -w 2000 = 2000ms timeout)
    
    Parameters:
        host (str): IP address or hostname to ping (default: 8.8.8.8)
        timeout (int): Timeout in seconds (default: 2)
        
    Returns:
        tuple (str, float or None):
            - status: 'UP' if host responded, 'DOWN' if unreachable or timed out
            - latency: Round-trip time in milliseconds (float), or None if DOWN
    """
    current_os = platform.system().lower()

    if current_os == "windows":
        # Windows ping command: -n is packet count, -w is timeout in milliseconds
        cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
    else:
        # Linux/macOS ping command: -c is packet count, -W is timeout in seconds
        cmd = ["ping", "-c", "1", "-W", str(timeout), host]

    try:
        # Execute the ping command without opening a visible shell window
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout + 2  # Extra buffer to avoid subprocess hanging
        )

        # A returncode of 0 means ping received a response
        if result.returncode == 0:
            output = result.stdout

            # Match latency using regular expressions
            # Linux example:   "time=14.2 ms" or "64 bytes from ... time=21.4 ms"
            # Windows example: "time=14ms" or "time<1ms" or "Average = 14ms"
            match = re.search(r"time[=<]\s*(\d+(?:\.\d+)?)\s*ms", output, re.IGNORECASE)
            if match:
                latency = float(match.group(1))
                return "UP", latency

            # Alternate regex for some Linux distributions (rtt min/avg/max/mdev = .../15.201/...)
            rtt_match = re.search(r"rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)/", output)
            if rtt_match:
                latency = float(rtt_match.group(1))
                return "UP", latency

            # If returncode is 0 but regex didn't capture, default to UP with minimal latency
            return "UP", 1.0

        else:
            # Non-zero exit code means packet loss, timeout, or destination unreachable
            return "DOWN", None

    except (subprocess.TimeoutExpired, Exception):
        # Any exception (e.g. timeout expired, network interface down) marks target DOWN
        return "DOWN", None


def get_system_uptime():
    """
    Calculates how long the operating system has been running.
    
    Returns:
        str: Human-readable uptime format (e.g., '2 days, 4h 12m' or '1h 35m 20s')
    """
    boot_timestamp = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_timestamp)
    
    # Use timedelta for clean human-readable representation
    uptime_duration = timedelta(seconds=uptime_seconds)
    days = uptime_duration.days
    hours, remainder = divmod(uptime_duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    else:
        return f"{minutes}m {seconds}s"


def get_system_metrics():
    """
    Collects system performance metrics using the psutil library.
    
    Returns:
        dict containing:
            - cpu_usage: CPU percentage (0.0 to 100.0)
            - ram_usage: Memory percentage (0.0 to 100.0)
            - disk_usage: Primary storage percentage (0.0 to 100.0)
            - uptime: Human-readable system uptime string
    """
    # CPU usage: sampled over a 0.5-second window for responsive and accurate reading
    cpu_usage = psutil.cpu_percent(interval=0.5)

    # RAM usage: calculates percentage based on available physical memory
    ram = psutil.virtual_memory()
    ram_usage = ram.percent

    # Disk usage: determine root mount path dynamically for cross-platform support
    # On Linux root is '/', on Windows root is 'C:\\' (or whatever drive code runs on)
    root_path = os.path.abspath(os.sep)
    disk = psutil.disk_usage(root_path)
    disk_usage = disk.percent

    # System uptime
    uptime = get_system_uptime()

    return {
        "cpu_usage": round(cpu_usage, 1),
        "ram_usage": round(ram_usage, 1),
        "disk_usage": round(disk_usage, 1),
        "uptime": uptime
    }


def collect_and_store_metrics(host=DEFAULT_TARGET_IP, db_name=database.DB_NAME):
    """
    Orchestrates a complete monitoring cycle:
    1. Tests network reachability & latency via ping.
    2. Collects CPU, RAM, Disk, and Uptime via psutil.
    3. Stores the snapshot into the SQLite database.
    4. Returns a combined dictionary of all metrics.
    """
    # 1. Network check
    ping_status, ping_latency = get_ping_latency(host)

    # 2. System metrics
    sys_metrics = get_system_metrics()

    # 3. Store snapshot into SQLite
    database.insert_metrics(
        ping_status=ping_status,
        ping_latency=ping_latency,
        cpu_usage=sys_metrics["cpu_usage"],
        ram_usage=sys_metrics["ram_usage"],
        disk_usage=sys_metrics["disk_usage"],
        db_name=db_name
    )

    # 4. Return combined dictionary
    return {
        "target_ip": host,
        "ping_status": ping_status,
        "ping_latency": ping_latency,
        "cpu_usage": sys_metrics["cpu_usage"],
        "ram_usage": sys_metrics["ram_usage"],
        "disk_usage": sys_metrics["disk_usage"],
        "uptime": sys_metrics["uptime"]
    }


if __name__ == "__main__":
    # Self-test when executed directly: python monitor.py
    print("=" * 50)
    print("Running NetWatch Monitor self-test...")
    print("=" * 50)
    
    # Initialize DB first in case it's not created yet
    database.init_db()

    data = collect_and_store_metrics()
    print(f"Target Host : {data['target_ip']}")
    print(f"Ping Status : {data['ping_status']}")
    print(f"Ping Latency: {data['ping_latency']} ms" if data['ping_latency'] else "Ping Latency: N/A")
    print(f"CPU Usage   : {data['cpu_usage']}%")
    print(f"RAM Usage   : {data['ram_usage']}%")
    print(f"Disk Usage  : {data['disk_usage']}%")
    print(f"Uptime      : {data['uptime']}")
    print("=" * 50)
    print("Metrics collected and stored successfully in SQLite.")
