import httpx
from contextlib import asynccontextmanager
from typing import Awaitable, Callable, Optional

from fastapi import FastAPI, WebSocket

from .clients.ollama import OllamaClient
from .clients.piper_http import PiperHttpClient
from .config import load_settings
from .logging_utils import setup_logging
from .readiness import tcp_ready
from .session import ConnectionSession
from .splitter import Splitter
from .ws_handler import new_connection_id, serve_tts_websocket

settings = load_settings()
setup_logging(settings.log_level)


def create_app(
    app_settings=None,
    splitter: Optional[Splitter] = None,
    piper: Optional[PiperHttpClient] = None,
    ollama: Optional[OllamaClient] = None,
    readiness_probe: Optional[Callable[[str, float], Awaitable[bool]]] = None,
) -> FastAPI:
    active_settings = app_settings or settings
    probe = readiness_probe or tcp_ready

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        timeout = httpx.Timeout(
            timeout=active_settings.request_timeout_seconds,
            connect=active_settings.connect_timeout_seconds,
        )
        app.state.settings = active_settings
        app.state.splitter = splitter or Splitter()
        app.state.piper = piper or PiperHttpClient(
            active_settings.piper_base_url,
            timeout=timeout,
            retries=active_settings.piper_retries,
        )
        app.state.ollama = ollama or OllamaClient(
            active_settings.ollama_base_url,
            model=active_settings.ollama_model,
            timeout=timeout,
            retries=active_settings.ollama_retries,
        )
        yield
        if hasattr(app.state.piper, "aclose"):
            await app.state.piper.aclose()
        if hasattr(app.state.ollama, "aclose"):
            await app.state.ollama.aclose()

    app = FastAPI(lifespan=lifespan)

    @app.get("/health")
    def health():
        return {
            "ok": True,
            "piper_base_url": active_settings.piper_base_url,
            "ollama_base_url": active_settings.ollama_base_url,
            "use_ollama": active_settings.use_ollama,
            "chunk_ms": active_settings.chunk_ms,
            "segment_queue_size": active_settings.segment_queue_size,
        }

    @app.get("/ready")
    async def ready():
        piper_ready = await probe(
            active_settings.piper_base_url,
            active_settings.connect_timeout_seconds,
        )
        ollama_ready = True
        if active_settings.use_ollama:
            ollama_ready = await probe(
                active_settings.ollama_base_url,
                active_settings.connect_timeout_seconds,
            )

        ready_state = piper_ready and ollama_ready
        return {
            "ok": ready_state,
            "dependencies": {
                "piper": piper_ready,
                "ollama": ollama_ready if active_settings.use_ollama else "disabled",
            },
        }

    @app.websocket("/ws/tts")
    async def ws_tts(websocket: WebSocket):
        session = ConnectionSession(
            websocket=websocket,
            connection_id=new_connection_id(),
            settings=websocket.app.state.settings,
            splitter=websocket.app.state.splitter,
            piper=websocket.app.state.piper,
            ollama=websocket.app.state.ollama,
        )
        await serve_tts_websocket(websocket, session)

    return app


app = create_app()
