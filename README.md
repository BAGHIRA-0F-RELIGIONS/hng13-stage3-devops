---

````markdown
# 🚀 Blue/Green Deployment with Nginx Auto-Failover + Observability & Slack Alerts

## 🧭 Overview
This project extends the **Stage 2 Blue/Green deployment** by adding **observability and actionable alerts**.  
Nginx logs are instrumented to capture request and pool metadata, while a lightweight **Python log watcher** monitors those logs and sends alerts to **Slack** when:
- Failovers occur (Blue → Green or Green → Blue)
- Upstream error rates exceed a defined threshold

This ensures visibility into system behavior, proactive detection of issues, and confidence in deployment stability.

---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/BAGHIRA-0F-RELIGIONS/hng13-stage3-devops
cd hng13-stage2-devops/
````

### 2. Configure Environment Variables

Create or edit the `.env` file to include:

```bash
# app settings
PORT=8080
BLUE_IMAGE=<your-blue-image>
GREEN_IMAGE=<your-green-image>
RELEASE_ID_BLUE=v1.0
RELEASE_ID_GREEN=v1.1
ACTIVE_POOL=blue

# alert watcher settings
SLACK_WEBHOOK_URL=<your-slack-webhook>
ERROR_RATE_THRESHOLD=2
WINDOW_SIZE=200
ALERT_COOLDOWN_SEC=300
MAINTENANCE_MODE=false
LOG_PATH=/var/log/nginx/access.log
```

You can also view an example in `.env.example`.

---

### 3. Deploy the Stack

```bash
sudo docker-compose up -d --build
```

This command starts:

* **Nginx** (reverse proxy and logger)
* **Blue and Green** app containers
* **Alert Watcher** (Python sidecar container)

---

## 🧪 Chaos & Failover Testing

### 1. Confirm Initial Active Pool (Blue)

```bash
curl http://localhost:8080/version
# Expected: X-App-Pool: blue
```

### 2. Simulate a Failure (Chaos)

Trigger chaos on the Blue container:

```bash
curl -X POST http://localhost:8081/chaos/start
```

Then check again:

```bash
curl http://localhost:8080/version
# Expected: X-App-Pool: green  (automatic failover)
```

### 3. Stop Chaos

```bash
curl -X POST http://localhost:8081/chaos/stop
```

---

## 📊 Viewing Logs & Alerts

### View Nginx Logs

```bash
sudo docker-compose logs -f nginx
```

You should see structured log entries like:

```
pool="blue" release="v1.0" upstream_status="200" upstream_addr="172.20.0.4:8080" request_time="0.005"
```

### View Watcher Logs

```bash
sudo docker-compose logs -f alert_watcher
```

The watcher monitors `/var/log/nginx/access.log` and prints activity to the console.

---

## 💬 Verifying Slack Alerts

You will receive Slack alerts for:

### 1️⃣ Failover Event

```
🚨 Failover detected: blue → green
release=v1.1
```

### 2️⃣ High Error Rate

```
⚠️ High upstream 5xx rate: 4.50% over last 200 requests (threshold 2%)
```

Each alert is rate-limited and respects cooldown settings to avoid spam.

---

## 📸 Required Verification Screenshots

| #   | Screenshot                        | Description                                                                                 |
| --- | --------------------------------- | ------------------------------------------------------------------------------------------- |
| 1️⃣ | **Slack Alert – Failover Event**  | Slack message showing failover detection (e.g., Blue → Green)                               |
| 2️⃣ | **Slack Alert – High Error Rate** | Slack message showing an error-rate breach (> threshold)                                    |
| 3️⃣ | **Container Logs**                | Screenshot of Nginx log lines showing structured log fields (pool, release, upstream, etc.) |

Ensure all screenshots show timestamps, container/service names, and alert content clearly.

---

## 🏗️ Architecture

| Component             | Description                                                 |
| --------------------- | ----------------------------------------------------------- |
| **Nginx**             | Reverse proxy with upstream failover and custom logging     |
| **Blue Service**      | Primary application instance (port 8081)                    |
| **Green Service**     | Backup application instance (port 8082)                     |
| **Alert Watcher**     | Python process that tails Nginx logs and posts Slack alerts |
| **Shared Volume**     | `/var/log/nginx` shared between Nginx and watcher           |
| **Slack Integration** | Notifies of failovers and high error rates                  |

---

## ✨ Key Features

* ✅ Automatic health-based Blue/Green failover
* ✅ Real-time log monitoring & Slack alerts
* ✅ Configurable thresholds via environment variables
* ✅ Alert cooldown and maintenance mode support
* ✅ Zero modification to app images

---

## 🧰 Tech Stack

* **Nginx** — Load balancing & access logging
* **Python** — Log watcher (Slack alerting)
* **Docker Compose** — Container orchestration
* **Slack API** — Incoming Webhook integration

---

**Author:** [Bahir Momodu](https://github.com/BAGHIRA-0F-RELIGIONS)
**Track:** HNG 13 — DevOps
**Stage:** Stage 3 — Observability & Alerts (Blue/Green)

```

