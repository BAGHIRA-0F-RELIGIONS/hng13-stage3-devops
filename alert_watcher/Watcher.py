#!/usr/bin/env python3
import os
import time
import requests
import re
from collections import deque
from datetime import datetime

# -------------------------------
# Environment Variables
# -------------------------------
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
ERROR_RATE_THRESHOLD = float(os.getenv("ERROR_RATE_THRESHOLD", "2.0"))  # percent
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "200"))
ALERT_COOLDOWN_SEC = int(os.getenv("ALERT_COOLDOWN_SEC", "300"))
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() in ("1", "true", "yes")
LOG_PATH = os.getenv("LOG_PATH", "/var/log/nginx/access.log")

# -------------------------------
# Regex to parse structured log
# Example log line:
# pool="blue" release="1.0.0" upstream_status="200" upstream_addr="172.18.0.3:8080"
# -------------------------------
LOG_PATTERN = re.compile(
    r'pool="(?P<pool>[^"]*)"\s+'
    r'release="(?P<release>[^"]*)"\s+'
    r'upstream_status="(?P<upstream_status>[^"]*)"\s+'
    r'upstream_addr="(?P<upstream_addr>[^"]*)"'
)

# -------------------------------
# State
# -------------------------------
window = deque(maxlen=WINDOW_SIZE)
last_pool = None
last_failover_alert_time = None
last_error_alert_time = None

# -------------------------------
# Helper Functions
# -------------------------------
def post_slack(text: str):
    """Send alert to Slack unless in maintenance mode."""
    if MAINTENANCE_MODE:
        print("[INFO] MAINTENANCE mode ON - skipping alert:", text)
        return
    if not SLACK_WEBHOOK_URL:
        print("[INFO] No SLACK_WEBHOOK_URL configured. Alert text:", text)
        return
    try:
        r = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=5)
        r.raise_for_status()
        print("[INFO] Slack alert sent:", text)
    except Exception as e:
        print("[ERROR] Failed to send Slack alert:", e)

def parse_line(line: str):
    """Parse log line and return dict of pool, release, upstream_status, upstream_addr."""
    m = LOG_PATTERN.search(line)
    if not m:
        return {}
    return {
        "pool": m.group("pool"),
        "release": m.group("release"),
        "upstream_status": m.group("upstream_status"),
        "upstream_addr": m.group("upstream_addr")
    }

def should_alert(last_time: datetime):
    """Check if cooldown period has passed."""
    if last_time is None:
        return True
    return (datetime.utcnow() - last_time).total_seconds() > ALERT_COOLDOWN_SEC

def handle_pool_change(pool, release, line):
    """Detect failover and alert Slack."""
    global last_pool, last_failover_alert_time
    if not pool:
        return
    if last_pool is None:
        last_pool = pool
        return
    if pool != last_pool:
        if should_alert(last_failover_alert_time):
            msg = f":rotating_light: Failover detected: {last_pool} -> {pool}\nrelease={release}\nLog: {line.strip()}"
            post_slack(msg)
            last_failover_alert_time = datetime.utcnow()
        last_pool = pool

def handle_error_rate(upstream_status, line):
    """Check rolling window of upstream responses and alert on high 5xx rate."""
    global last_error_alert_time
    if not upstream_status:
        return
    try:
        code = int(upstream_status)
    except ValueError:
        return
    window.append(code)
    if len(window) < WINDOW_SIZE:
        return
    failures = sum(1 for c in window if 500 <= c <= 599)
    rate = (failures / len(window)) * 100.0
    if rate > ERROR_RATE_THRESHOLD and should_alert(last_error_alert_time):
        msg = f":warning: High upstream 5xx rate: {rate:.2f}% over last {len(window)} requests (threshold {ERROR_RATE_THRESHOLD}%).\nMost recent log: {line.strip()}"
        post_slack(msg)
        last_error_alert_time = datetime.utcnow()

def follow(file):
    """Tail file like 'tail -f'."""
    file.seek(0, 2)  # Move to EOF
    while True:
        line = file.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

# -------------------------------
# Main
# -------------------------------
def main():
    print("[INFO] Watcher starting, tailing:", LOG_PATH)
    while True:
        try:
            with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                for line in follow(f):
                    data = parse_line(line)
                    handle_pool_change(data.get("pool"), data.get("release"), line)
                    handle_error_rate(data.get("upstream_status"), line)
        except FileNotFoundError:
            print("[WARN] Log file not found, retrying in 1s...")
            time.sleep(1)
        except Exception as e:
            print("[ERROR] Watcher encountered exception:", e)
            time.sleep(1)

if __name__ == "__main__":
    main()
