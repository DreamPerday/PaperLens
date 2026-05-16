from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_base_url: str = "https://api.deepseek.com"
    storage_path: str = "./storage"
    max_upload_size: int = 50
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    proxy_enabled: bool = False
    proxy_url: str = ""
    layout_parsing_api_url: str = "https://jay3t01093w9y398.aistudio-app.com/layout-parsing"
    layout_parsing_token: str = ""

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

os.makedirs(settings.storage_path, exist_ok=True)
os.makedirs(f"{settings.storage_path}/projects", exist_ok=True)
os.makedirs(f"{settings.storage_path}/uploads", exist_ok=True)
os.makedirs(f"{settings.storage_path}/translations", exist_ok=True)
