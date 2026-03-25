import logging
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect

from .session import ConnectionSession

logger = logging.getLogger("app.ws_handler")


async def serve_tts_websocket(websocket: WebSocket, session: ConnectionSession) -> None:
    logger.info("websocket_connected", extra={"connection_id": session.connection_id})
    await websocket.accept()
    await session.start()

    try:
        while True:
            msg = await websocket.receive_json()
            await session.handle_message(msg)
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", extra={"connection_id": session.connection_id})
    finally:
        await session.close()


def new_connection_id() -> str:
    return uuid4().hex[:12]
