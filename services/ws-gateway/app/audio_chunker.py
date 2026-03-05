import asyncio
import io
import wave
from typing import AsyncIterator

async def wav_to_pcm_chunks(wav_bytes: bytes, chunk_ms: int = 100) -> AsyncIterator[bytes]:
    # WAV -> raw PCM frame bytes
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        framerate = wf.getframerate()
        sampwidth = wf.getsampwidth()
        nchannels = wf.getnchannels()

        bytes_per_frame = sampwidth * nchannels
        frames_per_chunk = int(framerate * (chunk_ms / 1000.0))
        bytes_per_chunk = frames_per_chunk * bytes_per_frame

        while True:
            data = wf.readframes(frames_per_chunk)
            if not data:
                break
            yield data
            await asyncio.sleep(0)  # event loop'a nefes aldır