import { useEffect, useRef } from "react";
import type { ConversationMessage } from "../types";
import { MessageBubble } from "./MessageBubble";

interface Props {
  messages: ConversationMessage[];
  onReplay: (message: ConversationMessage) => void;
}

export function Conversation({
  messages,
  onReplay,
}: Props) {
  const listRef = useRef<HTMLUListElement | null>(null);

  useEffect(() => {
    const list = listRef.current;

    if (!list) return;

    // Keep the conversation box fixed.
    // Only the messages inside it move upward.
    list.scrollTo({
      top: list.scrollHeight,
      behavior: "smooth",
    });
  }, [messages.length]);

  return (
    <section
      className="conversation"
      aria-label="Conversation history"
    >
      <div className="conversation__header">
        <div>
          <span className="section-kicker">
            CONVERSATION
          </span>

          <h2>Live exchange</h2>
        </div>

        <span className="conversation__count">
          {messages.length}
        </span>
      </div>

      {messages.length === 0 ? (
        <div className="conversation__empty">
          <span>○</span>

          <p>
            Your conversation will appear here as signs
            are recognized.
          </p>
        </div>
      ) : (
        <ul
          ref={listRef}
          className="conversation__list"
        >
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onReplay={onReplay}
            />
          ))}
        </ul>
      )}
    </section>
  );
}