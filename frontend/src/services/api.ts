import type { ModelInfo, OutputLanguage, SignLanguage } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchModels(): Promise<ModelInfo[]> {
  const res = await fetch(`${API_BASE_URL}/api/models`);
  if (!res.ok) throw new Error("Failed to reach CO-SL backend.");
  const data = await res.json();
  return data.models as ModelInfo[];
}

export async function createSession(
  signLanguage: SignLanguage,
  outputLanguage: OutputLanguage
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sign_language: signLanguage,
      output_language: outputLanguage,
    }),
  });
  if (!res.ok) throw new Error("Failed to create session.");
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
