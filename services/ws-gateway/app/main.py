import asyncio
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from .splitter import Splitter
from .clients.piper_http import PiperHttpClient
from .clients.ollama import OllamaClient
from .audio_chunker import wav_to_pcm_chunks

app = FastAPI()

PIPER_BASE_URL = os.getenv("PIPER_BASE_URL", "http://localhost:5000")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api")
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"
CHUNK_MS = int(os.getenv("CHUNK_MS", "100"))

splitter = Splitter()
piper = PiperHttpClient(PIPER_BASE_URL)
ollama = OllamaClient(OLLAMA_BASE_URL)

@app.get("/health")
def health():
    return {"ok": True}

@app.websocket("/ws/tts")
async def ws_tts(websocket: WebSocket):
    await websocket.accept()

    buffer = ""
    segment_order = 0
    stopped = asyncio.Event()

    # İlk format bilgisini gönder (POC: WAV->PCM chunk yapacağız, client'a PCM formatını söyle)
    await websocket.send_json({
        "type": "audio_format",
        "encoding": "pcm_s16le",
        "sample_rate": 22050,
        "channels": 1,
        "sample_width": 2
    })

    async def handle_segment(text: str, segment_id: str, order: int):
        # 1) opsiyonel normalize
        norm = text
        if USE_OLLAMA:
            norm = await ollama.normalize(text)

        await websocket.send_json({
            "type": "segment_ready",
            "segment_id": segment_id,
            "order": order,
            "text": text,
            "normalized_text": norm if USE_OLLAMA else None
        })

        if stopped.is_set():
            return

        # 2) TTS (Piper HTTP -> WAV bytes)
        wav_bytes = await piper.synthesize_wav(norm)

        await websocket.send_json({"type": "audio_start", "segment_id": segment_id})

        # 3) WAV -> PCM chunk’ları (~100ms) ve WS üstünden gönder
        chunk_seq = 0
        async for pcm_chunk in wav_to_pcm_chunks(wav_bytes, chunk_ms=CHUNK_MS):
            if stopped.is_set():
                return

            await websocket.send_json({
                "type": "audio_chunk",
                "segment_id": segment_id,
                "chunk_seq": chunk_seq,
                "byte_length": len(pcm_chunk)
            })
            # audio_chunk JSON’dan sonra gelen next frame binary bytes olmalı
            await websocket.send_bytes(pcm_chunk)
            chunk_seq += 1

        await websocket.send_json({"type": "audio_end", "segment_id": segment_id})

    try:
        while True:
            msg = await websocket.receive_json()

            mtype = msg.get("type")
            if mtype == "append":
                buffer += (msg.get("text") or "")
                await websocket.send_json({
                    "type": "buffer_status",
                    "buffer_len": len(buffer),
                    "queued_segments": 0
                })

                # Buffer’dan çıkarılabilir segment var mı?
                segments, buffer = splitter.pop_ready_segments(buffer)
                for seg in segments:
                    segment_id = f"s{segment_order}"
                    asyncio.create_task(handle_segment(seg, segment_id, segment_order))
                    segment_order += 1

            elif mtype in ("flush", "end"):
                # Nokta beklemeden fallback segment üret
                segments, buffer = splitter.flush_all(buffer)
                for seg in segments:
                    segment_id = f"s{segment_order}"
                    asyncio.create_task(handle_segment(seg, segment_id, segment_order))
                    segment_order += 1

            elif mtype == "stop":
                stopped.set()
                buffer = ""
                await websocket.send_json({"type": "buffer_status", "buffer_len": 0, "queued_segments": 0})

            else:
                await websocket.send_json({
                    "type": "warning",
                    "message": f"Unknown message type: {mtype}"
                })

    except WebSocketDisconnect:
        stopped.set()