import { useEffect, useRef, useState } from "react";
import { getWebSocketUrl } from "../lib/config";
import {
  parseServerMessage,
  serializeClientMessage,
  type ClientMessage,
  type ServerMessage,
} from "../lib/wsProtocol";
import type { AudioPlayerController } from "./useAudioPlayer";

export type UiStatus =
  | "disconnected"
  | "connecting"
  | "idle"
  | "streaming"
  | "stopping"
  | "error";

export type LogLevel = "info" | "warning" | "error";

export type LogEntry = {
  id: string;
  level: LogLevel;
  message: string;
  requestId?: string | null;
  timestamp: string;
};

type SocketFactory = (url: string) => WebSocket;
type UuidFactory = () => string;

type Options = {
  audioPlayer: AudioPlayerController;
  wsUrl?: string;
  createSocket?: SocketFactory;
  createRequestId?: UuidFactory;
  maxLogs?: number;
  initialLogs?: LogEntry[];
};

type PendingBinaryMeta = {
  requestId: string;
  segmentId: string;
  chunkSeq: number;
  byteLength: number;
};

type ConnectionDetails = {
  readyState: number | null;
  wsUrl: string;
};

const defaultSocketFactory: SocketFactory = (url) => new WebSocket(url);
const defaultUuidFactory: UuidFactory = () => crypto.randomUUID();

function timestamp(): string {
  return new Date().toLocaleTimeString("tr-TR", { hour12: false });
}

export function useTtsWebSocket(options: Options) {
  const {
    audioPlayer,
    wsUrl = getWebSocketUrl(),
    createSocket = defaultSocketFactory,
    createRequestId = defaultUuidFactory,
    maxLogs = 60,
    initialLogs = [],
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const pendingBinaryMetaRef = useRef<PendingBinaryMeta[]>([]);
  const activeRequestIdRef = useRef<string | null>(null);
  const currentStatusRef = useRef<UiStatus>("disconnected");

  const [status, setStatus] = useState<UiStatus>("disconnected");
  const [logs, setLogs] = useState<LogEntry[]>(initialLogs.slice(0, maxLogs));
  const [activeRequestId, setActiveRequestId] = useState<string | null>(null);
  const [connection, setConnection] = useState<ConnectionDetails>({
    readyState: null,
    wsUrl,
  });

  const pushLog = (level: LogLevel, message: string, requestId?: string | null) => {
    const entry: LogEntry = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      level,
      message,
      requestId,
      timestamp: timestamp(),
    };
    setLogs((prev) => [entry, ...prev].slice(0, maxLogs));
  };

  const transition = (nextStatus: UiStatus) => {
    currentStatusRef.current = nextStatus;
    setStatus(nextStatus);
  };

  const isSocketOpen = () => wsRef.current?.readyState === WebSocket.OPEN;

  const clearPendingAudio = async () => {
    pendingBinaryMetaRef.current = [];
    await audioPlayer.reset();
  };

  const clearRequest = async () => {
    activeRequestIdRef.current = null;
    setActiveRequestId(null);
    await clearPendingAudio();
  };

  const isActiveRequest = (message: ServerMessage) => {
    if (!message.request_id) {
      return message.type === "audio_format";
    }
    return message.request_id === activeRequestIdRef.current;
  };

  const send = (message: ClientMessage) => {
    if (!isSocketOpen()) {
      pushLog("error", "WebSocket acik degil.");
      return false;
    }

    wsRef.current?.send(serializeClientMessage(message));
    return true;
  };

  const stop = async (reason = "stop_requested") => {
    const requestId = activeRequestIdRef.current;
    if (requestId && isSocketOpen()) {
      send({ type: "stop", request_id: requestId });
    }
    transition(isSocketOpen() ? "stopping" : "idle");
    await clearRequest();
    pushLog("info", `Stop tamamlandi (${reason}).`, requestId);
    if (isSocketOpen()) {
      transition("idle");
    }
  };

  const handleBinaryFrame = async (payload: Blob | ArrayBuffer) => {
    const meta = pendingBinaryMetaRef.current.shift();

    if (!meta) {
      pushLog("warning", "Metadata olmadan binary frame geldi; drop edildi.");
      return;
    }

    if (meta.requestId !== activeRequestIdRef.current) {
      pushLog("warning", "Eski request'e ait binary frame drop edildi.", meta.requestId);
      return;
    }

    const buffer = payload instanceof Blob ? await payload.arrayBuffer() : payload;
    if (buffer.byteLength !== meta.byteLength) {
      pushLog(
        "warning",
        `Binary/meta boyut uyumsuzlugu; beklenen=${meta.byteLength} gelen=${buffer.byteLength}`,
        meta.requestId,
      );
      return;
    }

    audioPlayer.enqueue(buffer);
  };

  const handleServerMessage = async (message: ServerMessage) => {
    if (!isActiveRequest(message)) {
      if (message.request_id) {
        pushLog("warning", `Stale mesaj drop edildi: ${message.type}`, message.request_id);
      }
      return;
    }

    switch (message.type) {
      case "audio_format":
        await audioPlayer.init(message);
        pushLog(
          "info",
          `Audio format: ${message.encoding}, ${message.sample_rate}Hz, kanal=${message.channels}`,
        );
        break;
      case "buffer_status":
        pushLog(
          "info",
          `Buffer len=${message.buffer_len}, queued=${message.queued_segments}`,
          message.request_id,
        );
        if (
          currentStatusRef.current === "stopping" &&
          message.buffer_len === 0 &&
          message.queued_segments === 0
        ) {
          transition("idle");
        }
        break;
      case "segment_ready":
        transition("streaming");
        pushLog("info", `Segment hazir: ${message.segment_id} (${message.order})`, message.request_id);
        break;
      case "audio_start":
        transition("streaming");
        pushLog("info", `Audio start: ${message.segment_id}`, message.request_id);
        break;
      case "audio_chunk":
        pendingBinaryMetaRef.current.push({
          requestId: message.request_id ?? "",
          segmentId: message.segment_id,
          chunkSeq: message.chunk_seq,
          byteLength: message.byte_length,
        });
        break;
      case "audio_end":
        pushLog("info", `Audio end: ${message.segment_id}`, message.request_id);
        if (pendingBinaryMetaRef.current.length === 0) {
          transition("idle");
        }
        break;
      case "warning":
        pushLog("warning", message.message, message.request_id);
        break;
      case "error":
        transition("error");
        pushLog("error", message.message, message.request_id);
        break;
    }
  };

  const connect = async () => {
    if (isSocketOpen() || currentStatusRef.current === "connecting") {
      return;
    }

    transition("connecting");
    setConnection({ readyState: WebSocket.CONNECTING, wsUrl });
    await audioPlayer.prime();

    const ws = createSocket(wsUrl);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      wsRef.current = ws;
      transition("idle");
      setConnection({ readyState: ws.readyState, wsUrl });
      pushLog("info", "WebSocket baglandi.");
    };

    ws.onclose = async (event) => {
      wsRef.current = null;
      setConnection({ readyState: WebSocket.CLOSED, wsUrl });
      await clearRequest();
      transition("disconnected");
      pushLog("warning", `WebSocket kapandi. code=${event.code} reason=${event.reason || "yok"}`);
    };

    ws.onerror = () => {
      transition("error");
      pushLog("error", "WebSocket error olustu.");
    };

    ws.onmessage = async (event) => {
      if (typeof event.data === "string") {
        const message = parseServerMessage(event.data);
        if (!message) {
          pushLog("warning", "Parse edilemeyen mesaj alindi; drop edildi.");
          return;
        }
        await handleServerMessage(message);
        return;
      }

      if (event.data instanceof ArrayBuffer || event.data instanceof Blob) {
        await handleBinaryFrame(event.data);
      }
    };
  };

  const disconnect = async () => {
    const socket = wsRef.current;
    wsRef.current = null;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close(1000, "client_disconnect");
    }
    await clearRequest();
    await audioPlayer.close();
    setConnection({ readyState: WebSocket.CLOSED, wsUrl });
    transition("disconnected");
    pushLog("info", "Baglanti kapatildi.");
  };

  const speak = async (rawText: string) => {
    if (!isSocketOpen()) {
      pushLog("error", "WebSocket acik degilken speak gonderilemez.");
      return false;
    }

    const trimmed = rawText.trim();
    if (!trimmed) {
      pushLog("warning", "Bos metin gonderilemez.");
      return false;
    }

    const previousRequestId = activeRequestIdRef.current;
    if (previousRequestId) {
      send({ type: "stop", request_id: previousRequestId });
      pushLog("info", "Yeni request baslamadan once onceki request durduruldu.", previousRequestId);
    }

    const requestId = createRequestId();
    activeRequestIdRef.current = requestId;
    setActiveRequestId(requestId);
    pendingBinaryMetaRef.current = [];
    await audioPlayer.reset();

    transition("streaming");
    send({ type: "append", text: trimmed, request_id: requestId });
    send({ type: "flush", request_id: requestId });
    pushLog("info", "Speak gonderildi.", requestId);
    return true;
  };

  useEffect(() => {
    return () => {
      void disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    status,
    logs,
    activeRequestId,
    connection,
    connect,
    disconnect,
    speak,
    stop,
    clearLogs: () => setLogs([]),
  };
}
