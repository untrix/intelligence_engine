"""Application configuration loaded from environment variables and .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _default_home_dir() -> Path:
    return _PROJECT_ROOT.resolve()


def _parse_path(v):
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
    p = Path(v).expanduser()
    if not p.is_absolute():
        p = (_PROJECT_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


class Settings(BaseSettings):
    """App-wide settings with INTELLIGENCE_ENGINE_ env prefix and .env file support."""

    app_name: str = "Intelligence Engine"
    home_dir: Path = Field(default_factory=_default_home_dir)
    data_dir: Path | None = Field(default=None)
    database_url: str = ""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    bedrock_connect_timeout_seconds: int = 60
    bedrock_read_timeout_seconds: int = 900

    model_config = {"env_prefix": "INTELLIGENCE_ENGINE_", "env_file": ".env"}

    @field_validator("home_dir", mode="before")
    @classmethod
    def _normalize_home_dir(cls, v):
        if v is None:
            return _default_home_dir()
        return _parse_path(v)

    @field_validator("data_dir", mode="before")
    @classmethod
    def _normalize_data_dir(cls, v):
        if v is None:
            return None
        return _parse_path(v)

    @model_validator(mode="after")
    def _derive_data_dir(self):
        if self.data_dir is None:
            object.__setattr__(self, "data_dir", self.home_dir / "data")
        return self

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.database_url:
            self.database_url = f"sqlite+aiosqlite:///{self.data_dir / 'intelligence_engine.db'}"


settings = Settings()
