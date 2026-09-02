"""
database.py - NetWatch Database Layer
======================================
This module handles all database operations using Python's built-in SQLite library.

Key Concepts Explained:
-----------------------
1. What is SQLite?
   SQLite is a self-contained, serverless, zero-configuration SQL database engine.
   Unlike MySQL or PostgreSQL, which require a running background server process,
   SQLite stores the entire database in a single regular file on disk (netwatch.db).
   This makes it ideal for lightweight monitoring tools, embedded devices, and demos.

2. SQL Injection Prevention:
   We use parameterized queries (using '?' placeholders) instead of string formatting.
   This ensures that values are safely treated as data, preventing SQL injection attacks.

3. Context Manager ('with' statement):
   Using 'with sqlite3.connect(...) as conn:' ensures transactions are automatically
   committed upon completion and connections are closed cleanly, avoiding database locks.
"""

import sqlite3
from datetime import datetime

# Default database filename
DB_NAME = "netwatch.db"


def get_connection(db_name=DB_NAME):
    """
    Creates and returns a connection to the SQLite database.
    Setting row_factory to sqlite3.Row allows accessing columns by name
    (like a dictionary: row['cpu_usage']) as well as by index.
    """
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_name=DB_NAME):
    """
    Initializes the database schema if the table does not exist.
    
    Table: metrics
    - id: Unique auto-incrementing record ID.
    - timestamp: Date and time when the measurement was captured.
    - ping_status: Reachability of the target host ('UP' or 'DOWN').
    - ping_latency: Round-trip time in milliseconds (or None if DOWN).
    - cpu_usage: Percentage of CPU currently in use (0.0 to 100.0).
    - ram_usage: Percentage of RAM currently in use (0.0 to 100.0).
    - disk_usage: Percentage of Disk space currently in use (0.0 to 100.0).
    """
    with get_connection(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ping_status TEXT NOT NULL,
                ping_latency REAL,
                cpu_usage REAL NOT NULL,
                ram_usage REAL NOT NULL,
                disk_usage REAL NOT NULL
            )
        """)
        conn.commit()


def insert_metrics(ping_status, ping_latency, cpu_usage, ram_usage, disk_usage, db_name=DB_NAME):
    """
    Inserts a single monitoring snapshot into the metrics table.
    
    Parameters:
        ping_status (str): 'UP' or 'DOWN'
        ping_latency (float or None): Latency in milliseconds
        cpu_usage (float): CPU usage percentage
        ram_usage (float): RAM usage percentage
        disk_usage (float): Disk usage percentage
        db_name (str): Database file path
    """
    # Format timestamp as: YYYY-MM-DD HH:MM:SS
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO metrics (timestamp, ping_status, ping_latency, cpu_usage, ram_usage, disk_usage)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, ping_status, ping_latency, cpu_usage, ram_usage, disk_usage))
        conn.commit()


def get_latest_metrics(limit=10, db_name=DB_NAME):
    """
    Retrieves the most recent N metric records, sorted newest first.
    
    Parameters:
        limit (int): Number of records to return (default: 10)
    
    Returns:
        list[dict]: List of metric records converted to standard Python dictionaries.
    """
    with get_connection(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, ping_status, ping_latency, cpu_usage, ram_usage, disk_usage
            FROM metrics
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        # Convert sqlite3.Row objects to standard dictionaries for easy use in templates
        return [dict(row) for row in rows]


def get_current_metrics(db_name=DB_NAME):
    """
    Retrieves the single most recent metric snapshot.
    
    Returns:
        dict or None: The newest metric dictionary, or None if database is empty.
    """
    records = get_latest_metrics(limit=1, db_name=db_name)
    if records:
        return records[0]
    return None


if __name__ == "__main__":
    # Simple self-test when running 'python database.py' directly
    print("Initializing NetWatch database...")
    init_db()
    print("Database initialized successfully.")
    
    print("Inserting sample record...")
    insert_metrics("UP", 14.5, 32.1, 45.8, 60.2)
    
    latest = get_latest_metrics(5)
    print(f"Retrieved {len(latest)} record(s):")
    for r in latest:
        print(" ", r)
