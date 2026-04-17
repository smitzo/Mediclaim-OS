export type JobStatus = "queued" | "processing" | "succeeded" | "partial" | "failed";

export type ClaimJob = {
  job_id: string;
  claim_id: string;
  filename: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  page_count: number;
  file_size_bytes: number;
  error?: string | null;
  result_url?: string | null;
};

export type ClaimResponse = {
  claim_id: string;
  status: string;
  page_classification: Array<Record<string, unknown>>;
  extracted_data: Record<string, unknown>;
  errors: string[];
  processing_summary: Record<string, unknown>;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export async function listJobs(): Promise<ClaimJob[]> {
  const response = await fetch(`${API_BASE_URL}/api/claims?limit=100`, {
    cache: "no-store"
  });
  return parseResponse<ClaimJob[]>(response);
}

export async function submitClaims(files: File[]): Promise<{ jobs: ClaimJob[]; rejected: Array<Record<string, string>> }> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));

  const response = await fetch(`${API_BASE_URL}/api/claims/batch`, {
    method: "POST",
    body: form
  });
  return parseResponse(response);
}

export async function getClaimResult(jobId: string): Promise<ClaimResponse> {
  const response = await fetch(`${API_BASE_URL}/api/claims/${jobId}/result`, {
    cache: "no-store"
  });
  return parseResponse<ClaimResponse>(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return response.json() as Promise<T>;
  }

  let message = `Request failed with ${response.status}`;
  try {
    const payload = await response.json();
    if (payload?.detail) {
      message = Array.isArray(payload.detail) ? payload.detail.map(String).join(", ") : String(payload.detail);
    }
  } catch {
    // Keep the status-based message when the server does not return JSON.
  }
  throw new Error(message);
}
