import pytest

from app.config import GatewaySettings


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for key in [
        "PIPER_BASE_URL",
        "OLLAMA_BASE_URL",
        "USE_OLLAMA",
        "OLLAMA_MODEL",
        "CHUNK_MS",
        "SEGMENT_QUEUE_SIZE",
        "REQUEST_TIMEOUT_SECONDS",
        "CONNECT_TIMEOUT_SECONDS",
        "PIPER_RETRIES",
        "OLLAMA_RETRIES",
        "LOG_LEVEL",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_gateway_settings_defaults():
    settings = GatewaySettings.from_env()
    assert settings.segment_queue_size == 8
    assert settings.chunk_ms == 100
    assert settings.use_ollama is False


def test_gateway_settings_validation(monkeypatch):
    monkeypatch.setenv("SEGMENT_QUEUE_SIZE", "0")
    with pytest.raises(Exception):
        GatewaySettings.from_env()
