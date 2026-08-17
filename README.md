# InfluxDB MCP

Read-only Model Context Protocol server for Home Assistant history stored in
InfluxDB 1.8. It provides bounded, validated tools instead of arbitrary InfluxQL.

## Tools

- `influx_health`: check connectivity and report the InfluxDB version.
- `list_entities`: list stored Home Assistant entity object IDs.
- `latest_value`: retrieve the newest stored numeric value.
- `entity_history`: retrieve raw or aggregated history for one entity.
- `compare_entities`: retrieve aligned histories for up to 20 entities.

All tools are read-only. Time ranges, result sizes, identifiers, aggregations, and
grouping windows are validated before a query reaches InfluxDB.

## InfluxDB account

Enable authentication and create a dedicated non-admin account in Chronograf or
the InfluxDB shell:

```sql
CREATE USER "chatgpt_mcp" WITH PASSWORD '<generate-locally>';
GRANT READ ON "home_assistant" TO "chatgpt_mcp";
SHOW GRANTS FOR "chatgpt_mcp";
```

Do not commit the password. Copy `.env.example` to `.env` on the deployment host
and fill it locally.

## Local development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
ruff check .
```

Run the server:

```bash
influxdb-mcp
```

The streamable HTTP MCP endpoint is available at:

```text
http://127.0.0.1:8000/mcp
```

The health endpoint is:

```text
http://127.0.0.1:8000/health
```

## Docker deployment

The Compose file expects an existing Docker network that can resolve the Home
Assistant add-on hostname `a0d7b954-influxdb`. Set `HA_DOCKER_NETWORK` in `.env`
if that network is not named `hassio`.

```bash
cp .env.example .env
docker compose config
docker compose build
docker compose up -d
docker compose logs --tail=100 influxdb-mcp
curl --fail http://127.0.0.1:8000/health
```

The published port binds only to loopback. Do not publish InfluxDB port 8086.

## Secure MCP Tunnel

Use OpenAI Secure MCP Tunnel so the private MCP server does not need public
ingress. Create a tunnel in OpenAI Platform and run `tunnel-client` inside the
same network boundary with the local MCP URL:

```bash
export CONTROL_PLANE_API_KEY='<set-locally>'

tunnel-client init \
  --sample sample_mcp_http_local \
  --profile influxdb-mcp \
  --tunnel-id '<tunnel_id>' \
  --mcp-server-url http://127.0.0.1:8000/mcp

tunnel-client doctor --profile influxdb-mcp --explain
tunnel-client run --profile influxdb-mcp
```

Keep the API key outside Git. Once the client is healthy, create a developer-mode
app in ChatGPT, choose **Tunnel**, and select the same tunnel.

## Operational limits

- Default maximum range: 366 days.
- Default maximum result size: 5,000 points per entity.
- Maximum comparison width: 20 entities.
- Supported aggregation windows: seconds, minutes, hours, days, and weeks.
- Only the configured database, retention policy, and measurement are queried.

