import type { LogEntry } from "../hooks/useTtsWebSocket";

type Props = {
  logs: LogEntry[];
  onClear: () => void;
};

export function LogPanel({ logs, onClear }: Props) {
  return (
    <section className="panel log-panel">
      <div className="panel-header">
        <h2>Debug Log</h2>
        <button className="secondary-button" onClick={onClear}>
          Clear
        </button>
      </div>
      <ul className="log-list">
        {logs.length === 0 ? <li className="log-empty">Henüz log yok.</li> : null}
        {logs.map((entry) => (
          <li key={entry.id} className={`log-entry log-${entry.level}`}>
            <span className="log-time">{entry.timestamp}</span>
            <span className="log-message">{entry.message}</span>
            {entry.requestId ? <code className="log-request">{entry.requestId}</code> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
