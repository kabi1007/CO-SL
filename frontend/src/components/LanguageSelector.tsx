import type { OutputLanguage } from "../types";

interface Props {
  value: OutputLanguage;
  onChange: (value: OutputLanguage) => void;
  compact?: boolean;
  id?: string;
}

const OPTIONS: {
  code: OutputLanguage;
  label: string;
  native: string;
}[] = [
  { code: "en", label: "English", native: "English" },
  { code: "ta", label: "Tamil", native: "தமிழ்" },
  { code: "hi", label: "Hindi", native: "हिन्दी" },
  { code: "te", label: "Telugu", native: "తెలుగు" },
  { code: "ml", label: "Malayalam", native: "മലയാളം" },
  { code: "kn", label: "Kannada", native: "ಕನ್ನಡ" },
];

export function LanguageSelector({
  value,
  onChange,
  compact,
}: Props) {
  if (compact) {
    return (
      <div className="language-mini">
        <span className="language-mini__icon">🌐</span>

        <select
          className="language-mini__select"
          value={value}
          onChange={(e) =>
            onChange(e.target.value as OutputLanguage)
          }
          aria-label="Listener output language"
        >
          {OPTIONS.map((option) => (
            <option key={option.code} value={option.code}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <fieldset className="language-card">
      <div className="language-card__heading">
        <div>
          <span className="language-card__kicker">
            LISTENER LANGUAGE
          </span>

          <h2 className="language-card__title">
            Choose a language
          </h2>

          <p className="language-card__description">
            The recognized sign will be shown and spoken
            in this language.
          </p>
        </div>

        <span className="language-card__globe">
          🌐
        </span>
      </div>

      <div className="language-card__options">
        {OPTIONS.map((option) => {
          const selected = value === option.code;

          return (
            <button
              key={option.code}
              type="button"
              className={`language-option ${
                selected ? "language-option--selected" : ""
              }`}
              onClick={() => onChange(option.code)}
              aria-pressed={selected}
            >
              <span className="language-option__native">
                {option.native}
              </span>

              <span className="language-option__name">
                {option.label}
              </span>

              {selected && (
                <span className="language-option__check">
                  ✓
                </span>
              )}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}