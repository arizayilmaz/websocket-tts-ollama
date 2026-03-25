import { vi } from "vitest";

type MessageEventLike = {
  data: string | ArrayBuffer | Blob;
};

export class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  static instances: MockWebSocket[] = [];

  readonly url: string;
  readyState = MockWebSocket.CONNECTING;
  binaryType = "blob";
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEventLike) => void | Promise<void>) | null = null;
  sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  static reset() {
    MockWebSocket.instances = [];
  }

  send(payload: string) {
    this.sentMessages.push(payload);
  }

  close(code = 1000, reason = "") {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code, reason } as CloseEvent);
  }

  open() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event("open"));
  }

  async emitJson(payload: unknown) {
    await this.onmessage?.({ data: JSON.stringify(payload) });
  }

  async emitBinary(payload: ArrayBuffer) {
    await this.onmessage?.({ data: payload });
  }

  emitError() {
    this.onerror?.(new Event("error"));
  }
}

export class MockAudioWorkletNode {
  static instances: MockAudioWorkletNode[] = [];
  port = {
    postMessage: vi.fn(),
  };
  connect = vi.fn();
  disconnect = vi.fn();

  constructor() {
    MockAudioWorkletNode.instances.push(this);
  }

  static reset() {
    MockAudioWorkletNode.instances = [];
  }
}

export class MockAudioContext {
  static instances: MockAudioContext[] = [];
  audioWorklet = {
    addModule: vi.fn().mockResolvedValue(undefined),
  };
  destination = {};
  state: AudioContextState = "suspended";
  resume = vi.fn(async () => {
    this.state = "running";
  });
  close = vi.fn(async () => {
    this.state = "closed";
  });

  constructor(options?: AudioContextOptions) {
    void options;
    MockAudioContext.instances.push(this);
  }

  static reset() {
    MockAudioContext.instances = [];
  }
}
