import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { MockAudioContext, MockAudioWorkletNode, MockWebSocket } from "./mocks";

beforeEach(() => {
  MockWebSocket.reset();
  MockAudioContext.reset();
  MockAudioWorkletNode.reset();

  vi.stubGlobal("WebSocket", MockWebSocket);
  vi.stubGlobal("AudioContext", MockAudioContext);
  vi.stubGlobal("AudioWorkletNode", MockAudioWorkletNode);
  vi.stubGlobal("crypto", {
    randomUUID: vi
      .fn()
      .mockReturnValueOnce("req-1")
      .mockReturnValueOnce("req-2")
      .mockReturnValueOnce("req-3")
      .mockReturnValue("req-x"),
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
