import { useState } from "react";
import type { OutputLanguage } from "../types";
import {
  isSpeechRecognitionSupported,
  startListening,
} from "../services/speech";

interface Props {
  language: OutputLanguage;
  onSend: (text: string) => void;
}

export function ReplyInput({
  language,
  onSend,
}: Props) {
  const [text, setText] = useState("");
  const [listening, setListening] =
    useState(false);
  const [micError, setMicError] =
    useState<string | null>(null);

  const micSupported =
    isSpeechRecognitionSupported();

  const handleSend = () => {
    const trimmed = text.trim();

    if (!trimmed) return;

    onSend(trimmed);
    setText("");
  };

  const handleMicClick = () => {
    if (!micSupported) {
      setMicError(
        "Microphone input isn't supported in this browser."
      );
      return;
    }

    setMicError(null);
    setListening(true);

    startListening(
      language,
      (transcript) =>
        setText((prev) =>
          prev
            ? `${prev} ${transcript}`
            : transcript
        ),
      () => setListening(false),
      (message) => {
        setMicError(message);
        setListening(false);
      }
    );
  };

  return (
    <div className="reply-area">
      <div className="reply-input">
        <span className="reply-input__avatar">
          ◉
        </span>

        <label
          htmlFor="reply-text"
          className="visually-hidden"
        >
          Type your reply
        </label>

        <input
          id="reply-text"
          type="text"
          className="reply-input__field"
          placeholder="Type a reply to the signer…"
          value={text}
          onChange={(e) =>
            setText(e.target.value)
          }
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleSend();
            }
          }}
        />

        <button
          type="button"
          className={`mic-button ${
            listening
              ? "mic-button--active"
              : ""
          }`}
          onClick={handleMicClick}
          aria-label="Speak your reply"
          aria-pressed={listening}
        >
          🎤
        </button>

        <button
          type="button"
          className="send-button"
          onClick={handleSend}
          disabled={!text.trim()}
          aria-label="Send reply"
        >
          <span>➤</span>
        </button>
      </div>

      {micError && (
        <p
          className="reply-input__mic-error"
          role="status"
        >
          {micError}
        </p>
      )}
    </div>
  );
}