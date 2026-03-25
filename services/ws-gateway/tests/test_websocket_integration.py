import io
import wave

from fastapi.testclient import TestClient

from app.config import GatewaySettings
from app.main import create_app
from app.splitter import Splitter


class FakePiper:
    async def synthesize_wav(self, text: str) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            wf.writeframes(b"\x01\x02" * 2205)
        return buffer.getvalue()

    async def aclose(self) -> None:
        return None


class FakeOllama:
    async def normalize(self, text: str) -> str:
        return text.strip()

    async def aclose(self) -> None:
        return None


async def always_ready(url: str, timeout_seconds: float) -> bool:
    return True


def test_websocket_streams_audio_and_rejects_invalid_messages():
    app = create_app(
        app_settings=GatewaySettings(use_ollama=True),
        splitter=Splitter(),
        piper=FakePiper(),
        ollama=FakeOllama(),
        readiness_probe=always_ready,
    )

    with TestClient(app) as client:
        with client.websocket_connect("/ws/tts") as websocket:
            audio_format = websocket.receive_json()
            assert audio_format["type"] == "audio_format"

            websocket.send_json({"type": "append", "request_id": "r1", "text": "Merhaba dunya."})
            buffer_status = websocket.receive_json()
            assert buffer_status["type"] == "buffer_status"

            websocket.send_json({"type": "flush", "request_id": "r1"})

            segment_ready = websocket.receive_json()
            audio_start = websocket.receive_json()
            audio_chunk = websocket.receive_json()
            assert segment_ready["type"] == "segment_ready"
            assert audio_start["type"] == "audio_start"
            assert audio_chunk["type"] == "audio_chunk"
            binary_chunk = websocket.receive_bytes()
            assert len(binary_chunk) > 0
            audio_end = websocket.receive_json()
            assert audio_end["type"] == "audio_end"

            trailing_status = websocket.receive_json()
            assert trailing_status["type"] == "buffer_status"

            websocket.send_json({"type": "append", "request_id": "r2", "text": "test", "unexpected": True})
            invalid = websocket.receive_json()
            assert invalid["type"] == "error"
            assert "Invalid message" in invalid["message"]


def test_ready_endpoint_reports_dependency_state():
    app = create_app(
        app_settings=GatewaySettings(use_ollama=True),
        splitter=Splitter(),
        piper=FakePiper(),
        ollama=FakeOllama(),
        readiness_probe=always_ready,
    )

    with TestClient(app) as client:
        response = client.get("/ready")
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["dependencies"]["piper"] is True
        assert payload["dependencies"]["ollama"] is True
