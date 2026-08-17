from typing import Any

import httpx

from influxdb_mcp.config import Settings


class InfluxQueryError(RuntimeError):
    pass


class InfluxClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def query(self, influxql: str, epoch: str = "ms") -> dict[str, Any]:
        endpoint = f"{self.settings.influx_url.rstrip('/')}/query"
        try:
            response = httpx.get(
                endpoint,
                params={
                    "db": self.settings.influx_database,
                    "q": influxql,
                    "epoch": epoch,
                },
                auth=(self.settings.influx_username, self.settings.influx_password),
                verify=self.settings.influx_verify_tls,
                trust_env=False,
                timeout=20.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise InfluxQueryError(f"InfluxDB request failed: {error}") from error

        payload = response.json()
        for result in payload.get("results", []):
            if "error" in result:
                raise InfluxQueryError(f"InfluxDB rejected query: {result['error']}")
        return payload

    def ping(self) -> dict[str, Any]:
        endpoint = f"{self.settings.influx_url.rstrip('/')}/ping"
        try:
            response = httpx.get(
                endpoint,
                auth=(self.settings.influx_username, self.settings.influx_password),
                verify=self.settings.influx_verify_tls,
                trust_env=False,
                timeout=5.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise InfluxQueryError(f"InfluxDB ping failed: {error}") from error
        return {
            "status": "ok",
            "version": response.headers.get("X-Influxdb-Version", "unknown"),
        }


def rows_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in payload.get("results", []):
        for series in result.get("series", []):
            columns = series.get("columns", [])
            for values in series.get("values", []):
                rows.append(dict(zip(columns, values, strict=False)))
    return rows
