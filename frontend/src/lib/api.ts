import type {
  ArtifactDownloadOut,
  AuditLogFile,
  DocumentOut,
  DownloadOut,
  EvaluationRunOut,
  JobDetailOut,
  JobOut,
  PIIType,
  PIITypeInfo,
  PolicyOut,
  RedactionStrategy,
  ReplacementMapFile,
  ReviewDecision,
} from "@/lib/types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1").replace(/\/+$/, "");
const API_KEY = process.env.NEXT_PUBLIC_API_KEY;
const API_ORIGIN = API_URL.replace(/\/api\/v1$/, "");

/**
 * `DownloadOut.url` from the backend is root-relative (e.g. `/api/v1/files/download?token=...`),
 * not relative to API_URL (which already ends in `/api/v1`) — resolve against the bare origin.
 */
export function resolveFileUrl(download: DownloadOut): string {
  return download.url.startsWith("http") ? download.url : `${API_ORIGIN}${download.url}`;
}

export class ApiRequestError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (API_KEY) headers.set("X-API-Key", API_KEY);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (!res.ok) {
    let code = "unknown_error";
    let message = res.statusText || "Request failed";
    try {
      const body = await res.json();
      code = body.error ?? code;
      message = body.message ?? message;
    } catch {
      // non-JSON error body; keep the defaults
    }
    throw new ApiRequestError(res.status, code, message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Fetches JSON content that lives behind a signed-URL artifact endpoint (map/audit log). */
async function fetchArtifact<T>(download: DownloadOut): Promise<T> {
  const res = await fetch(resolveFileUrl(download));
  if (!res.ok) throw new ApiRequestError(res.status, "artifact_fetch_failed", "Failed to fetch report artifact.");
  return (await res.json()) as T;
}

export const api = {
  baseUrl: API_URL,

  documents: {
    upload: (file: File): Promise<DocumentOut> => {
      const form = new FormData();
      form.append("file", file);
      return request<DocumentOut>("/documents", { method: "POST", body: form });
    },
    get: (documentId: string) => request<DocumentOut>(`/documents/${documentId}`),
    downloadUrl: (documentId: string) => request<DownloadOut>(`/documents/${documentId}/download`),
  },

  policies: {
    list: () => request<PolicyOut[]>("/policies"),
    get: (policyId: string) => request<PolicyOut>(`/policies/${policyId}`),
    create: (payload: {
      name: string;
      strategy_map: Partial<Record<PIIType, RedactionStrategy>>;
      confidence_floor: number;
    }) => request<PolicyOut>("/policies", { method: "POST", body: JSON.stringify(payload) }),
    update: (
      policyId: string,
      payload: Partial<{
        name: string;
        strategy_map: Partial<Record<PIIType, RedactionStrategy>>;
        confidence_floor: number;
      }>,
    ) => request<PolicyOut>(`/policies/${policyId}`, { method: "PUT", body: JSON.stringify(payload) }),
  },

  piiTypes: {
    list: () => request<PIITypeInfo[]>("/pii-types"),
  },

  jobs: {
    list: () => request<JobOut[]>("/jobs"),
    create: (payload: { document_id: string; policy_id: string; pii_types: PIIType[] }) =>
      request<JobOut>("/jobs", { method: "POST", body: JSON.stringify(payload) }),
    get: (jobId: string) => request<JobDetailOut>(`/jobs/${jobId}`),
    reviewDetection: (jobId: string, detectionId: string, decision: ReviewDecision, newPiiType?: PIIType | null) =>
      request(`/jobs/${jobId}/detections/${detectionId}`, {
        method: "PATCH",
        body: JSON.stringify({ decision, new_pii_type: newPiiType ?? null }),
      }),
    redact: (jobId: string) => request<JobOut>(`/jobs/${jobId}/redact`, { method: "POST" }),
    downloadUrl: (jobId: string) => request<DownloadOut>(`/jobs/${jobId}/download`),
    artifacts: (jobId: string) => request<ArtifactDownloadOut>(`/jobs/${jobId}/artifacts`),
    streamUrl: (jobId: string) => `${API_URL}/jobs/${jobId}/stream`,
  },

  evaluation: {
    createRun: (dataset = "bundled_sample") =>
      request<EvaluationRunOut>("/evaluation/runs", { method: "POST", body: JSON.stringify({ dataset }) }),
    getRun: (runId: string) => request<EvaluationRunOut>(`/evaluation/runs/${runId}`),
  },

  artifacts: {
    replacementMap: (download: DownloadOut) => fetchArtifact<ReplacementMapFile>(download),
    auditLog: (download: DownloadOut) => fetchArtifact<AuditLogFile>(download),
  },
};
