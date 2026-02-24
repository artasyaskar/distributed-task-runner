import os
from typing import Optional
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")
    
    database_url: str = "sqlite:///./tasks.db"
    redis_url: str = "redis://localhost:6379"
    secret_key: str = "your-secret-key-here"
    debug: bool = True
    
    # Task settings
    max_retries: int = 3
    retry_delay: int = 5  # seconds


settings = Settings()
