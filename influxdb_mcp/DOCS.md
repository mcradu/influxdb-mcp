# Configuration

Before starting the app:

1. Create a non-admin InfluxDB user with `READ` on `home_assistant`.
2. Create an OpenAI Secure MCP Tunnel and a runtime API key.
3. Enter the InfluxDB password, tunnel ID, and runtime key in Configuration.
4. Start the app and inspect its logs.

The app never exposes InfluxDB or the MCP HTTP port publicly. Both services bind
inside the app container and tunnel-client initiates the outbound connection.

## InfluxDB permissions

```sql
CREATE USER "chatgpt_mcp" WITH PASSWORD '<generate-locally>';
GRANT READ ON "home_assistant" TO "chatgpt_mcp";
SHOW GRANTS FOR "chatgpt_mcp";
```

## Defaults

- InfluxDB URL: `http://a0d7b954-influxdb:8086`
- Database: `home_assistant`
- Retention policy: `one_year`
- Measurement: `state`
- Maximum query range: 366 days
- Maximum points per entity: 5,000

## Health

Startup fails if the app cannot authenticate to InfluxDB. The logs then show a
sanitized connectivity error; credentials are never printed.
