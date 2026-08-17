# InfluxDB MCP for Home Assistant OS

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

## Install on Home Assistant OS

Add this repository in **Settings → Apps → App store → Repositories**:

```text
https://github.com/mcradu/influxdb-mcp
```

Install **InfluxDB MCP**, fill its Configuration page, start it, and inspect the
logs. The repository must be accessible to Home Assistant when it refreshes the
app store.

## Local development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e './influxdb_mcp[dev]'
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

## Secure MCP Tunnel

The app bundles the official OpenAI `tunnel-client` v0.0.11. Tunnel ID and runtime
API key are entered through the Home Assistant app configuration and are stored
by Supervisor, never in this repository. Once healthy, create a developer-mode
app in ChatGPT, choose **Tunnel**, and select the same tunnel.

## Operational limits

- Default maximum range: 366 days.
- Default maximum result size: 5,000 points per entity.
- Maximum comparison width: 20 entities.
- Supported aggregation windows: seconds, minutes, hours, days, and weeks.
- Only the configured database, retention policy, and measurement are queried.
