import type { ModelInfo, SignLanguage } from "../types";

interface Props {
  models: ModelInfo[];
  value: SignLanguage | null;
  onChange: (value: SignLanguage) => void;
}

const OPTIONS: {
  code: SignLanguage;
  name: string;
  description: string;
  icon: string;
}[] = [
  {
    code: "ASL",
    name: "American Sign Language",
    description: "For ASL signing",
    icon: "A",
  },
  {
    code: "ISL",
    name: "Indian Sign Language",
    description: "For ISL signing",
    icon: "I",
  },
];

export function SignLanguageSelector({
  models,
  value,
  onChange,
}: Props) {
  return (
    <fieldset className="sign-language-card">
      <div className="sign-language-card__heading">
        <div>
          <span className="sign-language-card__kicker">
            SIGN LANGUAGE
          </span>

          <h2 className="sign-language-card__title">
            Choose how you sign
          </h2>

          <p className="sign-language-card__description">
            Select the sign language you will use with CO-SL.
          </p>
        </div>

        <span className="sign-language-card__icon">
          🤟
        </span>
      </div>

      <div className="sign-language-options">
        {OPTIONS.map((option) => {
          const model = models.find(
            (item) => item.id === option.code
          );

          const disabled = model ? !model.available : false;
          const selected = value === option.code;

          return (
            <button
              key={option.code}
              type="button"
              className={`sign-language-option ${
                selected
                  ? "sign-language-option--selected"
                  : ""
              }`}
              disabled={disabled}
              onClick={() => onChange(option.code)}
              aria-pressed={selected}
            >
              <span className="sign-language-option__icon">
                {option.icon}
              </span>

              <span className="sign-language-option__content">
                <span className="sign-language-option__code">
                  {option.code}
                </span>

                <span className="sign-language-option__name">
                  {option.name}
                </span>

                <span className="sign-language-option__description">
                  {disabled
                    ? "Model unavailable"
                    : option.description}
                </span>
              </span>

              {selected && (
                <span className="sign-language-option__check">
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