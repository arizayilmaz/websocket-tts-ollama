import asyncio
import io
import wave

import pytest

from app.config import GatewaySettings
from app.session import ConnectionSession
from app.splitter import Splitter, SplitterConfig


class FakeWebSocket:
    def __init__(self):
        self.json_messages = []
        self.binary_messages = []

    async def send_json(self, payload):
        self.json_messages.append(payload)

    async def send_bytes(self, payload):
        self.binary_messages.append(payload)


class SlowPiper:
    def __init__(self, wav_bytes: bytes):
        self.wav_bytes = wav_bytes
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.cancelled = False

    async def synthesize_wav(self, text: str) -> bytes:
        self.started.set()
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return self.wav_bytes


class FakeOllama:
    async def normalize(self, text: str) -> str:
        return text


def make_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00\x00" * 2205)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_stop_cancels_active_request_and_prevents_stale_audio():
    websocket = FakeWebSocket()
    piper = SlowPiper(make_wav_bytes())
    settings = GatewaySettings(segment_queue_size=2)
    session = ConnectionSession(
        websocket=websocket,
        connection_id="conn-test-1",
        settings=settings,
        splitter=Splitter(),
        piper=piper,
        ollama=FakeOllama(),
    )

    await session.start()
    await session.handle_message({"type": "append", "request_id": "r1", "text": "Merhaba dunya."})
    await session.handle_message({"type": "flush", "request_id": "r1"})
    await piper.started.wait()

    await session.handle_message({"type": "stop", "request_id": "r1"})
    await asyncio.sleep(0)

    assert piper.cancelled is True
    assert not any(msg.get("type") == "audio_start" and msg.get("request_id") == "r1" for msg in websocket.json_messages)
    assert websocket.binary_messages == []

    await session.close()


@pytest.mark.asyncio
async def test_new_request_cancels_old_request():
    websocket = FakeWebSocket()
    piper = SlowPiper(make_wav_bytes())
    settings = GatewaySettings(segment_queue_size=2)
    session = ConnectionSession(
        websocket=websocket,
        connection_id="conn-test-2",
        settings=settings,
        splitter=Splitter(),
        piper=piper,
        ollama=FakeOllama(),
    )

    await session.start()
    await session.handle_message({"type": "append", "request_id": "r1", "text": "Ilk cumle."})
    await session.handle_message({"type": "flush", "request_id": "r1"})
    await piper.started.wait()

    await session.handle_message({"type": "append", "request_id": "r2", "text": "Ikinci cumle."})
    await session.handle_message({"type": "flush", "request_id": "r2"})
    await asyncio.sleep(0)

    assert piper.cancelled is True
    assert any(msg.get("type") == "warning" and msg.get("request_id") == "r1" for msg in websocket.json_messages)

    await session.close()


@pytest.mark.asyncio
async def test_backpressure_cancels_request_when_queue_is_full():
    websocket = FakeWebSocket()
    piper = SlowPiper(make_wav_bytes())
    settings = GatewaySettings(segment_queue_size=1)
    splitter = Splitter(
        SplitterConfig(
            WAITING_THRESHOLD_CHARS=10,
            FALLBACK_TARGET_CHARS=10,
            MAX_SEGMENT_CHARS=10,
            MIN_SEGMENT_CHARS=1,
        )
    )
    session = ConnectionSession(
        websocket=websocket,
        connection_id="conn-test-3",
        settings=settings,
        splitter=splitter,
        piper=piper,
        ollama=FakeOllama(),
    )

    await session.start()
    await session.handle_message(
        {
            "type": "append",
            "request_id": "r1",
            "text": "bir iki uc dort bes alti yedi sekiz dokuz on onbir oniki",
        }
    )
    await session.handle_message({"type": "flush", "request_id": "r1"})
    await asyncio.sleep(0)

    assert any(msg.get("type") == "error" and "queue is full" in msg.get("message", "") for msg in websocket.json_messages)
    assert session.current_request_id is None

    await session.close()
