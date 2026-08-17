from datetime import UTC, datetime, timedelta

import pytest
from influxdb_mcp.config import Settings
from influxdb_mcp.generic_query import (
    build_generic_history_query,
    build_generic_latest_query,
    build_list_measurements_query,
    build_list_retention_policies_query,
    build_tag_values_query,
    quote_value,
)
from influxdb_mcp.query import Aggregation


@pytest.fixture
def settings() -> Settings:
    return Settings(
        influx_username="reader",
        influx_password="secret",
        influx_allowed_databases=["home_assistant", "tradeville"],
        mcp_max_range_days=31,
        mcp_max_points=100,
    )


def test_database_metadata_queries_are_bounded_to_allowlist(settings: Settings) -> None:
    assert build_list_retention_policies_query(settings, "tradeville") == (
        'SHOW RETENTION POLICIES ON "tradeville"'
    )
    assert build_list_measurements_query(settings, "tradeville", 999) == (
        'SHOW MEASUREMENTS ON "tradeville" LIMIT 100'
    )
    assert build_tag_values_query(
        settings, "tradeville", "tradeville_quotes", "symbol", 50
    ) == (
        'SHOW TAG VALUES ON "tradeville" FROM "tradeville_quotes" '
        'WITH KEY = "symbol" LIMIT 50'
    )


def test_disallowed_database_is_rejected(settings: Settings) -> None:
    with pytest.raises(ValueError, match="not allowed"):
        build_list_measurements_query(settings, "_internal", 10)


def test_latest_bvb_quote_query(settings: Settings) -> None:
    query = build_generic_latest_query(
        settings,
        "tradeville",
        "autogen",
        "tradeville_quotes",
        ["price", "bid", "ask"],
        {"symbol": "TLV.RO"},
    )
    assert query == (
        'SELECT "price", "bid", "ask" '
        'FROM "tradeville"."autogen"."tradeville_quotes" '
        'WHERE "symbol" = \'TLV.RO\' ORDER BY time DESC LIMIT 1'
    )


def test_raw_bvb_history_query(settings: Settings) -> None:
    end = datetime.now(UTC) - timedelta(minutes=1)
    start = end - timedelta(days=1)
    query = build_generic_history_query(
        settings,
        "tradeville",
        "autogen",
        "tradeville_quotes",
        ["price"],
        {"symbol": "SNP.RO"},
        start.isoformat(),
        end.isoformat(),
        Aggregation.RAW,
        "5m",
        50,
    )
    assert 'SELECT "price" FROM "tradeville"."autogen"."tradeville_quotes"' in query
    assert '"symbol" = \'SNP.RO\'' in query
    assert "ORDER BY time ASC LIMIT 50" in query


def test_aggregated_query_requires_one_field(settings: Settings) -> None:
    end = datetime.now(UTC) - timedelta(minutes=1)
    start = end - timedelta(hours=1)
    with pytest.raises(ValueError, match="exactly one field"):
        build_generic_history_query(
            settings,
            "tradeville",
            "autogen",
            "tradeville_quotes",
            ["price", "bid"],
            {"symbol": "TLV.RO"},
            start.isoformat(),
            end.isoformat(),
            Aggregation.MEAN,
            "5m",
            50,
        )


def test_tag_value_is_escaped() -> None:
    assert quote_value("O'Reilly\\test") == "'O\\'Reilly\\\\test'"
