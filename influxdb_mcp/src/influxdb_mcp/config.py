from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    influx_url: str = "http://a0d7b954-influxdb:8086"
    influx_database: str = "home_assistant"
    influx_retention_policy: str = "one_year"
    influx_measurement: str = "*"
    influx_allowed_databases: list[str] = Field(
        default_factory=lambda: ["home_assistant", "tradeville"]
    )
    influx_username: str
    influx_password: str
    influx_verify_tls: bool = True
    mcp_host: str = "0.0.0.0"
    mcp_port: int = Field(default=8000, ge=1, le=65535)
    mcp_max_range_days: int = Field(default=366, ge=1, le=3650)
    mcp_max_points: int = Field(default=5000, ge=10, le=50000)

    @field_validator(
        "influx_database", "influx_retention_policy", "influx_measurement"
    )
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if not value or any(character in value for character in ('"', "\\", "\n", "\r")):
            raise ValueError("InfluxDB identifier contains unsafe characters")
        return value

    @field_validator("influx_allowed_databases")
    @classmethod
    def validate_allowed_databases(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("at least one allowed database is required")
        for value in values:
            cls.validate_identifier(value)
        return list(dict.fromkeys(values))

    def require_database_allowed(self, database: str) -> str:
        self.validate_identifier(database)
        if database not in self.influx_allowed_databases:
            raise ValueError(f'database "{database}" is not allowed')
        return database

    @property
    def qualified_measurement(self) -> str:
        if self.influx_measurement == "*":
            return (
                f'"{self.influx_database}".'
                f'"{self.influx_retention_policy}"./.*/'
            )
        return (
            f'"{self.influx_database}".'
            f'"{self.influx_retention_policy}".'
            f'"{self.influx_measurement}"'
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
