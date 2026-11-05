import { useCallback, useRef, useState } from "react";

import type { OutputLanguage } from "../types";

import {
  hasVoiceFor,
  isSpeechSynthesisSupported,
  speak,
} from "../services/speech";

const SARVAM_LANGUAGES: OutputLanguage[] = [
  "ta",
  "hi",
  "te",
  "ml",
  "kn",
];

export function useSpeech() {
  const [autoSpeak, setAutoSpeak] = useState(true);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const lastSpokenRef = useRef<string | null>(null);
  const lastLanguageRef = useRef<OutputLanguage | null>(null);
  const lastSpokenAtRef = useRef(0);

  const speakText = useCallback(
    async (text: string, language: OutputLanguage, force = false) => {
      const cleanText = text.trim();

      if (!cleanText) {
        return;
      }

      const now = Date.now();

      const sameMessage =
        lastSpokenRef.current === cleanText &&
        lastLanguageRef.current === language;

      const withinCooldown =
        now - lastSpokenAtRef.current < 2500;

      if (!force && sameMessage && withinCooldown) {
        return;
      }

      lastSpokenRef.current = cleanText;
      lastLanguageRef.current = language;
      lastSpokenAtRef.current = now;

      try {
        if (SARVAM_LANGUAGES.includes(language)) {
          setStatusMessage("Generating speech...");

          const response = await fetch("/api/tts", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              text: cleanText,
              language,
            }),
          });

          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `TTS request failed: ${response.status}`);
          }

          const audioBlob = await response.blob();
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);

          audio.onplay = () => {
            console.log("CO-SL SARVAM SPEECH START:", {
              language,
              text: cleanText,
            });
            setStatusMessage(null);
          };

          audio.onended = () => {
            console.log("CO-SL SARVAM SPEECH END:", {
              language,
            });
            URL.revokeObjectURL(audioUrl);
          };

          audio.onerror = () => {
            console.error("CO-SL SARVAM SPEECH ERROR:", {
              language,
            });
            URL.revokeObjectURL(audioUrl);
            setStatusMessage("Speech playback failed.");
          };

          await audio.play();
          return;
        }

        if (!isSpeechSynthesisSupported()) {
          setStatusMessage("Speech unavailable in this browser.");
          return;
        }

        if (!hasVoiceFor(language) && language !== "en") {
          setStatusMessage(
            "No matching voice for this language - using default voice."
          );
        } else {
          setStatusMessage(null);
        }

        const synth = window.speechSynthesis;

        if (synth.speaking || synth.pending) {
          synth.cancel();
        }

        speak(cleanText, language);
      } catch (error) {
        console.error("CO-SL SPEECH ERROR:", error);
        setStatusMessage("Speech generation failed.");
      }
    },
    []
  );

  return {
    autoSpeak,
    setAutoSpeak,
    statusMessage,
    speakText,
  };
}
