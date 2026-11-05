export type SignLanguage = "ASL" | "ISL";
export type OutputLanguage = "en" | "ta" | "hi" | "te" | "ml" | "kn";

export interface ModelInfo {
  id: SignLanguage;
  name: string;
  available: boolean;
  demo_mode?: boolean;
}

export type ServerMessageType = "status" | "prediction" | "message" | "error";

export interface ServerStatusMessage {
  type: "status";
  state: "ready" | "listening" | "reset" | "language_ack";
  sign_language?: SignLanguage;
  demo_mode?: boolean;
  ready_frames?: number;
  required_frames?: number;
  language?: string;
}

export interface ServerPredictionMessage {
  type: "prediction";
  sign_language: SignLanguage;
  label: string;
  meaning_key: string | null;
  confidence: number;
  stable: boolean;
}

export interface ServerConfirmedMessage {
  type: "message";
  speaker: "signer";
  meaning_key: string;
  language: OutputLanguage;
  text: string;
  speak: boolean;
}

export interface ServerErrorMessage {
  type: "error";
  code: string;
  message: string;
}

export type ServerMessage =
  | ServerStatusMessage
  | ServerPredictionMessage
  | ServerConfirmedMessage
  | ServerErrorMessage;

export type Speaker = "signer" | "listener";

export interface ConversationMessage {
  id: string;
  speaker: Speaker;
  text: string;
  originalText?: string;
  meaningKey?: string;
  language?: OutputLanguage;
  timestamp: number;
}

export type CameraStatus =
  | "idle"
  | "requesting"
  | "ready"
  | "permission_denied"
  | "unavailable"
  | "error";

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error";
