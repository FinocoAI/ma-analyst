import { TargetProfile, ScoringWeights, UserFilters, PipelineStatusResponse, ScoredProspect, Signal, ChatMessage } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    let message = `Request failed: ${res.status}`;
    if (typeof err.detail === "string") {
      message = err.detail;
    } else if (Array.isArray(err.detail)) {
      message = err.detail.map((e: any) => e.msg || JSON.stringify(e)).join(", ");
    } else if (err.detail) {
      try {
        message = JSON.stringify(err.detail);
      } catch (e) {
        message = "Unknown error object";
      }
    }
    throw new Error(message || `Request failed: ${res.status}`);
  }
  return res.json();
}

// Pipeline
export async function createPipelineRun(
  url: string,
  filters: UserFilters,
  weights: ScoringWeights
): Promise<{ run_id: string; status: string }> {
  return request("/api/v1/pipeline/run", {
    method: "POST",
    body: JSON.stringify({ url, filters, weights }),
  });
}

export async function getPipelineStatus(runId: string): Promise<PipelineStatusResponse> {
  return request(`/api/v1/pipeline/${runId}/status`);
}

export async function getPipelineRun(runId: string): Promise<any> {
  return request(`/api/v1/pipeline/${runId}`);
}

export async function confirmProfile(runId: string, profile: TargetProfile): Promise<void> {
  return request(`/api/v1/pipeline/${runId}/profile`, {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}

export async function rescorePipeline(runId: string, weights: ScoringWeights): Promise<void> {
  return request(`/api/v1/pipeline/${runId}/rescore`, {
    method: "POST",
    body: JSON.stringify(weights),
  });
}

export async function getProspects(runId: string): Promise<{ prospects: ScoredProspect[]; total: number }> {
  return request(`/api/v1/pipeline/${runId}/prospects`);
}

export async function getSignals(runId: string, filters?: { strength?: string; type?: string }): Promise<{ signals: Signal[]; total: number }> {
  const params = new URLSearchParams();
  if (filters?.strength) params.set("strength", filters.strength);
  if (filters?.type) params.set("signal_type", filters.type);
  return request(`/api/v1/pipeline/${runId}/signals?${params}`);
}

// Chat
export async function sendChatMessage(runId: string, message: string): Promise<{ response: string }> {
  return request(`/api/v1/pipeline/${runId}/chat`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export async function getChatHistory(runId: string): Promise<{ messages: ChatMessage[]; total: number }> {
  return request(`/api/v1/pipeline/${runId}/chat/history`);
}

export function streamChatMessage(runId: string, message: string): Promise<Response> {
  return fetch(`${BASE_URL}/api/v1/pipeline/${runId}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
}
