from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """
    Application configuration for production environments.
    Values are loaded from environment variables or .env file.
    """

    NVIDIA_API_KEY: str

    # Full endpoint for direct HTTP requests
    INVOKE_URL: str = "https://integrate.api.nvidia.com/v1/chat/completions"

    # Updated to the model you requested
    DEFAULT_MODEL: str = "meta/llama-3.1-70b-instruct"

    APP_NAME: str = "Real Estate Intelligence Agent"
    DEBUG: bool = False
    PORT: int = 8080

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
