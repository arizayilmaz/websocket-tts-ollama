import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useTtsWebSocket } from "./useTtsWebSocket";
import type { AudioPlayerController } from "./useAudioPlayer";

class TestWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = TestWebSocket.CONNECTING;
  binaryType = "arraybuffer";
  sentMessages: string[] = [];
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: { data: string | ArrayBuffer | Blob }) => void | Promise<void>) | null = null;

  send(payload: string) {
    this.sentMessages.push(payload);
  }

  close(code = 1000, reason = "") {
    this.readyState = TestWebSocket.CLOSED;
    this.onclose?.({ code, reason } as CloseEvent);
  }

  open() {
    this.readyState = TestWebSocket.OPEN;
    this.onopen?.(new Event("open"));
  }

  async emitJson(payload: unknown) {
    await this.onmessage?.({ data: JSON.stringify(payload) });
  }

  async emitBinary(payload: ArrayBuffer) {
    await this.onmessage?.({ data: payload });
  }
}

function createAudioPlayer(): AudioPlayerController {
  return {
    prime: vi.fn().mockResolvedValue(undefined),
    init: vi.fn().mockResolvedValue(undefined),
    enqueue: vi.fn(),
    reset: vi.fn().mockResolvedValue(undefined),
    close: vi.fn().mockResolvedValue(undefined),
  };
}

describe("useTtsWebSocket", () => {
  it("baslangic loglarini hydrate eder", () => {
    const audioPlayer = createAudioPlayer();
    const { result } = renderHook(() =>
      useTtsWebSocket({
        audioPlayer,
        initialLogs: [
          {
            id: "seed-1",
            level: "info",
            message: "seed log",
            timestamp: "10:00:00",
          },
        ],
      }),
    );

    expect(result.current.logs).toHaveLength(1);
    expect(result.current.logs[0]?.message).toBe("seed log");
  });

  it("connect -> speak -> stop akisini yonetir", async () => {
    const socket = new TestWebSocket();
    const audioPlayer = createAudioPlayer();
    const { result } = renderHook(() =>
      useTtsWebSocket({
        audioPlayer,
        createSocket: () => socket as unknown as WebSocket,
        createRequestId: () => "req-1",
      }),
    );

    await act(async () => {
      await result.current.connect();
    });

    act(() => {
      socket.open();
    });

    await act(async () => {
      await result.current.speak("Merhaba dunya.");
    });

    expect(socket.sentMessages.map((message) => JSON.parse(message).type)).toEqual(["append", "flush"]);

    await act(async () => {
      await result.current.stop();
    });

    expect(socket.sentMessages.map((message) => JSON.parse(message).type)).toContain("stop");
    expect(result.current.status).toBe("idle");
  });

  it("stop sonrasi stale message/audio ignore edilir", async () => {
    const socket = new TestWebSocket();
    const audioPlayer = createAudioPlayer();
    const { result } = renderHook(() =>
      useTtsWebSocket({
        audioPlayer,
        createSocket: () => socket as unknown as WebSocket,
        createRequestId: () => "req-1",
      }),
    );

    await act(async () => {
      await result.current.connect();
    });
    act(() => {
      socket.open();
    });
    await act(async () => {
      await result.current.speak("Merhaba dunya.");
      await result.current.stop();
    });

    await act(async () => {
      await socket.emitJson({
        type: "audio_chunk",
        request_id: "req-1",
        segment_id: "s1",
        chunk_seq: 0,
        byte_length: 4,
      });
      await socket.emitBinary(new Uint8Array([1, 0, 2, 0]).buffer);
    });

    expect(audioPlayer.enqueue).not.toHaveBeenCalled();
    expect(result.current.logs.some((entry) => entry.message.includes("drop"))).toBe(true);
  });

  it("yeni request baslayinca eski request etkisini keser", async () => {
    const socket = new TestWebSocket();
    const audioPlayer = createAudioPlayer();
    let sequence = 0;
    const { result } = renderHook(() =>
      useTtsWebSocket({
        audioPlayer,
        createSocket: () => socket as unknown as WebSocket,
        createRequestId: () => `req-${++sequence}`,
      }),
    );

    await act(async () => {
      await result.current.connect();
    });
    act(() => {
      socket.open();
    });

    await act(async () => {
      await result.current.speak("ilk");
      await result.current.speak("ikinci");
    });

    const messages = socket.sentMessages.map((message) => JSON.parse(message));
    expect(messages[2]).toMatchObject({ type: "stop", request_id: "req-1" });
    expect(messages[3]).toMatchObject({ type: "append", request_id: "req-2" });

    await act(async () => {
      await socket.emitJson({ type: "warning", request_id: "req-1", message: "old warning" });
    });

    expect(result.current.logs.some((entry) => entry.message.includes("Stale mesaj drop edildi"))).toBe(true);
  });

  it("disconnect sonrasi cleanup yapar", async () => {
    const socket = new TestWebSocket();
    const audioPlayer = createAudioPlayer();
    const { result } = renderHook(() =>
      useTtsWebSocket({
        audioPlayer,
        createSocket: () => socket as unknown as WebSocket,
        createRequestId: () => "req-1",
      }),
    );

    await act(async () => {
      await result.current.connect();
    });
    act(() => {
      socket.open();
    });

    await act(async () => {
      await result.current.disconnect();
    });

    expect(result.current.status).toBe("disconnected");
    expect(audioPlayer.close).toHaveBeenCalled();
  });

  it("bos text gonderimini engeller", async () => {
    const socket = new TestWebSocket();
    const audioPlayer = createAudioPlayer();
    const { result } = renderHook(() =>
      useTtsWebSocket({
        audioPlayer,
        createSocket: () => socket as unknown as WebSocket,
        createRequestId: () => "req-1",
      }),
    );

    await act(async () => {
      await result.current.connect();
    });
    act(() => {
      socket.open();
    });

    await act(async () => {
      await result.current.speak("   ");
    });

    expect(socket.sentMessages).toEqual([]);
    expect(result.current.logs.some((entry) => entry.message.includes("Bos metin"))).toBe(true);
  });

  it("websocket acik degilken speak yapilamaz", async () => {
    const socket = new TestWebSocket();
    const audioPlayer = createAudioPlayer();
    const { result } = renderHook(() =>
      useTtsWebSocket({
        audioPlayer,
        createSocket: () => socket as unknown as WebSocket,
        createRequestId: () => "req-1",
      }),
    );

    await act(async () => {
      await result.current.speak("Merhaba");
    });

    expect(socket.sentMessages).toEqual([]);
    expect(result.current.logs.some((entry) => entry.message.includes("WebSocket acik degil"))).toBe(true);
  });

  it("aktif request binary chunk geldiginde player enqueue edilir", async () => {
    const socket = new TestWebSocket();
    const audioPlayer = createAudioPlayer();
    const { result } = renderHook(() =>
      useTtsWebSocket({
        audioPlayer,
        createSocket: () => socket as unknown as WebSocket,
        createRequestId: () => "req-1",
      }),
    );

    await act(async () => {
      await result.current.connect();
    });
    act(() => {
      socket.open();
    });
    await act(async () => {
      await result.current.speak("Merhaba dunya.");
    });

    await act(async () => {
      await socket.emitJson({
        type: "audio_chunk",
        request_id: "req-1",
        segment_id: "s1",
        chunk_seq: 0,
        byte_length: 4,
      });
      await socket.emitBinary(new Uint8Array([1, 0, 2, 0]).buffer);
    });

    await waitFor(() => expect(audioPlayer.enqueue).toHaveBeenCalled());
  });
});
