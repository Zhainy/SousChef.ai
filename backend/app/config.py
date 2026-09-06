from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Proveedor de IA ────────────────────────────────────────────────────
    # Valores: "oci" | "local"
    llm_provider: str = "local"

    # ── Fallback automático ────────────────────────────────────────────────
    # Si el proveedor primario falla antes de emitir tokens, se intenta con
    # ai_fallback_provider de forma transparente para el cliente.
    ai_fallback_enabled: bool = True
    ai_fallback_provider: str = "local"

    # ── OCI Generative AI (primario) ───────────────────────────────────────
    oci_compartment_id: str | None = None
    oci_region: str = "us-ashburn-1"
    oci_model_id: str = "meta.llama-3.3-70b-instruct"
    oci_service_endpoint: str | None = None
    # "api_key" lee ~/.oci/config (desarrollo local)
    # "instance_principal" usa el IAM role de la VM (producción OCI)
    oci_auth_type: str = "api_key"
    oci_timeout_seconds: int = 30

    # ── llama.cpp local (fallback) ─────────────────────────────────────────
    # En Docker Compose el nombre del servicio es "llama-cpp"
    local_llm_base_url: str = "http://llama-cpp:8080/v1"
    local_llm_model: str = "llama-3.2-3b"

    # ── Imágenes de recetas ────────────────────────────────────────────────
    # "web"  → TheMealDB + Unsplash (gratuito, sin API key)
    # "none" → desactiva la búsqueda (útil para tests)
    image_source: str = "web"

    # ── Base de datos ──────────────────────────────────────────────────────
    database_url: str = "sqlite:///souschef.db"

    # ── Rutas internas ─────────────────────────────────────────────────────
    static_dir: str = str(BASE_DIR.parent / "static" / "recipes")
    frontend_dist: str = str(BASE_DIR.parents[1] / "frontend" / "dist")

    # ── CORS ───────────────────────────────────────────────────────────────
    allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allow_origins.split(",") if o.strip()]


settings = Settings()
