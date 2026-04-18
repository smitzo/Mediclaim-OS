"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  FileArchive,
  FileText,
  Loader2,
  RefreshCw,
  UploadCloud
} from "lucide-react";
import { ClaimJob, ClaimResponse, getClaimResult, listJobs, submitClaims } from "@/lib/api";

const statusStyles: Record<string, string> = {
  queued: "bg-slate-100 text-slate-700 ring-slate-200",
  processing: "bg-blue-50 text-blue-700 ring-blue-200",
  succeeded: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  partial: "bg-amber-50 text-amber-700 ring-amber-200",
  failed: "bg-rose-50 text-rose-700 ring-rose-200"
};

export default function Home() {
  const [jobs, setJobs] = useState<ClaimJob[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [selectedJob, setSelectedJob] = useState<ClaimJob | null>(null);
  const [result, setResult] = useState<ClaimResponse | null>(null);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [resultLoading, setResultLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stats = useMemo(() => {
    return {
      total: jobs.length,
      active: jobs.filter((job) => job.status === "queued" || job.status === "processing").length,
      completed: jobs.filter((job) => job.status === "succeeded" || job.status === "partial").length,
      failed: jobs.filter((job) => job.status === "failed").length
    };
  }, [jobs]);

  const refreshJobs = useCallback(async () => {
    setLoadingJobs(true);
    setError(null);
    try {
      const nextJobs = await listJobs();
      setJobs(nextJobs);
      setSelectedJob((current) => current ? nextJobs.find((job) => job.job_id === current.job_id) ?? current : current);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Unable to load jobs");
    } finally {
      setLoadingJobs(false);
    }
  }, []);

  async function uploadSelectedFiles() {
    if (!files.length) {
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const response = await submitClaims(files);
      setFiles([]);
      setJobs((current) => [...response.jobs, ...current]);
      if (response.rejected.length) {
        setError(`${response.rejected.length} file(s) were rejected. Check PDF type, size, or page limits.`);
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function inspectJob(job: ClaimJob) {
    setSelectedJob(job);
    setResult(null);
    if (job.status !== "succeeded" && job.status !== "partial") {
      return;
    }
    setResultLoading(true);
    setError(null);
    try {
      setResult(await getClaimResult(job.job_id));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Unable to load result");
    } finally {
      setResultLoading(false);
    }
  }

  useEffect(() => {
    refreshJobs();
  }, [refreshJobs]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      if (jobs.some((job) => job.status === "queued" || job.status === "processing")) {
        refreshJobs();
      }
    }, 4000);
    return () => window.clearInterval(interval);
  }, [jobs, refreshJobs]);

  return (
    <main className="min-h-screen bg-zinc-50 text-zinc-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 lg:px-8">
        <header className="flex flex-col gap-4 border-b border-zinc-200 pb-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-medium text-blue-700">ClaimOps</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal text-zinc-950">Document Processor</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-600">
              Upload claim PDFs in batches, let the distributed worker process them, and inspect structured extraction results as jobs finish.
            </p>
          </div>
          <button
            onClick={refreshJobs}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-zinc-300 bg-white px-4 text-sm font-medium text-zinc-800 shadow-sm hover:bg-zinc-100 disabled:opacity-60"
            disabled={loadingJobs}
          >
            <RefreshCw className={`h-4 w-4 ${loadingJobs ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </header>

        {error ? (
          <div className="flex items-start gap-3 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        <section className="grid gap-4 md:grid-cols-4">
          <MetricCard label="Recent jobs" value={stats.total} icon={<FileArchive className="h-5 w-5" />} />
          <MetricCard label="Active queue" value={stats.active} icon={<Clock3 className="h-5 w-5" />} />
          <MetricCard label="Completed" value={stats.completed} icon={<CheckCircle2 className="h-5 w-5" />} />
          <MetricCard label="Failed" value={stats.failed} icon={<AlertCircle className="h-5 w-5" />} />
        </section>

        <section className="grid gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">
          <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-blue-50 text-blue-700">
                <UploadCloud className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-zinc-950">Batch upload</h2>
                <p className="text-sm text-zinc-500">PDF files are queued as separate claim jobs.</p>
              </div>
            </div>

            <label className="mt-5 flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-zinc-300 bg-zinc-50 px-4 py-6 text-center hover:border-blue-400 hover:bg-blue-50">
              <UploadCloud className="h-8 w-8 text-blue-700" />
              <span className="mt-3 text-sm font-medium text-zinc-900">Choose claim PDFs</span>
              <span className="mt-1 text-xs text-zinc-500">Select one file or hundreds.</span>
              <input
                className="sr-only"
                type="file"
                accept="application/pdf"
                multiple
                onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
              />
            </label>

            <div className="mt-4 max-h-44 space-y-2 overflow-auto">
              {files.map((file) => (
                <div key={`${file.name}-${file.size}`} className="flex items-center justify-between rounded-md border border-zinc-200 px-3 py-2 text-sm">
                  <span className="truncate text-zinc-800">{file.name}</span>
                  <span className="ml-3 shrink-0 text-xs text-zinc-500">{formatBytes(file.size)}</span>
                </div>
              ))}
            </div>

            <button
              onClick={uploadSelectedFiles}
              disabled={!files.length || uploading}
              className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-blue-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-zinc-300"
            >
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
              Queue {files.length || ""} file{files.length === 1 ? "" : "s"}
            </button>
          </div>

          <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-zinc-200 px-5 py-4">
              <div>
                <h2 className="text-base font-semibold text-zinc-950">Recent claim jobs</h2>
                <p className="text-sm text-zinc-500">Jobs poll automatically while active.</p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-zinc-50 text-xs uppercase text-zinc-500">
                  <tr>
                    <th className="px-5 py-3 font-semibold">Claim</th>
                    <th className="px-5 py-3 font-semibold">File</th>
                    <th className="px-5 py-3 font-semibold">Pages</th>
                    <th className="px-5 py-3 font-semibold">Status</th>
                    <th className="px-5 py-3 font-semibold">Updated</th>
                    <th className="px-5 py-3 font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {jobs.map((job) => (
                    <tr key={job.job_id} className="hover:bg-zinc-50">
                      <td className="px-5 py-3 font-medium text-zinc-950">{job.claim_id}</td>
                      <td className="max-w-64 truncate px-5 py-3 text-zinc-600">{job.filename}</td>
                      <td className="px-5 py-3 text-zinc-600">{job.page_count}</td>
                      <td className="px-5 py-3">
                        <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${statusStyles[job.status]}`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-zinc-600">{formatDate(job.updated_at)}</td>
                      <td className="px-5 py-3">
                        <button
                          onClick={() => inspectJob(job)}
                          className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-800 hover:bg-zinc-100"
                        >
                          <FileText className="h-4 w-4" />
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!jobs.length ? (
                    <tr>
                      <td colSpan={6} className="px-5 py-10 text-center text-sm text-zinc-500">
                        No jobs yet.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-zinc-950">Result inspector</h2>
              <p className="text-sm text-zinc-500">
                {selectedJob ? `${selectedJob.claim_id} · ${selectedJob.status}` : "Select a completed or partial job to view extracted JSON."}
              </p>
            </div>
            {resultLoading ? <Loader2 className="h-5 w-5 animate-spin text-blue-700" /> : null}
          </div>
          <pre className="mt-4 max-h-[520px] overflow-auto rounded-md bg-zinc-950 p-4 text-xs leading-6 text-zinc-100">
            {result ? JSON.stringify(result, null, 2) : selectedJob?.error ?? "No result selected."}
          </pre>
        </section>
      </div>
    </main>
  );
}

function MetricCard({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-500">{label}</span>
        <span className="text-blue-700">{icon}</span>
      </div>
      <div className="mt-3 text-2xl font-semibold text-zinc-950">{value}</div>
    </div>
  );
}

function formatBytes(bytes: number) {
  if (!bytes) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / Math.pow(1024, exponent)).toFixed(exponent ? 1 : 0)} ${units[exponent]}`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
