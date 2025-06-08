"""
Core configuration management for MiaChat
"""
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Base paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    CONFIG_DIR: Path = BASE_DIR / "config"
    
    # Database settings
    DATABASE_URL: str = Field(
        default="sqlite:///./data/miachat.db",
        description="Database connection URL"
    )
    
    # LLM settings
    DEFAULT_LLM_PROVIDER: str = Field(
        default="ollama",
        description="Default LLM provider to use"
    )
    OLLAMA_HOST: str = Field(
        default="localhost",
        description="Ollama host address"
    )
    OLLAMA_PORT: int = Field(
        default=11434,
        description="Ollama port number"
    )
    LLM_PROVIDER: Optional[str] = Field(default=None, description="LLM provider to use")
    OPENAI_MODEL: Optional[str] = Field(default=None, description="OpenAI model name")
    ANTHROPIC_MODEL: Optional[str] = Field(default=None, description="Anthropic model name")
    
    # Security settings
    SECRET_KEY: str = Field(
        default="your-secret-key-here",
        description="Application secret key"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    
    # Memory settings
    MAX_MEMORY_ITEMS: int = Field(
        default=1000,
        description="Maximum number of memory items to store"
    )
    MEMORY_CLEANUP_INTERVAL: int = Field(
        default=3600,
        description="Memory cleanup interval in seconds"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings() 