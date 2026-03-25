import os

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class GatewaySettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    piper_base_url: str = Field(default="http://localhost:5000", min_length=1)
    ollama_base_url: str = Field(default="http://localhost:11434/api", min_length=1)
    use_ollama: bool = False
    ollama_model: str = Field(default="gemma3", min_length=1)
    chunk_ms: int = Field(default=100, ge=20, le=1000)
    segment_queue_size: int = Field(default=8, ge=1, le=128)
    request_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    connect_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    piper_retries: int = Field(default=1, ge=0, le=5)
    ollama_retries: int = Field(default=1, ge=0, le=5)
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    @classmethod
    def from_env(cls) -> "GatewaySettings":
        data = {
            "piper_base_url": os.getenv("PIPER_BASE_URL", "http://localhost:5000"),
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api"),
            "use_ollama": os.getenv("USE_OLLAMA", "false"),
            "ollama_model": os.getenv("OLLAMA_MODEL", "gemma3"),
            "chunk_ms": os.getenv("CHUNK_MS", "100"),
            "segment_queue_size": os.getenv("SEGMENT_QUEUE_SIZE", "8"),
            "request_timeout_seconds": os.getenv("REQUEST_TIMEOUT_SECONDS", "30"),
            "connect_timeout_seconds": os.getenv("CONNECT_TIMEOUT_SECONDS", "5"),
            "piper_retries": os.getenv("PIPER_RETRIES", "1"),
            "ollama_retries": os.getenv("OLLAMA_RETRIES", "1"),
            "log_level": os.getenv("LOG_LEVEL", "INFO").upper(),
        }
        return cls.model_validate(data)


def load_settings() -> GatewaySettings:
    try:
        return GatewaySettings.from_env()
    except ValidationError as exc:
        raise RuntimeError(f"Invalid gateway configuration: {exc}") from exc
