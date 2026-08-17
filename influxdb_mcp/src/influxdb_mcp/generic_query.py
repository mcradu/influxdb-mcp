from typing import Any

from influxdb_mcp.config import Settings
from influxdb_mcp.query import Aggregation, format_time, validate_range, validate_window


def quote_identifier(value: str) -> str:
    Settings.validate_identifier(value)
    return f'"{value}"'


def quote_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def qualified_measurement(database: str, retention_policy: str, measurement: str) -> str:
    return ".".join(
        quote_identifier(value) for value in (database, retention_policy, measurement)
    )


def require_allowed_database(settings: Settings, database: str) -> str:
    return settings.require_database_allowed(database)


def build_list_databases_query() -> str:
    return "SHOW DATABASES"


def build_list_retention_policies_query(settings: Settings, database: str) -> str:
    database = require_allowed_database(settings, database)
    return f"SHOW RETENTION POLICIES ON {quote_identifier(database)}"


def build_list_measurements_query(settings: Settings, database: str, limit: int) -> str:
    database = require_allowed_database(settings, database)
    safe_limit = min(max(limit, 1), settings.mcp_max_points)
    return f"SHOW MEASUREMENTS ON {quote_identifier(database)} LIMIT {safe_limit}"


def build_field_keys_query(settings: Settings, database: str, measurement: str) -> str:
    database = require_allowed_database(settings, database)
    return (
        f"SHOW FIELD KEYS ON {quote_identifier(database)} "
        f"FROM {quote_identifier(measurement)}"
    )


def build_tag_keys_query(settings: Settings, database: str, measurement: str) -> str:
    database = require_allowed_database(settings, database)
    return (
        f"SHOW TAG KEYS ON {quote_identifier(database)} "
        f"FROM {quote_identifier(measurement)}"
    )


def build_tag_values_query(
    settings: Settings, database: str, measurement: str, tag: str, limit: int
) -> str:
    database = require_allowed_database(settings, database)
    safe_limit = min(max(limit, 1), settings.mcp_max_points)
    return (
        f"SHOW TAG VALUES ON {quote_identifier(database)} "
        f"FROM {quote_identifier(measurement)} WITH KEY = {quote_identifier(tag)} "
        f"LIMIT {safe_limit}"
    )


def build_tag_filter(tag_filters: dict[str, str] | None) -> str:
    if not tag_filters:
        return ""
    if len(tag_filters) > 20:
        raise ValueError("tag_filters cannot contain more than 20 entries")
    clauses = [
        f"{quote_identifier(tag)} = {quote_value(str(value))}"
        for tag, value in sorted(tag_filters.items())
    ]
    return " AND ".join(clauses)


def validate_fields(fields: list[str]) -> list[str]:
    if not fields or len(fields) > 20:
        raise ValueError("fields must contain between 1 and 20 names")
    for field in fields:
        Settings.validate_identifier(field)
    return list(dict.fromkeys(fields))


def build_generic_history_query(
    settings: Settings,
    database: str,
    retention_policy: str,
    measurement: str,
    fields: list[str],
    tag_filters: dict[str, str] | None,
    start: str,
    end: str,
    aggregation: Aggregation,
    window: str,
    limit: int,
) -> str:
    database = require_allowed_database(settings, database)
    fields = validate_fields(fields)
    start_time, end_time = validate_range(start, end, settings)
    safe_limit = min(max(limit, 1), settings.mcp_max_points)
    filters = build_tag_filter(tag_filters)
    time_filter = (
        f"time >= '{format_time(start_time)}' AND time < '{format_time(end_time)}'"
    )
    where = f"{filters} AND {time_filter}" if filters else time_filter
    source = qualified_measurement(database, retention_policy, measurement)
    if aggregation == Aggregation.RAW:
        select = ", ".join(quote_identifier(field) for field in fields)
        return (
            f"SELECT {select} FROM {source} WHERE {where} "
            f"ORDER BY time ASC LIMIT {safe_limit}"
        )
    if len(fields) != 1:
        raise ValueError("aggregated requests require exactly one field")
    safe_window = validate_window(window)
    field = quote_identifier(fields[0])
    return (
        f"SELECT {aggregation.value}({field}) AS {field} FROM {source} WHERE {where} "
        f"GROUP BY time({safe_window}) fill(none) ORDER BY time ASC LIMIT {safe_limit}"
    )


def build_generic_latest_query(
    settings: Settings,
    database: str,
    retention_policy: str,
    measurement: str,
    fields: list[str],
    tag_filters: dict[str, str] | None,
) -> str:
    database = require_allowed_database(settings, database)
    fields = validate_fields(fields)
    source = qualified_measurement(database, retention_policy, measurement)
    select = ", ".join(quote_identifier(field) for field in fields)
    filters = build_tag_filter(tag_filters)
    where = f" WHERE {filters}" if filters else ""
    return f"SELECT {select} FROM {source}{where} ORDER BY time DESC LIMIT 1"


def rows_with_values(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if any(key not in {"time", "measurement", "tags"} for key in row)]
