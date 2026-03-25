import type { UiStatus } from "../hooks/useTtsWebSocket";

const LABELS: Record<UiStatus, string> = {
  disconnected: "Disconnected",
  connecting: "Connecting",
  idle: "Idle",
  streaming: "Streaming",
  stopping: "Stopping",
  error: "Error",
};

export function StatusBadge({ status }: { status: UiStatus }) {
  return (
    <span className={`status-badge status-${status}`} data-testid="status-badge">
      {LABELS[status]}
    </span>
  );
}
