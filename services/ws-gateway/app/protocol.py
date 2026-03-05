from typing import Literal, Optional, Union
from pydantic import BaseModel, Field


# -------- Client -> Server --------
class AppendMsg(BaseModel):
    type: Literal["append"]
    text: str

class FlushMsg(BaseModel):
    type: Literal["flush"]

class EndMsg(BaseModel):
    type: Literal["end"]

class StopMsg(BaseModel):
    type: Literal["stop"]

ClientMsg = Union[AppendMsg, FlushMsg, EndMsg, StopMsg]


# -------- Server -> Client --------
class BufferStatus(BaseModel):
    type: Literal["buffer_status"]
    buffer_len: int
    queued_segments: int = 0

class SegmentReady(BaseModel):
    type: Literal["segment_ready"]
    segment_id: str
    order: int
    text: str
    normalized_text: Optional[str] = None

class AudioFormat(BaseModel):
    type: Literal["audio_format"]
    encoding: Literal["pcm_s16le"]
    sample_rate: int
    channels: int
    sample_width: int

class AudioStart(BaseModel):
    type: Literal["audio_start"]
    segment_id: str

class AudioChunk(BaseModel):
    type: Literal["audio_chunk"]
    segment_id: str
    chunk_seq: int
    byte_length: int = Field(..., ge=0)

class AudioEnd(BaseModel):
    type: Literal["audio_end"]
    segment_id: str

class WarningMsg(BaseModel):
    type: Literal["warning"]
    message: str

class ErrorMsg(BaseModel):
    type: Literal["error"]
    message: str

ServerMsg = Union[
    BufferStatus, SegmentReady, AudioFormat,
    AudioStart, AudioChunk, AudioEnd,
    WarningMsg, ErrorMsg
]