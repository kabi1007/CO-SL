import type {
  ConversationMessage,
  ServerPredictionMessage,
} from "../types";

interface Props {
  latest: ConversationMessage | null;
  lastPrediction: ServerPredictionMessage | null;
  onReplay: (message: ConversationMessage) => void;
}

export function RecognitionPanel({
  latest,
  lastPrediction,
  onReplay,
}: Props) {
  const confidence = lastPrediction
    ? Math.round(lastPrediction.confidence * 100)
    : null;

  return (
    <section
      className="recognition-panel"
      aria-live="polite"
    >
      <div className="recognition-panel__header">
        <div>
          <span className="section-kicker">
            LIVE INTERPRETATION
          </span>

          <h1>What the signer is saying</h1>
        </div>

        {lastPrediction && (
          <span
            className={`recognition-state ${
              lastPrediction.stable
                ? "recognition-state--confirmed"
                : ""
            }`}
          >
            <span />
            {lastPrediction.stable
              ? "Confirmed"
              : "Reading"}
          </span>
        )}
      </div>

      {latest ? (
        <div className="recognition-message">
          <span className="recognition-message__label">
            Recognized meaning
          </span>

          <h2>{latest.text}</h2>

          <div className="recognition-message__actions">
            {confidence !== null && (
              <div className="recognition-confidence">
                <div className="recognition-confidence__bar">
                  <span
                    style={{
                      width: `${confidence}%`,
                    }}
                  />
                </div>

                <div className="recognition-confidence__text">
                  <strong>{confidence}%</strong>
                  <span>confidence</span>
                </div>
              </div>
            )}

            <button
              type="button"
              className="recognition-play"
              onClick={() => onReplay(latest)}
              aria-label={`Play ${latest.text}`}
            >
              <span className="recognition-play__icon">
                ▶
              </span>
              <span>Play message</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="recognition-empty">
          <div className="recognition-empty__orb">
            🤟
          </div>

          <div>
            <h2>Ready when you are</h2>
            <p>
              Show a supported sign in the camera to begin
              the conversation.
            </p>
          </div>
        </div>
      )}

      {lastPrediction &&
        !lastPrediction.stable &&
        confidence !== null && (
          <div className="recognition-reading">
            <span className="recognition-reading__pulse" />
            Interpreting gesture · {confidence}%
          </div>
        )}
    </section>
  );
}