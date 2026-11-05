import type { OutputLanguage } from "../types";

const LANG_TAGS: Record<OutputLanguage, string> = {
  en: "en-IN",
  ta: "ta-IN",
  hi: "hi-IN",
  te: "te-IN",
  ml: "ml-IN",
  kn: "kn-IN",
};

const PREFERRED_VOICES: Partial<Record<OutputLanguage, string[]>> = {
  en: ["Rishi", "Google US English", "Samantha"],
  ta: ["Vani"],
  hi: ["Lekha", "Google हिन्दी"],
  te: ["Geeta"],
  ml: [],
  kn: ["Soumya"],
};

export function isSpeechSynthesisSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

function getVoices(): SpeechSynthesisVoice[] {
  if (!isSpeechSynthesisSupported()) return [];
  return window.speechSynthesis.getVoices();
}

function pickVoice(language: OutputLanguage): SpeechSynthesisVoice | undefined {
  const langTag = LANG_TAGS[language];
  const voices = getVoices();

  const preferredNames = PREFERRED_VOICES[language] ?? [];

  for (const name of preferredNames) {
    const voice = voices.find(
      (v) => v.name === name && v.lang === langTag
    );
    if (voice) return voice;
  }

  const exact = voices.find((v) => v.lang === langTag);
  if (exact) return exact;

  const base = langTag.split("-")[0];
  return voices.find((v) => v.lang.split("-")[0] === base);
}

export function speak(
  text: string,
  language: OutputLanguage
): boolean {
  if (!isSpeechSynthesisSupported()) return false;

  const cleanText = text.trim();
  if (!cleanText) return false;

  const synth = window.speechSynthesis;
  const langTag = LANG_TAGS[language];
  const voice = pickVoice(language);

  const utterance = new SpeechSynthesisUtterance(cleanText);

  utterance.lang = langTag;
  utterance.rate = 0.95;
  utterance.pitch = 1;
  utterance.volume = 1;

  if (voice) {
    utterance.voice = voice;
  }

  utterance.onstart = () => {
    console.log("CO-SL SPEECH START:", {
      language,
      langTag,
      voice: voice?.name ?? "browser default",
      voiceLang: voice?.lang ?? "unknown",
    });
  };

  utterance.onend = () => {
    console.log("CO-SL SPEECH END:", {
      language,
      voice: voice?.name ?? "browser default",
    });
  };

  utterance.onerror = (event) => {
    console.error("CO-SL SPEECH ERROR:", {
      language,
      langTag,
      voice: voice?.name,
      voiceLang: voice?.lang,
      error: event.error,
    });
  };

  console.log("CO-SL SPEAK:", {
    text: cleanText,
    language,
    langTag,
    voice: voice?.name ?? "browser default",
    voiceLang: voice?.lang ?? "unknown",
  });

  synth.speak(utterance);

  return true;
}

export function hasVoiceFor(language: OutputLanguage): boolean {
  if (!isSpeechSynthesisSupported()) return false;
  return !!pickVoice(language);
}

type SpeechRecognitionCtor = new () => SpeechRecognition;

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | undefined {
  const w = window as any;
  return w.SpeechRecognition || w.webkitSpeechRecognition;
}

export function isSpeechRecognitionSupported(): boolean {
  return typeof window !== "undefined" && !!getSpeechRecognitionCtor();
}

export function startListening(
  language: OutputLanguage,
  onResult: (text: string) => void,
  onEnd?: () => void,
  onError?: (message: string) => void
): () => void {
  const Ctor = getSpeechRecognitionCtor();

  if (!Ctor) {
    onError?.("Speech recognition is not supported in this browser.");
    return () => {};
  }

  const recognition = new Ctor() as any;

  recognition.lang = LANG_TAGS[language];
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = (event: SpeechRecognitionEvent) => {
    const text = event.results?.[0]?.[0]?.transcript?.trim();
    if (text) onResult(text);
  };

  recognition.onerror = (event: any) => {
    onError?.(event.error || "Speech recognition failed.");
  };

  recognition.onend = () => {
    onEnd?.();
  };

  recognition.start();

  return () => {
    try {
      recognition.stop();
    } catch {
      // Already stopped.
    }
  };
}
