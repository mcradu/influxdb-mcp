# InfluxDB MCP for Home Assistant OS

Read-only Model Context Protocol server for Home Assistant, BVB/TradeVille, and
other approved data stored in InfluxDB 1.8. It provides bounded, validated tools
instead of arbitrary InfluxQL.

## Tools

- `influx_health`: check connectivity and report the InfluxDB version.
- `list_entities`: list stored Home Assistant entity object IDs.
- `latest_value`: retrieve the newest stored numeric value.
- `entity_history`: retrieve raw or aggregated history for one entity.
- `compare_entities`: retrieve aligned histories for up to 20 entities.
- `list_databases`, `list_retention_policies`, `list_measurements`: discover schemas.
- `describe_measurement`, `list_tag_values`: inspect fields, tags, and tag values.
- `latest_point`, `series_history`: query bounded generic series such as BVB quotes.

All tools are read-only. Time ranges, result sizes, identifiers, aggregations, and
grouping windows are validated before a query reaches InfluxDB. By default the
server searches every measurement in the configured database and retention policy,
which supports Home Assistant's unit-based measurements such as `%`, `W`, `kWh`,
and `°C`. Set `influx_measurement` to a specific name only when intentionally
restricting access to one measurement.

Generic tools can access only databases listed in `influx_allowed_databases`. The
InfluxDB account must also have `READ` permission on each database. For BVB data:

```sql
GRANT READ ON "tradeville" TO "chatgpt_mcp";
```

`influx_database` and `influx_retention_policy` remain the single Home Assistant
defaults used by the entity tools. Do not put multiple database names in
`influx_database`. Multi-database access is enabled only through
`influx_allowed_databases`; generic tools then select `database` and
`retention_policy` explicitly. A typical configuration is:

```yaml
influx_database: home_assistant
influx_retention_policy: one_year
influx_allowed_databases:
  - home_assistant
  - tradeville
```

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
- Home Assistant entity tools query only the configured default database, retention
  policy, and measurement; generic tools query only explicitly allowlisted databases.
