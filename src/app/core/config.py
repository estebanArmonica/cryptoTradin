from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "CoinGecko API"
    PROJECT_DESCRIPTION: str = "API para interactuar con CoinGecko"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    class Config:
        env_file = ".env"

settings = Settings()

