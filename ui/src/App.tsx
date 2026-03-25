import { useState } from "react";
import "./App.css";
import { ControlBar } from "./components/ControlBar";
import { LogPanel } from "./components/LogPanel";
import { StatusBadge } from "./components/StatusBadge";
import { useAudioPlayer } from "./hooks/useAudioPlayer";
import { useTtsWebSocket } from "./hooks/useTtsWebSocket";
import { createDevSeedLogs, INITIAL_TEXT, isDevSeedEnabled } from "./lib/devSeed";

export default function App() {
  const devSeedEnabled = isDevSeedEnabled();
  const [text, setText] = useState(INITIAL_TEXT);
  const audioPlayer = useAudioPlayer();
  const { status, logs, activeRequestId, connection, connect, disconnect, speak, stop, clearLogs } =
    useTtsWebSocket({
      audioPlayer,
      initialLogs: devSeedEnabled ? createDevSeedLogs() : [],
    });

  const connected = status !== "disconnected" && status !== "connecting";

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Realtime Voice Demo</p>
          <h1>Frontend TTS Console</h1>
          <p className="hero-copy">
            Mevcut websocket TTS backend&apos;ine baglanir, request lifecycle&apos;i gorunur kilarken stale
            audio ve stale mesajlari guvenli sekilde drop eder.
          </p>
        </div>
        <div className="hero-meta">
          <StatusBadge status={status} />
          <dl className="meta-grid">
            <div>
              <dt>WebSocket</dt>
              <dd>{connection.wsUrl}</dd>
            </div>
            <div>
              <dt>Request</dt>
              <dd>{activeRequestId ?? "-"}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="panel composer-panel">
        <div className="panel-header">
          <h2>Speech Input</h2>
          <p>Mevcut backend contract&apos;ini bozmadan append + flush akisini kullanir.</p>
        </div>

        <ControlBar
          status={status}
          connected={connected}
          onConnect={connect}
          onDisconnect={disconnect}
          onSpeak={() => speak(text)}
          onStop={stop}
        />

        <label className="textarea-label" htmlFor="tts-input">
          Text
        </label>
        {devSeedEnabled ? <p className="seed-note">Dev seed aktif: ornek metin ve loglar yuklendi.</p> : null}
        <textarea
          id="tts-input"
          className="composer-textarea"
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={8}
          placeholder="Okunacak metni girin"
        />
      </section>

      <LogPanel logs={logs} onClear={clearLogs} />
    </main>
  );
}
