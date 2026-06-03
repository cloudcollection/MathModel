from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Math Modeling Agent"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    redis_url: str | None = None
    default_model: str = "gpt-4.1"
    planner_model: str | None = None
    coder_model: str | None = None
    analyst_model: str | None = None
    writer_model: str | None = None

    max_retry: int = 3
    llm_temperature: float = 0.2
    jupyter_timeout: int = 60
    mock_llm: bool = False

    upload_dir: str = "uploads"
    output_dir: str = "outputs"

    def resolve_path(self, value: str) -> Path:
        """Resolve a setting path relative to the backend directory."""

        path = Path(value)
        if path.is_absolute():
            return path
        return BACKEND_DIR / path

    @property
    def upload_path(self) -> Path:
        return self.resolve_path(self.upload_dir)

    @property
    def output_path(self) -> Path:
        return self.resolve_path(self.output_dir)

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def model_for(self, agent: str) -> str:
        """Return the configured model for an agent."""

        override = {
            "planner": self.planner_model,
            "coder": self.coder_model,
            "analyst": self.analyst_model,
            "writer": self.writer_model,
        }.get(agent)
        return override or self.default_model


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
