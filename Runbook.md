# Runbook — Observability & Alerts (Stage 3)

## Alert types
- FAILOVER DETECTED: pool changed (blue→green or green→blue)
  - Action: inspect `docker compose ps`, `docker compose logs app_blue|app_green`, check Nginx logs: `docker compose exec nginx tail /var/log/nginx/access.log`.
  - If unexpected: restart failing app or rollback.

- HIGH ERROR RATE: 5xx > ERROR_RATE_THRESHOLD over WINDOW_SIZE requests
  - Action: inspect app logs, check recent Nginx lines, verify if one pool is misbehaving, consider toggling active pool, restart, or rollback.

## Maintenance mode
- Set `MAINTENANCE_MODE=true` in `.env` or create a toggle file so watcher suppresses alerts during planned toggles.

## Escalation
- If repeated failovers or persistent >10% 5xx for >30 minutes, escalate to backend on-call with logs and timestamps.
