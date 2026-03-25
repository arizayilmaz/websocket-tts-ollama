from typing import Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# -------- Client -> Server --------
class AppendMsg(StrictModel):
    type: Literal["append"]
    request_id: Optional[str] = None
    text: str

class FlushMsg(StrictModel):
    type: Literal["flush"]
    request_id: Optional[str] = None

class EndMsg(StrictModel):
    type: Literal["end"]
    request_id: Optional[str] = None

class StopMsg(StrictModel):
    type: Literal["stop"]
    request_id: Optional[str] = None

ClientMsg = Union[AppendMsg, FlushMsg, EndMsg, StopMsg]
CLIENT_MSG_ADAPTER = TypeAdapter(ClientMsg)


# -------- Server -> Client --------
class BufferStatus(StrictModel):
    type: Literal["buffer_status"]
    request_id: Optional[str] = None
    buffer_len: int
    queued_segments: int = 0

class SegmentReady(StrictModel):
    type: Literal["segment_ready"]
    request_id: Optional[str] = None
    segment_id: str
    order: int
    text: str
    normalized_text: Optional[str] = None

class AudioFormat(StrictModel):
    type: Literal["audio_format"]
    request_id: Optional[str] = None
    encoding: Literal["pcm_s16le"]
    sample_rate: int
    channels: int
    sample_width: int

class AudioStart(StrictModel):
    type: Literal["audio_start"]
    request_id: Optional[str] = None
    segment_id: str

class AudioChunk(StrictModel):
    type: Literal["audio_chunk"]
    request_id: Optional[str] = None
    segment_id: str
    chunk_seq: int
    byte_length: int = Field(..., ge=0)

class AudioEnd(StrictModel):
    type: Literal["audio_end"]
    request_id: Optional[str] = None
    segment_id: str

class WarningMsg(StrictModel):
    type: Literal["warning"]
    request_id: Optional[str] = None
    message: str

class ErrorMsg(StrictModel):
    type: Literal["error"]
    request_id: Optional[str] = None
    message: str

ServerMsg = Union[
    BufferStatus, SegmentReady, AudioFormat,
    AudioStart, AudioChunk, AudioEnd,
    WarningMsg, ErrorMsg
]
