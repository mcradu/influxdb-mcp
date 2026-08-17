from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from influxdb_mcp.client import InfluxClient, rows_from_payload
from influxdb_mcp.config import get_settings
from influxdb_mcp.generic_query import (
    build_field_keys_query,
    build_generic_history_query,
    build_generic_latest_query,
    build_list_databases_query,
    build_list_measurements_query,
    build_list_retention_policies_query,
    build_tag_keys_query,
    build_tag_values_query,
    rows_with_values,
)
from influxdb_mcp.query import (
    Aggregation,
    build_entity_list_query,
    build_history_query,
    build_latest_query,
)

settings = get_settings()
client = InfluxClient(settings)


mcp = FastMCP(
    "Read-only InfluxDB Explorer",
    instructions=(
        "Read-only bounded access to allowed InfluxDB databases and Home Assistant history. "
        "Use entity IDs without the sensor. prefix when that is how InfluxDB stores them. "
        "Never claim that these tools can modify or delete data."
    ),
    host=settings.mcp_host,
    port=settings.mcp_port,
)


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    try:
        result = client.ping()
        return JSONResponse({"status": "ok", "influxdb": result})
    except Exception as error:
        return JSONResponse({"status": "error", "detail": str(error)}, status_code=503)


@mcp.tool()
def influx_health() -> dict[str, Any]:
    """Check connectivity and report the InfluxDB server version."""
    return client.ping()


@mcp.tool()
def list_databases() -> list[str]:
    """List InfluxDB databases visible to the read-only account and allowed by MCP."""
    rows = rows_from_payload(client.query(build_list_databases_query()))
    visible = {str(row["name"]) for row in rows if row.get("name")}
    return sorted(visible.intersection(settings.influx_allowed_databases))


@mcp.tool()
def list_retention_policies(database: str) -> list[dict[str, Any]]:
    """List retention policies for one allowed database."""
    query = build_list_retention_policies_query(settings, database)
    return rows_from_payload(client.query(query))


@mcp.tool()
def list_measurements(database: str, limit: int = 1000) -> list[str]:
    """List measurements in one allowed database."""
    query = build_list_measurements_query(settings, database, limit)
    rows = rows_from_payload(client.query(query))
    return sorted({str(row["name"]) for row in rows if row.get("name")})


@mcp.tool()
def describe_measurement(database: str, measurement: str) -> dict[str, Any]:
    """List field keys and tag keys for a measurement in an allowed database."""
    field_rows = rows_from_payload(
        client.query(build_field_keys_query(settings, database, measurement))
    )
    tag_rows = rows_from_payload(
        client.query(build_tag_keys_query(settings, database, measurement))
    )
    return {
        "database": database,
        "measurement": measurement,
        "fields": field_rows,
        "tags": tag_rows,
    }


@mcp.tool()
def list_tag_values(
    database: str, measurement: str, tag: str, limit: int = 1000
) -> list[str]:
    """List values of one tag in a measurement from an allowed database."""
    query = build_tag_values_query(settings, database, measurement, tag, limit)
    rows = rows_from_payload(client.query(query))
    return sorted({str(row["value"]) for row in rows if row.get("value") is not None})


@mcp.tool()
def latest_point(
    database: str,
    retention_policy: str,
    measurement: str,
    fields: list[str],
    tag_filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return the newest point from a bounded series in an allowed database."""
    query = build_generic_latest_query(
        settings, database, retention_policy, measurement, fields, tag_filters
    )
    rows = rows_with_values(
        rows_from_payload(client.query(query), include_measurement=True, include_tags=True)
    )
    point = max(rows, key=lambda row: row.get("time", 0), default=None)
    return {
        "database": database,
        "retention_policy": retention_policy,
        "measurement": measurement,
        "point": point,
    }


@mcp.tool()
def series_history(
    database: str,
    retention_policy: str,
    measurement: str,
    fields: list[str],
    start: str,
    end: str,
    tag_filters: dict[str, str] | None = None,
    aggregation: Aggregation = Aggregation.RAW,
    window: str = "5m",
    limit: int = 1000,
) -> dict[str, Any]:
    """Read bounded raw or aggregated history from an allowed InfluxDB series."""
    query = build_generic_history_query(
        settings,
        database,
        retention_policy,
        measurement,
        fields,
        tag_filters,
        start,
        end,
        aggregation,
        window,
        limit,
    )
    rows = rows_with_values(
        rows_from_payload(client.query(query), include_measurement=True, include_tags=True)
    )
    rows.sort(key=lambda row: row.get("time", 0))
    safe_limit = min(max(limit, 1), settings.mcp_max_points)
    return {
        "database": database,
        "retention_policy": retention_policy,
        "measurement": measurement,
        "aggregation": aggregation.value,
        "window": None if aggregation == Aggregation.RAW else window,
        "points": rows,
        "count": len(rows),
        "truncated": len(rows) >= safe_limit,
    }


@mcp.tool()
def list_entities(limit: int = 1000) -> list[str]:
    """List Home Assistant entity object IDs stored in the configured measurements."""
    payload = client.query(build_entity_list_query(settings, limit))
    entities = {
        str(row["value"]) for row in rows_from_payload(payload) if row.get("value")
    }
    safe_limit = min(max(limit, 1), settings.mcp_max_points)
    return sorted(entities)[:safe_limit]


@mcp.tool()
def latest_value(entity_id: str) -> dict[str, Any]:
    """Return the most recent stored numeric value for one Home Assistant entity."""
    payload = client.query(build_latest_query(settings, entity_id))
    rows = rows_from_payload(payload, include_measurement=True)
    point = max(rows, key=lambda row: row.get("time", 0), default=None)
    return {"entity_id": entity_id, "point": point}


@mcp.tool()
def entity_history(
    entity_id: str,
    start: str,
    end: str,
    aggregation: Aggregation = Aggregation.MEAN,
    window: str = "5m",
    limit: int = 1000,
) -> dict[str, Any]:
    """Read bounded history for an entity between ISO-8601 timestamps.

    Use aggregation='raw' for raw points. Aggregated requests accept windows such as
    30s, 5m, 1h, or 1d. Timestamps must contain a timezone.
    """
    query = build_history_query(
        settings, entity_id, start, end, aggregation, window, limit
    )
    rows = rows_from_payload(client.query(query), include_measurement=True)
    rows.sort(key=lambda row: row.get("time", 0))
    return {
        "entity_id": entity_id,
        "aggregation": aggregation.value,
        "window": None if aggregation == Aggregation.RAW else window,
        "points": rows,
        "count": len(rows),
        "truncated": len(rows) >= min(max(limit, 1), settings.mcp_max_points),
    }


@mcp.tool()
def compare_entities(
    entity_ids: list[str],
    start: str,
    end: str,
    aggregation: Aggregation = Aggregation.MEAN,
    window: str = "1h",
    limit_per_entity: int = 1000,
) -> dict[str, Any]:
    """Read aligned, aggregated histories for up to 20 Home Assistant entities."""
    if not entity_ids or len(entity_ids) > 20:
        raise ValueError("entity_ids must contain between 1 and 20 values")
    series: dict[str, list[dict[str, Any]]] = {}
    for entity_id in entity_ids:
        query = build_history_query(
            settings,
            entity_id,
            start,
            end,
            aggregation,
            window,
            limit_per_entity,
        )
        rows = rows_from_payload(client.query(query), include_measurement=True)
        rows.sort(key=lambda row: row.get("time", 0))
        series[entity_id] = rows
    return {
        "aggregation": aggregation.value,
        "window": None if aggregation == Aggregation.RAW else window,
        "series": series,
    }


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
