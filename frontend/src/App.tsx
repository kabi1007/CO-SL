import { useEffect, useState } from "react";
import { Header } from "./components/Header";
import { SignLanguageSelector } from "./components/SignLanguageSelector";
import { LanguageSelector } from "./components/LanguageSelector";
import { CameraPanel } from "./components/CameraPanel";
import { RecognitionPanel } from "./components/RecognitionPanel";
import { Conversation } from "./components/Conversation";
import { ReplyInput } from "./components/ReplyInput";
import { SpeechControls } from "./components/SpeechControls";
import { useCamera } from "./hooks/useCamera";
import { useSignWebSocket } from "./hooks/useSignWebSocket";
import { useSpeech } from "./hooks/useSpeech";
import { fetchModels, createSession, checkHealth } from "./services/api";
import type { ConversationMessage, ModelInfo, OutputLanguage, ServerConfirmedMessage, SignLanguage } from "./types";

type View = "setup" | "workspace";

export default function App() {
  const [view, setView] = useState<View>("setup");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [signLanguage, setSignLanguage] = useState<SignLanguage | null>(null);
  const [outputLanguage, setOutputLanguage] = useState<OutputLanguage>("en");
  const [backendReachable, setBackendReachable] = useState<boolean | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);

  const camera = useCamera();
  const speech = useSpeech();

  useEffect(() => {
    checkHealth().then(setBackendReachable);
    fetchModels()
      .then(setModels)
      .catch(() => setBackendReachable(false));
  }, []);

  const handleConfirmedMessage = (msg: ServerConfirmedMessage) => {
    const entry: ConversationMessage = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      speaker: "signer",
      text: msg.text,
      meaningKey: msg.meaning_key,
      language: msg.language,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, entry]);
    if (speech.autoSpeak && msg.speak) {
      speech.speakText(msg.text, msg.language);
    }
  };

  const ws = useSignWebSocket({
    videoRef: camera.videoRef,
    signLanguage: signLanguage || "ASL",
    outputLanguage,
    active: view === "workspace" && camera.status === "ready" && !!signLanguage,
    onConfirmedMessage: handleConfirmedMessage,
  });

  const latestSignerMessage = [...messages].reverse().find((m) => m.speaker === "signer") || null;

  const handleEnterWorkspace = () => {
    if (!signLanguage) return;

    setView("workspace");
    camera.start();

    void createSession(signLanguage, outputLanguage).catch(() => {
      // Non-fatal for the prototype: the WebSocket route validates independently.
    });
  };

  const handleExitWorkspace = () => {
    camera.stop();
    setView("setup");
  };

  const handleReplay = (message: ConversationMessage) => {
    if (message.language) {
      speech.speakText(message.text, message.language, true);
    }
  };

  const handleListenerReply = (text: string) => {
    const entry: ConversationMessage = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      speaker: "listener",
      text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, entry]);
  };

  return (
    <div className="app-shell">
      <Header
        inWorkspace={view === "workspace"}
        signLanguage={signLanguage}
        outputLanguage={outputLanguage}
        onOutputLanguageChange={setOutputLanguage}
        onExit={view === "workspace" ? handleExitWorkspace : undefined}
      />

      <main className="app-main">
        {backendReachable === false && (
          <div className="banner banner--error" role="alert">
            Can't reach the CO-SL backend. Make sure it's running at the configured API URL.
          </div>
        )}

        {view === "setup" && (
          <section className="setup-screen" aria-label="Session setup">

  <div className="setup-screen__intro-block">
    <span className="setup-screen__kicker">
      CO-SL
    </span>

    <h1 className="setup-screen__title">
      Start a conversation
    </h1>

    <p className="setup-screen__intro">
      Choose how you sign and the language your listener will use.
    </p>
  </div>

  <div className="setup-screen__choices">

    <SignLanguageSelector
      models={models}
      value={signLanguage}
      onChange={setSignLanguage}
    />

    <LanguageSelector
      value={outputLanguage}
      onChange={setOutputLanguage}
    />

  </div>

  <div className="setup-screen__action">
    <button
      type="button"
      className="primary-button primary-button--large"
      disabled={!signLanguage}
      onClick={handleEnterWorkspace}
    >
      Continue
      <span className="setup-screen__arrow">→</span>
    </button>

    <span className="setup-screen__hint">
      You can change these settings later.
    </span>
  </div>

</section>
        )}

        {view === "workspace" && signLanguage && (
          <section className="workspace" aria-label="Communication workspace">
            <CameraPanel
              videoRef={camera.videoRef}
              cameraStatus={camera.status}
              cameraError={camera.errorMessage}
              connectionStatus={ws.connectionStatus}
              demoMode={ws.demoMode}
              signLanguage={signLanguage}
              onStart={camera.start}
              onStop={camera.stop}
            />

            <div className="workspace__right">
              <RecognitionPanel
                latest={latestSignerMessage}
                lastPrediction={ws.lastPrediction}
                onReplay={handleReplay}
              />

              {ws.lastError && (
                <div className="banner banner--warning" role="alert">
                  {ws.lastError.message}
                </div>
              )}

              <Conversation messages={messages} onReplay={handleReplay} />

              <SpeechControls
                autoSpeak={speech.autoSpeak}
                onToggle={speech.setAutoSpeak}
                statusMessage={speech.statusMessage}
              />

              <ReplyInput language={outputLanguage} onSend={handleListenerReply} />
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
