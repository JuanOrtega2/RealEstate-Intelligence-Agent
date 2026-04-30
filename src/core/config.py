from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    NVIDIA_API_KEY: str
    INVOKE_URL: str = "https://integrate.api.nvidia.com/v1/chat/completions"
    DEFAULT_MODEL: str = "google/gemma-4-31b-it"  # Exact model from user snippet

    APP_NAME: str = "RealEstateIntelligenceAgent"
    DEBUG: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
