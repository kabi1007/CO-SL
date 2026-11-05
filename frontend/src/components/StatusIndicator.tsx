type Tone = "positive" | "neutral" | "warning" | "negative";

interface Props {
  label: string;
  tone: Tone;
}

const SYMBOLS: Record<Tone, string> = {
  positive: "●",
  neutral: "○",
  warning: "⚠",
  negative: "✕",
};

export function StatusIndicator({ label, tone }: Props) {
  return (
    <span className={`status-indicator status-indicator--${tone}`}>
      <span aria-hidden="true">{SYMBOLS[tone]}</span>
      <span>{label}</span>
    </span>
  );
}
