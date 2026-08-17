from datetime import UTC, datetime, timedelta

import pytest

from influxdb_mcp.config import Settings
from influxdb_mcp.query import (
    Aggregation,
    build_history_query,
    entity_filter,
    validate_window,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        influx_username="reader",
        influx_password="secret",
        mcp_max_range_days=31,
        mcp_max_points=100,
    )


def test_entity_filter_supports_full_entity_id() -> None:
    assert entity_filter("sensor.ss_battery_soc") == (
        '"entity_id" = \'ss_battery_soc\' AND "domain" = \'sensor\''
    )


def test_entity_filter_supports_object_id() -> None:
    assert entity_filter("ss_battery_soc") == '"entity_id" = \'ss_battery_soc\''


@pytest.mark.parametrize("unsafe", ["x' OR true", "sensor.x;drop", "../x"])
def test_entity_filter_rejects_unsafe_values(unsafe: str) -> None:
    with pytest.raises(ValueError):
        entity_filter(unsafe)


def test_entity_filter_normalizes_case() -> None:
    assert entity_filter("Sensor.SS_Battery_SOC") == (
        '"entity_id" = \'ss_battery_soc\' AND "domain" = \'sensor\''
    )


def test_build_history_query_is_bounded(settings: Settings) -> None:
    end = datetime.now(UTC) - timedelta(minutes=1)
    start = end - timedelta(days=1)
    query = build_history_query(
        settings,
        "sensor.ss_battery_soc",
        start.isoformat(),
        end.isoformat(),
        Aggregation.MEAN,
        "1h",
        9999,
    )
    assert 'mean("value")' in query
    assert "GROUP BY time(1h) fill(none)" in query
    assert "LIMIT 100" in query
    assert "ss_battery_soc" in query


def test_range_limit_is_enforced(settings: Settings) -> None:
    end = datetime.now(UTC) - timedelta(minutes=1)
    start = end - timedelta(days=32)
    with pytest.raises(ValueError, match="exceeds 31 days"):
        build_history_query(
            settings,
            "sensor.ss_battery_soc",
            start.isoformat(),
            end.isoformat(),
            Aggregation.MEAN,
            "1h",
            10,
        )


@pytest.mark.parametrize("window", ["0m", "1 month", "1h;drop", "-1h"])
def test_window_rejects_unsafe_values(window: str) -> None:
    with pytest.raises(ValueError):
        validate_window(window)
