interface Props {
  autoSpeak: boolean;
  onToggle: (value: boolean) => void;
  statusMessage: string | null;
}

export function SpeechControls({
  autoSpeak,
  onToggle,
  statusMessage,
}: Props) {
  return (
    <div className="speech-controls">
      <div className="speech-controls__info">
        <span className="speech-controls__icon">
          🔊
        </span>

        <div>
          <strong>Auto-speak</strong>
          <span>
            Read recognized signs aloud
          </span>
        </div>
      </div>

      <label className="toggle">
        <input
          type="checkbox"
          checked={autoSpeak}
          onChange={(e) =>
            onToggle(e.target.checked)
          }
        />

        <span className="toggle__track">
          <span className="toggle__thumb" />
        </span>
      </label>

      {statusMessage && (
        <span
          className="speech-controls__status"
          role="status"
        >
          {statusMessage}
        </span>
      )}
    </div>
  );
}