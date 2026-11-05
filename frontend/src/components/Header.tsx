import type { OutputLanguage, SignLanguage } from "../types";
import { LanguageSelector } from "./LanguageSelector";

interface Props {
  inWorkspace: boolean;
  signLanguage: SignLanguage | null;
  outputLanguage: OutputLanguage;
  onOutputLanguageChange: (lang: OutputLanguage) => void;
  onExit?: () => void;
}

export function Header({
  inWorkspace,
  signLanguage,
  outputLanguage,
  onOutputLanguageChange,
  onExit,
}: Props) {
  return (
    <header className="app-header">
      <div className="app-header__brand">
        <div className="app-header__mark">
          <span>CO</span>
          <span className="app-header__mark-dot" />
          <span>SL</span>
        </div>

        <div className="app-header__identity">
          <span className="app-header__title">CO-SL</span>
          <span className="app-header__subtitle">
            Sign. Translate. Connect.
          </span>
        </div>
      </div>

      {inWorkspace && signLanguage && (
        <div className="app-header__workspace">
          <div className="app-header__mode">
            <span className="app-header__mode-dot" />
            <span>LIVE SESSION</span>
          </div>

          <div className="app-header__language">
            <span className="app-header__language-label">
              SIGN
            </span>
            <strong>{signLanguage}</strong>
          </div>

          <div className="app-header__language">
            <span className="app-header__language-label">
              OUTPUT
            </span>

            <LanguageSelector
              value={outputLanguage}
              onChange={onOutputLanguageChange}
              compact
            />
          </div>

          {onExit && (
            <button
              type="button"
              className="app-header__settings"
              onClick={onExit}
            >
              Change
            </button>
          )}
        </div>
      )}
    </header>
  );
}