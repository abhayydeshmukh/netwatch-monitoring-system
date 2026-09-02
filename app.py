"""
app.py - NetWatch Flask Web Application
=========================================
This is the main entry point for the NetWatch monitoring web dashboard.

Key Concepts Explained:
-----------------------
1. What is Flask?
   Flask is a lightweight "micro" web framework for Python.
   - It provides URL routing, request handling, and response delivery.
   - It uses Jinja2 as its template engine to dynamically inject Python variables into HTML.
   - It relies on WSGI (Web Server Gateway Interface), the standard specification
     defining how Python applications interact with web servers.

2. Server-Side Rendering (SSR):
   When a user accesses the dashboard in their browser:
   a. The browser sends an HTTP GET request to '/'
   b. Flask executes the 'index()' function
   c. The function collects live server & network metrics, saves them to SQLite
   d. The function checks alert threshold rules
   e. Jinja2 combines 'index.html' with the dynamic data to produce pure HTML
   f. The browser receives and renders the ready-to-view HTML page.

3. Alert Evaluation:
   Instead of running complex background message brokers (like Celery/Redis),
   we evaluate alert conditions directly when metrics are gathered:
   - CPU > 80%
   - RAM > 80%
   - Disk > 80%
   - Ping == 'DOWN'
"""

from datetime import datetime
from flask import Flask, render_template, jsonify, request
import database
import monitor

# Initialize Flask application
app = Flask(__name__)

# Configurable alert thresholds
CPU_ALERT_THRESHOLD = 80.0    # Warning if CPU usage > 80%
RAM_ALERT_THRESHOLD = 80.0    # Warning if RAM usage > 80%
DISK_ALERT_THRESHOLD = 80.0   # Warning if Disk usage > 80%
DEFAULT_TARGET_IP = "8.8.8.8" # Default IP to ping (Google Public DNS)


def evaluate_alerts(metrics):
    """
    Evaluates monitoring metrics against defined threshold limits.
    
    Parameters:
        metrics (dict): Current monitoring snapshot
        
    Returns:
        list[str]: List of human-readable alert warning messages.
    """
    alerts = []

    # 1. Network Alert: Ping status check
    if metrics.get("ping_status") == "DOWN":
        alerts.append(f"Network Alert: Ping failed! Target host ({metrics.get('target_ip')}) is UNREACHABLE.")

    # 2. CPU Alert
    cpu = metrics.get("cpu_usage", 0.0)
    if cpu > CPU_ALERT_THRESHOLD:
        alerts.append(f"High CPU Usage Warning: {cpu}% exceeds safe threshold ({CPU_ALERT_THRESHOLD}%).")

    # 3. RAM Alert
    ram = metrics.get("ram_usage", 0.0)
    if ram > RAM_ALERT_THRESHOLD:
        alerts.append(f"High Memory (RAM) Usage Warning: {ram}% exceeds safe threshold ({RAM_ALERT_THRESHOLD}%).")

    # 4. Disk Alert
    disk = metrics.get("disk_usage", 0.0)
    if disk > DISK_ALERT_THRESHOLD:
        alerts.append(f"High Disk Usage Warning: {disk}% exceeds safe threshold ({DISK_ALERT_THRESHOLD}%).")

    return alerts


@app.route("/")
def index():
    """
    Dashboard Home Route.
    Triggered whenever a user opens or refreshes the page.
    1. Reads target IP (allows optional ?ip=x.x.x.x query parameter).
    2. Collects live system and network metrics.
    3. Saves data to SQLite.
    4. Evaluates alert conditions.
    5. Retrieves the latest 10 historical records from SQLite.
    6. Renders index.html with current metrics, alerts, and history.
    """
    # Allow overriding target IP via query parameter, e.g. /?ip=1.1.1.1
    target_ip = request.args.get("ip", DEFAULT_TARGET_IP)

    # 1. Collect live metrics and save to SQLite
    current_data = monitor.collect_and_store_metrics(host=target_ip)
    
    # Attach formatted timestamp for display
    current_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 2. Evaluate warnings/alerts
    alerts = evaluate_alerts(current_data)

    # 3. Retrieve recent history (last 10 records) from SQLite
    history = database.get_latest_metrics(limit=10)

    # 4. Render the web page template
    return render_template(
        "index.html",
        current=current_data,
        alerts=alerts,
        history=history
    )


@app.route("/api/metrics")
def api_metrics():
    """
    JSON API endpoint.
    Useful for demonstrating RESTful API concepts in an interview.
    Returns the latest monitoring snapshot as JSON.
    """
    target_ip = request.args.get("ip", DEFAULT_TARGET_IP)
    data = monitor.collect_and_store_metrics(host=target_ip)
    alerts = evaluate_alerts(data)
    data["alerts"] = alerts
    return jsonify(data)


if __name__ == "__main__":
    # Ensure database and table are initialized before running server
    database.init_db()

    print("=" * 60)
    print(" NetWatch Monitoring Server is starting...")
    print(" Dashboard URL: http://127.0.0.1:5000")
    print(" Press Ctrl+C to stop the server.")
    print("=" * 60)

    # Run Flask development server
    # host='0.0.0.0' allows external access from local network or VMs
    # port=5000 is the standard Flask port
    app.run(host="0.0.0.0", port=5000, debug=True)
