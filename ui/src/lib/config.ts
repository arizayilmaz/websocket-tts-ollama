const fallbackUrl = "ws://127.0.0.1:8000/ws/tts";

export function getWebSocketUrl(): string {
  const raw = import.meta.env.VITE_TTS_WS_URL?.trim();
  return raw || fallbackUrl;
}
