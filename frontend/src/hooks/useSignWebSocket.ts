import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ConnectionStatus,
  OutputLanguage,
  ServerConfirmedMessage,
  ServerErrorMessage,
  ServerMessage,
  ServerPredictionMessage,
  SignLanguage,
} from "../types";

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000";
const FRAME_INTERVAL_MS = 150;
const MAX_RECONNECT_ATTEMPTS = 4;

interface UseSignWebSocketOptions {
  videoRef: React.RefObject<HTMLVideoElement>;
  signLanguage: SignLanguage;
  outputLanguage: OutputLanguage;
  active: boolean;
  onConfirmedMessage: (msg: ServerConfirmedMessage) => void;
}

export function useSignWebSocket({
  videoRef,
  signLanguage,
  outputLanguage,
  active,
  onConfirmedMessage,
}: UseSignWebSocketOptions) {
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("disconnected");

  const [demoMode, setDemoMode] = useState(false);
  const [lastPrediction, setLastPrediction] =
    useState<ServerPredictionMessage | null>(null);
  const [lastError, setLastError] =
    useState<ServerErrorMessage | null>(null);
  const [recognizing, setRecognizing] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const frameTimerRef = useRef<number | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const reconnectAttemptsRef = useRef(0);
  const connectionIdRef = useRef(0);

  const outputLanguageRef = useRef(outputLanguage);
  const onConfirmedMessageRef = useRef(onConfirmedMessage);

  outputLanguageRef.current = outputLanguage;
  onConfirmedMessageRef.current = onConfirmedMessage;

  const stopFrameLoop = useCallback(() => {
    if (frameTimerRef.current !== null) {
      window.clearInterval(frameTimerRef.current);
      frameTimerRef.current = null;
    }
  }, []);

  const stopReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const sendFrame = useCallback(() => {
    const video = videoRef.current;
    const ws = wsRef.current;

    if (!video || !ws || ws.readyState !== WebSocket.OPEN) return;
    if (video.readyState < 2) return;

    if (!canvasRef.current) {
      canvasRef.current = document.createElement("canvas");
    }

    const canvas = canvasRef.current;

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const ctx = canvas.getContext("2d");

    if (!ctx) return;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) return;

        blob.arrayBuffer().then((buf) => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(buf);
          }
        });
      },
      "image/jpeg",
      0.7
    );
  }, [videoRef]);

  const connect = useCallback(() => {
    stopFrameLoop();
    stopReconnectTimer();

    setConnectionStatus("connecting");

    /*
     * Every connection gets its own ID.
     * Old sockets are not allowed to reconnect after they have
     * been replaced or cleaned up.
     */
    const connectionId = ++connectionIdRef.current;

    const url =
      `${WS_BASE_URL}/ws/sign/${signLanguage}` +
      `?output_language=${outputLanguageRef.current}`;

    const ws = new WebSocket(url);

    wsRef.current = ws;

    ws.onopen = () => {
      // Ignore old socket events.
      if (connectionId !== connectionIdRef.current) return;

      reconnectAttemptsRef.current = 0;
      setLastError(null);
    };

    ws.onmessage = (event) => {
      console.log("CO-SL WS MESSAGE:", event.data);
      // Ignore messages from an old socket.
      if (connectionId !== connectionIdRef.current) return;

      let data: ServerMessage;

      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }

      if (data.type === "status") {
        if (data.state === "ready") {
          setConnectionStatus("connected");
          setDemoMode(!!data.demo_mode);

          stopFrameLoop();

          frameTimerRef.current = window.setInterval(
            sendFrame,
            FRAME_INTERVAL_MS
          );
        } else if (data.state === "listening") {
          setRecognizing(true);
        }
      } else if (data.type === "prediction") {
        setLastPrediction(data);
        setLastError(null);
      } else if (data.type === "message") {
        onConfirmedMessageRef.current(data);
      } else if (data.type === "error") {
        setLastError(data);
        setConnectionStatus("error");
      }
    };

    ws.onerror = () => {
      // Ignore errors from old sockets.
      if (connectionId !== connectionIdRef.current) return;

      setConnectionStatus("error");
    };

    ws.onclose = () => {
      stopFrameLoop();

      /*
       * CRITICAL:
       * Only the currently active socket is allowed to reconnect.
       *
       * This prevents an old socket from creating Socket 3,
       * Socket 4, Socket 5, etc.
       */
      if (connectionId !== connectionIdRef.current) {
        return;
      }

      if (
        active &&
        reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS
      ) {
        reconnectAttemptsRef.current += 1;

        const delay = 1000 * reconnectAttemptsRef.current;

        setConnectionStatus("reconnecting");

        reconnectTimerRef.current = window.setTimeout(() => {
          reconnectTimerRef.current = null;

          if (
            active &&
            connectionId === connectionIdRef.current
          ) {
            connect();
          }
        }, delay);
      } else if (active) {
        setConnectionStatus("error");

        setLastError({
          type: "error",
          code: "connection_lost",
          message: "Lost connection to the recognition server.",
        });
      } else {
        setConnectionStatus("disconnected");
      }
    };
  }, [
    signLanguage,
    sendFrame,
    stopFrameLoop,
    stopReconnectTimer,
    active,
  ]);

  const disconnect = useCallback(() => {
    /*
     * Invalidate the current connection first.
     * This makes any late onclose/onerror/onmessage events harmless.
     */
    connectionIdRef.current += 1;

    stopFrameLoop();
    stopReconnectTimer();

    reconnectAttemptsRef.current = MAX_RECONNECT_ATTEMPTS;

    const ws = wsRef.current;
    wsRef.current = null;

    if (ws) {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;

      if (
        ws.readyState === WebSocket.OPEN ||
        ws.readyState === WebSocket.CONNECTING
      ) {
        ws.close();
      }
    }

    setRecognizing(false);
    setConnectionStatus("disconnected");
  }, [stopFrameLoop, stopReconnectTimer]);

  useEffect(() => {
    if (active) {
      reconnectAttemptsRef.current = 0;
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [active, signLanguage, connect, disconnect]);

  /*
   * Change output language without creating another WebSocket.
   */
  useEffect(() => {
    const ws = wsRef.current;

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: "set_language",
          language: outputLanguage,
        })
      );
    }
  }, [outputLanguage]);

  return {
    connectionStatus,
    demoMode,
    lastPrediction,
    lastError,
    recognizing,
  };
}