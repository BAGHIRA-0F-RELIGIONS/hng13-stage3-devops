#!/usr/bin/env python3
import os, re, time, requests
from collections import deque
from datetime import datetime

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
ERROR_RATE_THRESHOLD = float(os.getenv("ERROR_RATE_THRESHOLD", "2.0"))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "200"))
ALERT_COOLDOWN_SEC = int(os.getenv("ALERT_COOLDOWN_SEC", "300"))
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() in ("1","true","yes")
LOG_PATH = os.getenv("LOG_PATH", "/var/log/nginx/access.log")

LOG_PATTERN = re.compile(r'pool="(?P<pool>[^"]*)"|release="(?P<release>[^"]*)"|upstream_status="(?P<upstream_status>[^"]*)"|upstream_addr="(?P<upstream_addr>[^"]*)"')

window = deque(maxlen=WINDOW_SIZE)
last_pool = None
last_failover_alert_time = None
last_error_alert_time = None

def post_slack(text):
    if MAINTENANCE_MODE:
        print("MAINTENANCE mode ON - skipping alert.")
        return
    if not SLACK_WEBHOOK_URL:
        print("No SLACK_WEBHOOK_URL; alert text:", text)
        return
    payload = {"text": text}
    try:
        r = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        r.raise_for_status()
    except Exception as e:
        print("Slack post failed:", e)

def parse_line(line):
    pool = None; release = None; upstream_status = None; upstream_addr = None
    for m in LOG_PATTERN.finditer(line):
        if m.group('pool'): pool = m.group('pool')
        if m.group('release'): release = m.group('release')
        if m.group('upstream_status'): upstream_status = m.group('upstream_status')
        if m.group('upstream_addr'): upstream_addr = m.group('upstream_addr')
    return {"pool": pool, "release": release, "upstream_status": upstream_status, "upstream_addr": upstream_addr}

def should_alert(last_time):
    if last_time is None: return True
    return (datetime.utcnow() - last_time).total_seconds() > ALERT_COOLDOWN_SEC

def handle_pool_change(pool, release, line):
    global last_pool, last_failover_alert_time
    if pool is None:
        return
    if last_pool is None:
        last_pool = pool
        return
    if pool != last_pool:
        if should_alert(last_failover_alert_time):
            txt = f":rotating_light: Failover detected: {last_pool} -> {pool}\nrelease={release}\nline={line.strip()}"
            post_slack(txt)
            last_failover_alert_time = datetime.utcnow()
        last_pool = pool

def handle_error_rate(up_status, line):
    global last_error_alert_time
    if not up_status: return
    nums = re.findall(r'\d+', up_status)
    if not nums: return
    code = int(nums[0])
    window.append(code)
    if len(window) < WINDOW_SIZE:
        return
    failures = sum(1 for c in window if 500 <= c <= 599)
    rate = (failures / len(window)) * 100.0
    if rate > ERROR_RATE_THRESHOLD and should_alert(last_error_alert_time):
        txt = f":warning: High upstream 5xx rate: {rate:.2f}% over last {len(window)} requests (threshold {ERROR_RATE_THRESHOLD}%).\nMost_recent_line: {line.strip()}"
        post_slack(txt)
        last_error_alert_time = datetime.utcnow()

def follow(file):
    file.seek(0,2)
    while True:
        line = file.readline()
        if not line:
            time.sleep(0.1); continue
        yield line

def main():
    print("Watcher starting, tailing:", LOG_PATH)
    while True:
        try:
            with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                for line in follow(f):
                    p = parse_line(line)
                    handle_pool_change(p.get("pool"), p.get("release"), line)
                    handle_error_rate(p.get("upstream_status"), line)
        except FileNotFoundError:
            print("Log not found, retrying in 1s"); time.sleep(1)
        except Exception as e:
            print("Watcher error:", e); time.sleep(1)

if __name__ == "__main__":
    main()
