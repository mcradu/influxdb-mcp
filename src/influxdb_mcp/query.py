import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from influxdb_mcp.config import Settings

ENTITY_ID_PATTERN = re.compile(r"^[a-z0-9_]+(?:\.[a-z0-9_]+)?$")
WINDOW_PATTERN = re.compile(r"^[1-9][0-9]*(?:s|m|h|d|w)$")


class Aggregation(StrEnum):
    RAW = "raw"
    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    FIRST = "first"
    LAST = "last"
    MEDIAN = "median"


def parse_time(value: str, field_name: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone")
    return parsed.astimezone(UTC)


def format_time(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def validate_range(start: str, end: str, settings: Settings) -> tuple[datetime, datetime]:
    start_time = parse_time(start, "start")
    end_time = parse_time(end, "end")
    if start_time >= end_time:
        raise ValueError("start must be earlier than end")
    if end_time - start_time > timedelta(days=settings.mcp_max_range_days):
        raise ValueError(f"time range exceeds {settings.mcp_max_range_days} days")
    if end_time > datetime.now(UTC) + timedelta(minutes=5):
        raise ValueError("end cannot be in the future")
    return start_time, end_time


def normalize_entity_id(entity_id: str) -> tuple[str | None, str]:
    normalized = entity_id.strip().lower()
    if not ENTITY_ID_PATTERN.fullmatch(normalized):
        raise ValueError("entity_id contains unsupported characters")
    if "." in normalized:
        domain, object_id = normalized.split(".", 1)
        return domain, object_id
    return None, normalized


def entity_filter(entity_id: str) -> str:
    domain, object_id = normalize_entity_id(entity_id)
    clauses = [f'"entity_id" = \'{object_id}\'']
    if domain:
        clauses.append(f'"domain" = \'{domain}\'')
    return " AND ".join(clauses)


def validate_window(window: str) -> str:
    normalized = window.strip().lower()
    if not WINDOW_PATTERN.fullmatch(normalized):
        raise ValueError("window must look like 30s, 5m, 1h, or 1d")
    return normalized


def build_history_query(
    settings: Settings,
    entity_id: str,
    start: str,
    end: str,
    aggregation: Aggregation,
    window: str,
    limit: int,
) -> str:
    start_time, end_time = validate_range(start, end, settings)
    safe_limit = min(max(limit, 1), settings.mcp_max_points)
    where = (
        f"{entity_filter(entity_id)} "
        f"AND time >= '{format_time(start_time)}' AND time < '{format_time(end_time)}'"
    )
    measurement = settings.qualified_measurement
    if aggregation == Aggregation.RAW:
        return (
            f'SELECT "value" FROM {measurement} WHERE {where} '
            f"ORDER BY time ASC LIMIT {safe_limit}"
        )
    safe_window = validate_window(window)
    return (
        f'SELECT {aggregation.value}("value") AS "value" FROM {measurement} '
        f"WHERE {where} GROUP BY time({safe_window}) fill(none) "
        f"ORDER BY time ASC LIMIT {safe_limit}"
    )


def build_entity_list_query(settings: Settings, limit: int) -> str:
    safe_limit = min(max(limit, 1), settings.mcp_max_points)
    return (
        f'SHOW TAG VALUES FROM {settings.qualified_measurement} '
        f'WITH KEY = "entity_id" LIMIT {safe_limit}'
    )


def build_latest_query(settings: Settings, entity_id: str) -> str:
    return (
        f'SELECT last("value") AS "value" FROM {settings.qualified_measurement} '
        f"WHERE {entity_filter(entity_id)}"
    )
