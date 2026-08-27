from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "JanAvaaz"
    app_mode: str = "demo"
    public_base_url: str = "http://localhost:8080"
    database_url: str = "postgresql+asyncpg://janaavaaz:janaavaaz@postgres:5432/janaavaaz"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_live_model: str = "gemini-2.5-flash-native-audio-preview-12-2025"
    gcp_region: str = "asia-south1"
    ai_provider: str = "gemini"
    hearing_mode: str = "upload"
    geo_provider: str = "lgd"
    use_fixtures: bool = True
    repo_root: Path = ROOT
    pack_root: Path = ROOT / "data" / "packs"
    fixture_root: Path = ROOT / "data" / "fixtures"
    media_root: Path = ROOT / "data" / "media"
    context_root: Path = ROOT / "context"
    k_anon_min: int = 5
    demo_officer_email: str = "officer@demo.janaavaaz"
    demo_officer_token: str = "jan-demo-board"


settings = Settings()
