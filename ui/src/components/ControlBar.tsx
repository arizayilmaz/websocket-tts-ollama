import type { UiStatus } from "../hooks/useTtsWebSocket";

type Props = {
  status: UiStatus;
  connected: boolean;
  onConnect: () => void | Promise<void>;
  onDisconnect: () => void | Promise<void>;
  onSpeak: () => void | Promise<unknown>;
  onStop: () => void | Promise<void>;
};

export function ControlBar({
  status,
  connected,
  onConnect,
  onDisconnect,
  onSpeak,
  onStop,
}: Props) {
  const busy = status === "connecting" || status === "stopping";

  return (
    <div className="control-bar">
      <button onClick={() => void onConnect()} disabled={connected || status === "connecting"}>
        Connect
      </button>
      <button onClick={() => void onDisconnect()} disabled={!connected && status === "disconnected"}>
        Disconnect
      </button>
      <button onClick={() => void onSpeak()} disabled={!connected || busy}>
        Speak
      </button>
      <button onClick={() => void onStop()} disabled={!connected || status === "idle" || status === "disconnected"}>
        Stop
      </button>
    </div>
  );
}
