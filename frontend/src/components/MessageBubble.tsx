import type { ConversationMessage } from "../types";

interface Props {
  message: ConversationMessage;
  onReplay?: (message: ConversationMessage) => void;
}

export function MessageBubble({
  message,
  onReplay,
}: Props) {
  const isSigner = message.speaker === "signer";

  const time = new Date(
    message.timestamp
  ).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <li
      className={`message-bubble message-bubble--${
        message.speaker
      }`}
    >
      <div className="message-bubble__top">
        <span className="message-bubble__speaker">
          {isSigner ? "SIGNER" : "LISTENER"}
        </span>

        <span className="message-bubble__time">
          {time}
        </span>
      </div>

      <p className="message-bubble__text">
        {message.text}
      </p>

      {isSigner && onReplay && (
        <button
          type="button"
          className="replay-button replay-button--inline"
          onClick={() => onReplay(message)}
          aria-label={`Replay: ${message.text}`}
        >
          <span>▶</span>
          Replay
        </button>
      )}
    </li>
  );
}