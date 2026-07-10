"use client";
import { useState } from "react";
import { ApiError, ClaimResponse, ClaimReview, ReviewStatus, getClaimReview, saveClaimReview } from "@/lib/api";

function fields(value: unknown, path = ""): Array<[string, unknown]> {
  if (Array.isArray(value)) return value.flatMap((item, index) => fields(item, `${path}.${index}`));
  if (value && typeof value === "object") return Object.entries(value).filter(([key]) => key !== "extra_fields").flatMap(([key, item]) => fields(item, path ? `${path}.${key}` : key));
  return [[path, value]];
}
function merged(result: ClaimResponse, review: ClaimReview) {
  const data = structuredClone(result.extracted_data);
  for (const [section, changes] of Object.entries(review.corrected_data)) data[section] = { ...(data[section] as object || {}), ...(changes as object) };
  return data;
}

export function ClaimReviewPanel({ jobId, result, review, canReview, onSaved }: { jobId: string; result: ClaimResponse; review: ClaimReview; canReview: boolean; onSaved: (review: ClaimReview) => void }) {
  const [draft, setDraft] = useState(() => merged(result, review));
  const [current, setCurrent] = useState(review);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const findings = current.validation_findings?.length ? current.validation_findings : result.validation_findings || [];
  const api = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  function change(path: string, value: string) {
    setDraft((previous) => {
      const next = structuredClone(previous);
      const parts = path.split(".");
      let cursor: Record<string, unknown> = next;
      for (const part of parts.slice(0, -1)) cursor = cursor[part] as Record<string, unknown>;
      cursor[parts[parts.length - 1]] = value || null;
      return next;
    });
  }
  async function save() {
    setSaving(true); setError("");
    try {
      const corrections = Object.fromEntries(Object.entries(draft).filter(([section, value]) => JSON.stringify(value) !== JSON.stringify(result.extracted_data[section])));
      const saved = await saveClaimReview(jobId, { status: current.status, notes: current.notes, corrected_data: corrections, expected_version: current.version, result_version: current.result_version, acknowledged_findings: current.acknowledged_findings });
      setCurrent(saved); onSaved(saved); setConflict(false);
    } catch (exc) { setError(exc instanceof Error ? exc.message : "Review could not be saved."); setConflict(exc instanceof ApiError && exc.status === 409); }
    finally { setSaving(false); }
  }
  async function reload() {
    try { const saved = await getClaimReview(jobId); setCurrent(saved); setDraft(merged(result, saved)); onSaved(saved); setConflict(false); setError(""); }
    catch (exc) { setError(exc instanceof Error ? exc.message : "Unable to reload review."); }
  }
  return <section className="mt-5 rounded-lg border border-zinc-200 p-4">
    <h3 className="font-semibold">Review with source evidence</h3>
    <p className="mt-1 text-sm text-zinc-500">Extraction version {current.result_version} · Review version {current.version} · Evidence remains unscored.</p>
    <div className="mt-4 grid gap-4 lg:grid-cols-2">
      <div><iframe title="Authorized claim PDF" src={`${api}/api/claims/${encodeURIComponent(jobId)}/document#page=${page}`} className="h-[560px] w-full rounded border" />
        {selected && <p className="mt-2 whitespace-pre-wrap text-xs text-zinc-600">{result.field_evidence?.[selected]?.supporting_text || "No literal source evidence is available."}</p>}
      </div>
      <div className="max-h-[600px] space-y-3 overflow-auto">
        {fields(draft).map(([path, value]) => <label key={path} className="block text-xs text-zinc-600">
          <span className="flex items-center justify-between gap-2"><span>{path}</span><button type="button" className="text-blue-700 underline" onClick={() => { setSelected(path); setPage(result.field_evidence?.[path]?.source_page || 1); }}>Source {result.field_evidence?.[path]?.source_page || "unavailable"}</button></span>
          <input disabled={!canReview} value={value === null ? "" : String(value)} onChange={(event) => change(path, event.target.value)} className="mt-1 w-full rounded border border-zinc-300 px-2 py-1.5 text-sm text-zinc-900 disabled:bg-zinc-50" />
        </label>)}
      </div>
    </div>
    <div className="mt-4 space-y-2" aria-label="Validation findings">{findings.map((finding) => <label key={finding.id} className="flex gap-2 rounded border border-amber-200 bg-amber-50 p-2 text-sm">
      <input type="checkbox" disabled={!canReview} checked={current.acknowledged_findings.includes(finding.id)} onChange={(event) => setCurrent({ ...current, acknowledged_findings: event.target.checked ? [...current.acknowledged_findings, finding.id] : current.acknowledged_findings.filter((id) => id !== finding.id) })} />
      <span>{finding.message} <span className="text-xs text-zinc-500">{finding.fields.join(", ")}</span></span>
    </label>)}</div>
    <div className="mt-4 flex flex-wrap gap-3">
      <label className="text-sm">Decision<select disabled={!canReview} className="ml-2 rounded border p-2" value={current.status} onChange={(event) => setCurrent({ ...current, status: event.target.value as ReviewStatus })}>{["needs_review", "corrected", "approved", "rejected"].map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></label>
      <label className="flex-1 text-sm">Notes<input disabled={!canReview} value={current.notes} onChange={(event) => setCurrent({ ...current, notes: event.target.value })} className="ml-2 w-full rounded border p-2" /></label>
      <button disabled={!canReview || saving || conflict} onClick={save} className="rounded bg-blue-700 px-4 py-2 text-sm text-white disabled:bg-zinc-300">{saving ? "Saving…" : "Save review"}</button>
    </div>
    {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
    {conflict && <div className="mt-3 text-sm"><p>Your draft is preserved below. Copy needed changes before loading the saved review.</p><details><summary>Unsaved draft</summary><pre className="max-h-40 overflow-auto text-xs">{JSON.stringify(draft, null, 2)}</pre></details><button onClick={reload} className="mt-2 rounded border px-3 py-2">Reload saved review</button></div>}
  </section>;
}
