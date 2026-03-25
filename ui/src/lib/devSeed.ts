import type { LogEntry } from "../hooks/useTtsWebSocket";

export const INITIAL_TEXT =
  "Merhaba. Bu bir websocket TTS testidir. Cumlelerin sirayla ve duzgun okunmasini kontrol ediyoruz.";

export function isDevSeedEnabled(): boolean {
  if (!import.meta.env.DEV) {
    return false;
  }

  return import.meta.env.VITE_ENABLE_DEV_SEED?.trim().toLowerCase() !== "false";
}

export function createDevSeedLogs(): LogEntry[] {
  const timestamp = new Date().toLocaleTimeString("tr-TR", { hour12: false });

  return [
    {
      id: "seed-log-1",
      level: "info",
      message: "Dev seed aktif. Connect ile websocket akisini hizlica test edebilirsiniz.",
      timestamp,
    },
    {
      id: "seed-log-2",
      level: "info",
      message: "Ornek metin textarea icine yuklendi. Speak ile append + flush akisini tetikleyin.",
      timestamp,
    },
  ];
}
