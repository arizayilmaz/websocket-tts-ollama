export type ClientMessage =
  | { type: "append"; text: string; request_id?: string | null }
  | { type: "flush"; request_id?: string | null }
  | { type: "end"; request_id?: string | null }
  | { type: "stop"; request_id?: string | null };

type BaseMsg = {
  request_id?: string | null;
};

export type AudioFormatMsg = BaseMsg & {
  type: "audio_format";
  encoding: "pcm_s16le";
  sample_rate: number;
  channels: number;
  sample_width: number;
};

export type AudioChunkMsg = BaseMsg & {
  type: "audio_chunk";
  segment_id: string;
  chunk_seq: number;
  byte_length: number;
};

export type BufferStatusMsg = BaseMsg & {
  type: "buffer_status";
  buffer_len: number;
  queued_segments: number;
};

export type SegmentReadyMsg = BaseMsg & {
  type: "segment_ready";
  segment_id: string;
  order: number;
  text: string;
  normalized_text?: string | null;
};

export type AudioStartMsg = BaseMsg & {
  type: "audio_start";
  segment_id: string;
};

export type AudioEndMsg = BaseMsg & {
  type: "audio_end";
  segment_id: string;
};

export type WarningMsg = BaseMsg & {
  type: "warning";
  message: string;
};

export type ErrorMsg = BaseMsg & {
  type: "error";
  message: string;
};

export type ServerMessage =
  | AudioFormatMsg
  | BufferStatusMsg
  | SegmentReadyMsg
  | AudioStartMsg
  | AudioChunkMsg
  | AudioEndMsg
  | WarningMsg
  | ErrorMsg;

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const hasString = (value: Record<string, unknown>, key: string): value is Record<string, string> =>
  typeof value[key] === "string";

const hasNumber = (value: Record<string, unknown>, key: string): value is Record<string, number> =>
  typeof value[key] === "number";

const optionalRequestId = (value: Record<string, unknown>): string | null | undefined => {
  const requestId = value.request_id;
  if (requestId == null || typeof requestId === "string") {
    return requestId as string | null | undefined;
  }
  return undefined;
};

export function parseServerMessage(raw: string): ServerMessage | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }

  if (!isObject(parsed) || !hasString(parsed, "type")) {
    return null;
  }

  const request_id = optionalRequestId(parsed);
  if ("request_id" in parsed && request_id === undefined) {
    return null;
  }

  switch (parsed.type) {
    case "audio_format":
      if (
        parsed.encoding === "pcm_s16le" &&
        hasNumber(parsed, "sample_rate") &&
        hasNumber(parsed, "channels") &&
        hasNumber(parsed, "sample_width")
      ) {
        return {
          type: "audio_format",
          request_id,
          encoding: "pcm_s16le",
          sample_rate: parsed.sample_rate,
          channels: parsed.channels,
          sample_width: parsed.sample_width,
        };
      }
      return null;
    case "buffer_status":
      if (hasNumber(parsed, "buffer_len") && hasNumber(parsed, "queued_segments")) {
        return {
          type: "buffer_status",
          request_id,
          buffer_len: parsed.buffer_len,
          queued_segments: parsed.queued_segments,
        };
      }
      return null;
    case "segment_ready":
      if (
        hasString(parsed, "segment_id") &&
        hasNumber(parsed, "order") &&
        hasString(parsed, "text")
      ) {
        return {
          type: "segment_ready",
          request_id,
          segment_id: parsed.segment_id,
          order: parsed.order,
          text: parsed.text,
          normalized_text:
            parsed.normalized_text == null || typeof parsed.normalized_text === "string"
              ? (parsed.normalized_text as string | null | undefined)
              : undefined,
        };
      }
      return null;
    case "audio_start":
      if (hasString(parsed, "segment_id")) {
        return { type: "audio_start", request_id, segment_id: parsed.segment_id };
      }
      return null;
    case "audio_chunk":
      if (
        hasString(parsed, "segment_id") &&
        hasNumber(parsed, "chunk_seq") &&
        hasNumber(parsed, "byte_length")
      ) {
        return {
          type: "audio_chunk",
          request_id,
          segment_id: parsed.segment_id,
          chunk_seq: parsed.chunk_seq,
          byte_length: parsed.byte_length,
        };
      }
      return null;
    case "audio_end":
      if (hasString(parsed, "segment_id")) {
        return { type: "audio_end", request_id, segment_id: parsed.segment_id };
      }
      return null;
    case "warning":
      if (hasString(parsed, "message")) {
        return { type: "warning", request_id, message: parsed.message };
      }
      return null;
    case "error":
      if (hasString(parsed, "message")) {
        return { type: "error", request_id, message: parsed.message };
      }
      return null;
    default:
      return null;
  }
}

export function serializeClientMessage(message: ClientMessage): string {
  return JSON.stringify(message);
}
