import type React from "react";
import type {
  CameraStatus,
  ConnectionStatus,
  SignLanguage,
} from "../types";
import { StatusIndicator } from "./StatusIndicator";

interface Props {
  videoRef: React.RefObject<HTMLVideoElement>;
  cameraStatus: CameraStatus;
  cameraError: string | null;
  connectionStatus: ConnectionStatus;
  demoMode: boolean;
  signLanguage: SignLanguage;
  onStart: () => void;
  onStop: () => void;
}

function cameraStatusView(
  status: CameraStatus,
  error: string | null
) {
  switch (status) {
    case "ready":
      return <StatusIndicator label="Ready" tone="positive" />;

    case "requesting":
      return (
        <StatusIndicator
          label="Connecting…"
          tone="neutral"
        />
      );

    case "permission_denied":
      return (
        <StatusIndicator
          label={error || "Camera permission required"}
          tone="warning"
        />
      );

    case "unavailable":
      return (
        <StatusIndicator
          label={error || "Camera unavailable"}
          tone="negative"
        />
      );

    case "error":
      return (
        <StatusIndicator
          label={error || "Camera error"}
          tone="negative"
        />
      );

    default:
      return (
        <StatusIndicator
          label="Not started"
          tone="neutral"
        />
      );
  }
}

function connectionStatusView(
  status: ConnectionStatus,
  demoMode: boolean
) {
  if (demoMode && status === "connected") {
    return (
      <StatusIndicator
        label="Demo mode"
        tone="warning"
      />
    );
  }

  switch (status) {
    case "connected":
      return (
        <StatusIndicator
          label="Listening"
          tone="positive"
        />
      );

    case "connecting":
      return (
        <StatusIndicator
          label="Connecting…"
          tone="neutral"
        />
      );

    case "reconnecting":
      return (
        <StatusIndicator
          label="Reconnecting…"
          tone="warning"
        />
      );

    case "error":
      return (
        <StatusIndicator
          label="Recognition unavailable"
          tone="negative"
        />
      );

    default:
      return (
        <StatusIndicator
          label="Idle"
          tone="neutral"
        />
      );
  }
}

export function CameraPanel({
  videoRef,
  cameraStatus,
  cameraError,
  connectionStatus,
  demoMode,
  signLanguage,
  onStart,
  onStop,
}: Props) {
  return (
    <section
      className="camera-panel"
      aria-label="Live signer camera"
    >
      <div className="camera-panel__frame">
        <video
          ref={videoRef}
          className="camera-panel__video"
          autoPlay
          playsInline
          muted
          aria-label="Live camera preview of the signer"
        />

        {cameraStatus !== "ready" && (
          <div className="camera-panel__placeholder">
            {cameraStatus === "requesting" && (
              <div className="camera-panel__placeholder-content">
                <span className="camera-panel__loader" />
                <p>Connecting camera…</p>
              </div>
            )}

            {cameraStatus === "idle" && (
              <div className="camera-panel__placeholder-content">
                <span className="camera-panel__placeholder-icon">
                  ◉
                </span>
                <p>Camera is off</p>
                <small>
                  Start the camera to begin signing.
                </small>
              </div>
            )}

            {(cameraStatus === "permission_denied" ||
              cameraStatus === "unavailable" ||
              cameraStatus === "error") && (
              <div className="camera-panel__placeholder-content">
                <span className="camera-panel__placeholder-icon">
                  !
                </span>
                <p role="alert">
                  {cameraError || "Camera unavailable."}
                </p>
              </div>
            )}
          </div>
        )}

        <div className="camera-panel__top">
          <div className="camera-live-pill">
            <span className="camera-live-pill__dot" />
            LIVE
          </div>

          <div className="camera-sign-pill">
            {signLanguage}
          </div>
        </div>

        <div className="camera-panel__bottom">
          <div className="camera-panel__recognition">
            <span className="camera-panel__tiny-label">
              Recognition
            </span>

            <div className="camera-panel__recognition-status">
              {cameraStatusView(cameraStatus, cameraError)}
              <span className="camera-panel__divider" />
              {connectionStatusView(
                connectionStatus,
                demoMode
              )}
            </div>
          </div>

          <button
            type="button"
            className={`camera-action ${
              cameraStatus === "ready"
                ? "camera-action--stop"
                : ""
            }`}
            onClick={
              cameraStatus === "ready"
                ? onStop
                : onStart
            }
          >
            <span className="camera-action__icon">
              {cameraStatus === "ready" ? "■" : "▶"}
            </span>

            {cameraStatus === "ready"
              ? "Stop"
              : "Start camera"}
          </button>
        </div>
      </div>

      <div className="camera-panel__privacy">
        <span>⌁</span>
        Camera feed is processed for live recognition and
        isn't stored.
      </div>
    </section>
  );
}