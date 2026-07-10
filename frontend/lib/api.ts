import { apiFetch } from "./http";

export type JobStatus = "queued" | "processing" | "succeeded" | "partial" | "failed";

export type ClaimJob = {
  job_id: string;
  tenant_id: string;
  claim_id: string;
  filename: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  page_count: number;
  file_size_bytes: number;
  retry_count?: number;
  error?: string | null;
  result_url?: string | null;
};

export type FieldEvidence = { source_page?: number | null; supporting_text?: string | null; verification: string; method: string; confidence: number | null };
export type ValidationFinding = { id: string; code: string; severity: string; fields: string[]; message: string };

export type ClaimResponse = {
  schema_version?: string;
  field_evidence?: Record<string, FieldEvidence>;
  validation_findings?: ValidationFinding[];
  claim_id: string;
  status: string;
  page_classification: Array<Record<string, unknown>>;
  extracted_data: Record<string, unknown>;
  errors: string[];
  processing_summary: Record<string, unknown>;
};

export type ReviewStatus = "needs_review" | "approved" | "rejected" | "corrected";

export type ClaimReview = {
  version: number;
  result_version: number;
  acknowledged_findings: string[];
  validation_findings?: ValidationFinding[];
  job_id: string;
  tenant_id: string;
  status: ReviewStatus;
  reviewer?: string | null;
  notes: string;
  corrected_data: Record<string, unknown>;
  updated_at: string;
};



export async function listJobs(): Promise<ClaimJob[]> {
  const response = await apiFetch(`/api/claims?limit=100`, {
    cache: "no-store",
  });
  return parseResponse<ClaimJob[]>(response);
}

export async function submitClaims(files: File[]): Promise<{ jobs: ClaimJob[]; rejected: Array<Record<string, string>> }> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));

  const response = await apiFetch(`/api/claims/batch`, {
    method: "POST",
    body: form
  });
  return parseResponse(response);
}

export async function getClaimResult(jobId: string): Promise<ClaimResponse> {
  const response = await apiFetch(`/api/claims/${jobId}/result`, {
    cache: "no-store",
  });
  return parseResponse<ClaimResponse>(response);
}

export async function getClaimReview(jobId: string): Promise<ClaimReview> {
  const response = await apiFetch(`/api/claims/${jobId}/review`, {
    cache: "no-store",
  });
  return parseResponse<ClaimReview>(response);
}

export async function saveClaimReview(
  jobId: string,
  review: Pick<ClaimReview, "status" | "notes" | "corrected_data" | "result_version" | "acknowledged_findings"> & { expected_version: number },
): Promise<ClaimReview> {
  const response = await apiFetch(`/api/claims/${jobId}/review`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(review)
  });
  return parseResponse<ClaimReview>(response);
}

export async function retryClaimJob(jobId: string): Promise<ClaimJob> {
  const response = await apiFetch(`/api/claims/${jobId}/retry`, {
    method: "POST",
  });
  return parseResponse<ClaimJob>(response);
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
  throw new ApiError(message, response.status);
}

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
