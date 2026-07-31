from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash"
    image_model: str = "gemini-3-pro-image-preview"
    llm_provider: str = "local"
    local_llm_base_url: str = "http://127.0.0.1:8080/v1"
    local_llm_model: str = "qwen3.5-4b"
    database_url: str = "sqlite:///souschef.db"
    static_dir: str = str(BASE_DIR.parent / "static" / "recipes")
    frontend_dist: str = str(BASE_DIR.parents[1] / "frontend" / "dist")
    allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allow_origins.split(",") if o.strip()]


settings = Settings()
