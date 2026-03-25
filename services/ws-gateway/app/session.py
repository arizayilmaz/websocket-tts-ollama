import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

from .audio_chunker import wav_to_pcm_chunks
from .clients.ollama import OllamaClient
from .clients.piper_http import PiperHttpClient
from .config import GatewaySettings
from .protocol import AudioChunk, AudioEnd, AudioFormat, AudioStart, BufferStatus, CLIENT_MSG_ADAPTER, ErrorMsg, SegmentReady, WarningMsg
from .splitter import Splitter

logger = logging.getLogger("app.session")


@dataclass
class SegmentJob:
    request_id: Optional[str]
    request_seq: int
    segment_id: str
    order: int
    text: str


class ConnectionSession:
    def __init__(
        self,
        websocket: Any,
        connection_id: str,
        settings: GatewaySettings,
        splitter: Splitter,
        piper: PiperHttpClient,
        ollama: OllamaClient,
    ) -> None:
        self.websocket = websocket
        self.connection_id = connection_id
        self.settings = settings
        self.splitter = splitter
        self.piper = piper
        self.ollama = ollama
        self.buffer = ""
        self.segment_order = 0
        self.current_request_id: Optional[str] = None
        self.request_seq = 0
        self.closed = False
        self._send_lock = asyncio.Lock()
        self._segment_queue: asyncio.Queue[Optional[SegmentJob]] = asyncio.Queue(
            maxsize=settings.segment_queue_size
        )
        self._worker_task: Optional[asyncio.Task] = None
        self._active_segment_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._worker_task = asyncio.create_task(self._segment_worker())
        await self._send_json(
            AudioFormat(
                type="audio_format",
                request_id=None,
                encoding="pcm_s16le",
                sample_rate=22050,
                channels=1,
                sample_width=2,
            ).model_dump()
        )

    async def close(self) -> None:
        if self.closed:
            return

        self.closed = True
        await self.cancel_active_request(reason="connection_closed", emit_warning=False)
        await self._segment_queue.put(None)
        if self._worker_task is not None:
            await self._worker_task

    async def handle_message(self, msg: dict[str, Any]) -> None:
        try:
            parsed = CLIENT_MSG_ADAPTER.validate_python(msg)
        except Exception as exc:
            await self._send_json(
                ErrorMsg(
                    type="error",
                    request_id=msg.get("request_id"),
                    message=f"Invalid message: {exc}",
                ).model_dump()
            )
            return

        mtype = parsed.type
        request_id = parsed.request_id

        if mtype == "append":
            await self._ensure_request(request_id)
            self.buffer += parsed.text or ""
            await self._emit_ready_segments(request_id=request_id, flush=False)
            await self._send_buffer_status(request_id)
            return

        if mtype in {"flush", "end"}:
            await self._ensure_request(request_id)
            await self._emit_ready_segments(request_id=request_id, flush=True)
            await self._send_buffer_status(request_id)
            return

        if mtype == "stop":
            await self.cancel_active_request(reason="client_stop", request_id=request_id, emit_warning=False)
            await self._send_buffer_status(request_id)
            return

        await self._send_json(
            WarningMsg(
                type="warning",
                request_id=request_id,
                message=f"Unknown message type: {mtype}",
            ).model_dump()
        )

    async def cancel_active_request(
        self,
        reason: str,
        request_id: Optional[str] = None,
        emit_warning: bool = True,
    ) -> None:
        cancelled_request_id = self.current_request_id if self.current_request_id is not None else request_id
        self.request_seq += 1
        self.current_request_id = request_id if reason == "request_started" else None
        self.buffer = ""
        self._drain_queue()

        if self._active_segment_task is not None and not self._active_segment_task.done():
            self._active_segment_task.cancel()
            try:
                await self._active_segment_task
            except asyncio.CancelledError:
                logger.info(
                    "active_segment_cancelled",
                    extra={
                        "connection_id": self.connection_id,
                        "request_id": cancelled_request_id,
                        "reason": reason,
                    },
                )

        if emit_warning and cancelled_request_id is not None:
            await self._send_json(
                WarningMsg(
                    type="warning",
                    request_id=cancelled_request_id,
                    message=f"Request cancelled: {reason}",
                ).model_dump()
            )

    async def _ensure_request(self, request_id: Optional[str]) -> None:
        if self.current_request_id is None:
            self.current_request_id = request_id
            self.request_seq += 1
            logger.info(
                "request_started",
                extra={
                    "connection_id": self.connection_id,
                    "request_id": request_id,
                    "request_seq": self.request_seq,
                },
            )
            return

        if request_id == self.current_request_id:
            return

        await self.cancel_active_request(reason="superseded_by_new_request", request_id=request_id)
        self.current_request_id = request_id
        logger.info(
            "request_started",
            extra={
                "connection_id": self.connection_id,
                "request_id": request_id,
                "request_seq": self.request_seq,
            },
        )

    async def _emit_ready_segments(self, request_id: Optional[str], flush: bool) -> None:
        if flush:
            segments, self.buffer = self.splitter.flush_all(self.buffer)
        else:
            segments, self.buffer = self.splitter.pop_ready_segments(self.buffer)

        for seg in segments:
            job = SegmentJob(
                request_id=request_id,
                request_seq=self.request_seq,
                segment_id=f"s{self.segment_order}",
                order=self.segment_order,
                text=seg,
            )
            self.segment_order += 1
            if not await self._try_enqueue(job):
                await self.cancel_active_request(reason="backpressure", request_id=request_id)
                await self._send_json(
                    ErrorMsg(
                        type="error",
                        request_id=request_id,
                        message="Segment queue is full; request cancelled",
                    ).model_dump()
                )
                return

    async def _try_enqueue(self, job: SegmentJob) -> bool:
        try:
            self._segment_queue.put_nowait(job)
            return True
        except asyncio.QueueFull:
            logger.warning(
                "segment_queue_full",
                extra={
                    "connection_id": self.connection_id,
                    "request_id": job.request_id,
                    "segment_id": job.segment_id,
                },
            )
            return False

    async def _segment_worker(self) -> None:
        while True:
            job = await self._segment_queue.get()
            if job is None:
                self._segment_queue.task_done()
                break

            try:
                if not self._is_job_active(job):
                    continue

                self._active_segment_task = asyncio.create_task(self._process_segment(job))
                try:
                    await self._active_segment_task
                except asyncio.CancelledError:
                    logger.info(
                        "segment_task_cancelled",
                        extra={
                            "connection_id": self.connection_id,
                            "request_id": job.request_id,
                            "segment_id": job.segment_id,
                        },
                    )
                finally:
                    self._active_segment_task = None
            finally:
                self._segment_queue.task_done()

    async def _process_segment(self, job: SegmentJob) -> None:
        try:
            if not self._is_job_active(job):
                return

            normalized_text = job.text
            if self.settings.use_ollama:
                normalized_text = await self.ollama.normalize(job.text)

            if not self._is_job_active(job):
                return

            await self._send_json(
                SegmentReady(
                    type="segment_ready",
                    request_id=job.request_id,
                    segment_id=job.segment_id,
                    order=job.order,
                    text=job.text,
                    normalized_text=normalized_text if self.settings.use_ollama else None,
                ).model_dump()
            )

            wav_bytes = await self.piper.synthesize_wav(normalized_text)

            if not self._is_job_active(job):
                return

            await self._send_json(
                AudioStart(
                    type="audio_start",
                    request_id=job.request_id,
                    segment_id=job.segment_id,
                ).model_dump()
            )

            chunk_seq = 0
            async for pcm_chunk in wav_to_pcm_chunks(wav_bytes, chunk_ms=self.settings.chunk_ms):
                if not self._is_job_active(job):
                    return

                await self._send_json(
                    AudioChunk(
                        type="audio_chunk",
                        request_id=job.request_id,
                        segment_id=job.segment_id,
                        chunk_seq=chunk_seq,
                        byte_length=len(pcm_chunk),
                    ).model_dump()
                )
                await self._send_bytes(pcm_chunk)
                chunk_seq += 1

            if not self._is_job_active(job):
                return

            await self._send_json(
                AudioEnd(
                    type="audio_end",
                    request_id=job.request_id,
                    segment_id=job.segment_id,
                ).model_dump()
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(
                "segment_processing_failed",
                extra={
                    "connection_id": self.connection_id,
                    "request_id": job.request_id,
                    "segment_id": job.segment_id,
                },
            )
            await self._send_json(
                ErrorMsg(
                    type="error",
                    request_id=job.request_id,
                    message=f"segment {job.segment_id} failed: {exc}",
                ).model_dump()
            )

    def _is_job_active(self, job: SegmentJob) -> bool:
        return (
            not self.closed
            and self.current_request_id == job.request_id
            and self.request_seq == job.request_seq
        )

    def _drain_queue(self) -> None:
        while not self._segment_queue.empty():
            try:
                self._segment_queue.get_nowait()
                self._segment_queue.task_done()
            except asyncio.QueueEmpty:
                return

    async def _send_buffer_status(self, request_id: Optional[str]) -> None:
        await self._send_json(
            BufferStatus(
                type="buffer_status",
                request_id=request_id,
                buffer_len=len(self.buffer),
                queued_segments=self._segment_queue.qsize(),
            ).model_dump()
        )

    async def _send_json(self, payload: dict[str, Any]) -> None:
        async with self._send_lock:
            await self.websocket.send_json(payload)

    async def _send_bytes(self, payload: bytes) -> None:
        async with self._send_lock:
            await self.websocket.send_bytes(payload)
