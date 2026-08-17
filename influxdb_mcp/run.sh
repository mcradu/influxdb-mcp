#!/usr/bin/env bash
set -Eeuo pipefail

OPTIONS=/data/options.json

read_option() {
  jq -er --arg key "$1" '.[$key]' "${OPTIONS}"
}

export INFLUX_URL="$(read_option influx_url)"
export INFLUX_DATABASE="$(read_option influx_database)"
export INFLUX_RETENTION_POLICY="$(read_option influx_retention_policy)"
export INFLUX_MEASUREMENT="$(read_option influx_measurement)"
export INFLUX_USERNAME="$(read_option influx_username)"
export INFLUX_PASSWORD="$(read_option influx_password)"
export INFLUX_VERIFY_TLS="$(read_option influx_verify_tls)"
export MCP_HOST=127.0.0.1
export MCP_PORT=8000
export MCP_MAX_RANGE_DAYS="$(read_option max_range_days)"
export MCP_MAX_POINTS="$(read_option max_points)"

export CONTROL_PLANE_TUNNEL_ID="$(read_option control_plane_tunnel_id)"
export CONTROL_PLANE_API_KEY="$(read_option control_plane_api_key)"
export MCP_SERVER_URL=http://127.0.0.1:8000/mcp
export HEALTH_LISTEN_ADDR=127.0.0.1:8080
export LOG_LEVEL="$(read_option log_level)"
export LOG_FORMAT=json

influxdb-mcp &
MCP_PID=$!

shutdown() {
  kill -TERM "${MCP_PID}" 2>/dev/null || true
  wait "${MCP_PID}" 2>/dev/null || true
}
trap shutdown EXIT INT TERM

for attempt in $(seq 1 30); do
  if ! kill -0 "${MCP_PID}" 2>/dev/null; then
    echo "InfluxDB MCP stopped during startup" >&2
    exit 1
  fi
  if curl --fail --silent http://127.0.0.1:8000/health >/dev/null; then
    break
  fi
  if [[ "${attempt}" == 30 ]]; then
    echo "InfluxDB MCP health check did not become ready" >&2
    exit 1
  fi
  sleep 1
done

exec tunnel-client run
