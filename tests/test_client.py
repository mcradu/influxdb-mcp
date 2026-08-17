import httpx
import respx
from influxdb_mcp.client import InfluxClient, rows_from_payload
from influxdb_mcp.config import Settings


def settings() -> Settings:
    return Settings(influx_username="reader", influx_password="secret")


@respx.mock
def test_ping_reads_influx_version() -> None:
    respx.get("http://a0d7b954-influxdb:8086/ping").mock(
        return_value=httpx.Response(204, headers={"X-Influxdb-Version": "1.8.10"})
    )
    assert InfluxClient(settings()).ping() == {"status": "ok", "version": "1.8.10"}


def test_rows_from_payload() -> None:
    payload = {
        "results": [
            {
                "series": [
                    {
                        "columns": ["time", "value"],
                        "values": [[1, 45.0], [2, 46.0]],
                    }
                ]
            }
        ]
    }
    assert rows_from_payload(payload) == [
        {"time": 1, "value": 45.0},
        {"time": 2, "value": 46.0},
    ]


def test_rows_from_payload_can_include_measurement() -> None:
    payload = {
        "results": [
            {
                "series": [
                    {
                        "name": "%",
                        "columns": ["time", "value"],
                        "values": [[1, 45.0]],
                    }
                ]
            }
        ]
    }
    assert rows_from_payload(payload, include_measurement=True) == [
        {"time": 1, "value": 45.0, "measurement": "%"}
    ]
