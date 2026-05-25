"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  CircleX,
  Clock3,
  Database,
  Download,
  FileArchive,
  FileText,
  Loader2,
  LogIn,
  LogOut,
  PlayCircle,
  RefreshCw,
  UploadCloud
} from "lucide-react";
import { ClaimJob, ClaimResponse, JobStatus, getClaimResult, listJobs, submitClaims } from "@/lib/api";
import { AuthSession, loadSession, registerCompany, signInCompany, signOutCompany } from "@/lib/auth";
import { getDemoJobs, getDemoResult, getDemoSummary, getProcessedDemoJobs, getProcessingDemoJobs, isDemoJob } from "@/lib/demo-data";

const statusStyles: Record<string, string> = {
  queued: "bg-slate-100 text-slate-700 ring-slate-200",
  processing: "bg-blue-50 text-blue-700 ring-blue-200",
  succeeded: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  partial: "bg-amber-50 text-amber-700 ring-amber-200",
  failed: "bg-rose-50 text-rose-700 ring-rose-200"
};

const statusLabels: Record<string, string> = {
  queued: "Queued",
  processing: "Processing",
  succeeded: "Succeeded",
  partial: "Partial",
  failed: "Failed"
};

type JobFilter = "all" | JobStatus;
type ResultView = "summary" | "json";
type AuthMode = "signin" | "register";

const jobFilters: JobFilter[] = ["all", "queued", "processing", "succeeded", "partial", "failed"];

export default function Home() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>("signin");
  const [companyName, setCompanyName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [jobs, setJobs] = useState<ClaimJob[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [jobFilter, setJobFilter] = useState<JobFilter>("all");
  const [selectedJob, setSelectedJob] = useState<ClaimJob | null>(null);
  const [result, setResult] = useState<ClaimResponse | null>(null);
  const [resultView, setResultView] = useState<ResultView>("summary");
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [resultLoading, setResultLoading] = useState(false);
  const [processingDemo, setProcessingDemo] = useState(false);
  const [demoLoaded, setDemoLoaded] = useState(false);
  const [demoProcessed, setDemoProcessed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  const stats = useMemo(() => {
    return {
      total: jobs.length,
      active: jobs.filter((job) => job.status === "queued" || job.status === "processing").length,
      completed: jobs.filter((job) => job.status === "succeeded" || job.status === "partial").length,
      failed: jobs.filter((job) => job.status === "failed").length
    };
  }, [jobs]);

  const demoSummary = useMemo(() => {
    if (!demoLoaded) {
      return "Live API";
    }
    const summary = getDemoSummary();
    if (demoProcessed) {
      return `${summary.claims} demo claims processed`;
    }
    return `${summary.claims} demo claims, ${summary.pages} pages`;
  }, [demoLoaded, demoProcessed]);

  const filteredJobs = useMemo(() => {
    if (jobFilter === "all") {
      return jobs;
    }
    return jobs.filter((job) => job.status === jobFilter);
  }, [jobFilter, jobs]);

  const refreshJobs = useCallback(async () => {
    if (!session) {
      return;
    }
    setLoadingJobs(true);
    setError(null);
    try {
      const nextJobs = await listJobs(session.tenantId);
      setJobs(nextJobs);
      setDemoLoaded(false);
      setDemoProcessed(false);
      setResult(null);
      setResultView("summary");
      setJobFilter("all");
      setSelectedJob((current) => current ? nextJobs.find((job) => job.job_id === current.job_id) ?? null : current);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Unable to load jobs");
    } finally {
      setLoadingJobs(false);
    }
  }, [session]);

  function submitAuthForm() {
    const result = authMode === "register"
      ? registerCompany(companyName, username, password)
      : signInCompany(username, password);
    if (!result.ok) {
      setAuthError(result.message);
      return;
    }
    setSession(result.session);
    setAuthError(null);
    setPassword("");
  }

  function signOut() {
    signOutCompany();
    setSession(null);
    setJobs([]);
    setFiles([]);
    setSelectedJob(null);
    setResult(null);
    setDemoLoaded(false);
    setDemoProcessed(false);
  }

  function loadDemoData() {
    const nextJobs = getDemoJobs(session?.tenantId);
    setJobs(nextJobs);
    setFiles([]);
    setResult(null);
    setResultView("summary");
    setSelectedJob(nextJobs[0] ?? null);
    setJobFilter("all");
    setDemoLoaded(true);
    setDemoProcessed(false);
    setError(null);
  }

  async function processDemoData() {
    setProcessingDemo(true);
    setError(null);
    setResult(null);
    setResultView("summary");
    setJobs(getProcessingDemoJobs(session?.tenantId));
    await new Promise((resolve) => window.setTimeout(resolve, 650));
    const nextJobs = getProcessedDemoJobs(session?.tenantId);
    const nextSelectedJob = nextJobs[0] ?? null;
    setJobs(nextJobs);
    setSelectedJob(nextSelectedJob);
    setDemoLoaded(true);
    setDemoProcessed(true);
    setResult(nextSelectedJob ? getDemoResult(nextSelectedJob.job_id, session?.tenantId) : null);
    setResultView("summary");
    setProcessingDemo(false);
  }

  function clearDemoData() {
    setJobs((current) => current.filter((job) => !isDemoJob(job.job_id)));
    setSelectedJob(null);
    setResult(null);
    setResultView("summary");
    setDemoLoaded(false);
    setDemoProcessed(false);
    setJobFilter("all");
    setError(null);
  }

  async function uploadSelectedFiles() {
    if (!files.length) {
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const response = await submitClaims(files, session?.tenantId);
      setFiles([]);
      setJobs((current) => [...response.jobs, ...current.filter((job) => !isDemoJob(job.job_id))]);
      setDemoLoaded(false);
      setDemoProcessed(false);
      setJobFilter("all");
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
    setResultView("summary");
    if (isDemoJob(job.job_id)) {
      const demoResult = getDemoResult(job.job_id, session?.tenantId);
      if (demoResult && (job.status === "succeeded" || job.status === "partial")) {
        setResult(demoResult);
      }
      return;
    }
    if (job.status !== "succeeded" && job.status !== "partial") {
      return;
    }
    setResultLoading(true);
    setError(null);
    try {
      setResult(await getClaimResult(job.job_id, session?.tenantId));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Unable to load result");
    } finally {
      setResultLoading(false);
    }
  }

  function downloadResult() {
    if (!result || !selectedJob) {
      return;
    }
    const payload = JSON.stringify(result, null, 2);
    const blob = new Blob([payload], { type: "application/json" });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${selectedJob.claim_id}-result.json`;
    anchor.click();
    window.URL.revokeObjectURL(url);
  }

  useEffect(() => {
    setSession(loadSession());
  }, []);

  useEffect(() => {
    if (session) {
      refreshJobs();
    }
  }, [refreshJobs, session]);

  useEffect(() => {
    if (demoLoaded) {
      return;
    }
    const interval = window.setInterval(() => {
      if (jobs.some((job) => job.status === "queued" || job.status === "processing")) {
        refreshJobs();
      }
    }, 4000);
    return () => window.clearInterval(interval);
  }, [demoLoaded, jobs, refreshJobs]);

  if (!session) {
    return (
      <AuthScreen
        authMode={authMode}
        authError={authError}
        companyName={companyName}
        username={username}
        password={password}
        onAuthModeChange={setAuthMode}
        onCompanyNameChange={setCompanyName}
        onUsernameChange={setUsername}
        onPasswordChange={setPassword}
        onSubmit={submitAuthForm}
      />
    );
  }

  return (
    <main className="min-h-screen bg-zinc-50 text-zinc-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-7 px-5 py-8 lg:px-8">
        <header className="border-b border-zinc-200 pb-6">
          <div className="max-w-3xl">
            <p className="text-sm font-medium text-blue-700">ClaimOps</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal text-zinc-950">Document Processor</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-600">
              Upload claim PDFs in batches, let the distributed worker process them, and inspect structured extraction results as jobs finish.
            </p>
          </div>
        </header>

        <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 font-semibold text-blue-700">
                <Building2 className="h-3.5 w-3.5" />
                {session.companyName}
              </span>
              <span className="rounded-full bg-zinc-100 px-2.5 py-1 font-medium">{session.tenantId}</span>
              <span className="rounded-full bg-zinc-100 px-2.5 py-1 font-medium">{demoSummary}</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={loadDemoData}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-zinc-300 bg-white px-4 text-sm font-medium text-zinc-800 shadow-sm hover:bg-zinc-100"
              >
                <Database className="h-4 w-4" />
                Load demo data
              </button>
              <button
                onClick={processDemoData}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-zinc-300"
                disabled={processingDemo}
              >
                {processingDemo ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlayCircle className="h-4 w-4" />}
                Process demo data
              </button>
              {demoLoaded ? (
                <button
                  onClick={clearDemoData}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-zinc-300 bg-white px-4 text-sm font-medium text-zinc-800 shadow-sm hover:bg-zinc-100"
                >
                  <CircleX className="h-4 w-4" />
                  Clear demo
                </button>
              ) : null}
              <button
                onClick={refreshJobs}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-zinc-300 bg-white px-4 text-sm font-medium text-zinc-800 shadow-sm hover:bg-zinc-100"
                disabled={loadingJobs}
              >
                <RefreshCw className={`h-4 w-4 ${loadingJobs ? "animate-spin" : ""}`} />
                Refresh
              </button>
              <button
                onClick={signOut}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-zinc-300 bg-white px-4 text-sm font-medium text-zinc-800 shadow-sm hover:bg-zinc-100"
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          </div>
        </section>

        {error ? (
          <div className="flex items-start gap-3 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Recent jobs" value={stats.total} icon={<FileArchive className="h-5 w-5" />} />
          <MetricCard label="Active queue" value={stats.active} icon={<Clock3 className="h-5 w-5" />} />
          <MetricCard label="Completed" value={stats.completed} icon={<CheckCircle2 className="h-5 w-5" />} />
          <MetricCard label="Failed" value={stats.failed} icon={<AlertCircle className="h-5 w-5" />} />
        </section>

        <section className="grid gap-7 xl:grid-cols-[340px_minmax(0,1fr)]">
          <div className="rounded-lg border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-blue-50 text-blue-700">
                <UploadCloud className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-zinc-950">Batch upload</h2>
                <p className="text-sm text-zinc-500">PDF files are queued as separate claim jobs.</p>
              </div>
            </div>

            <label className="mt-6 flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-zinc-300 bg-zinc-50 px-4 py-7 text-center hover:border-blue-400 hover:bg-blue-50">
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

            <div className="mt-5 max-h-44 space-y-2 overflow-auto">
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
              className="mt-6 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-blue-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-zinc-300"
            >
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
              Queue {files.length || ""} file{files.length === 1 ? "" : "s"}
            </button>
          </div>

          <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm">
            <div className="border-b border-zinc-200 px-6 py-5">
              <div>
                <h2 className="text-base font-semibold text-zinc-950">Recent claim jobs</h2>
                <p className="text-sm text-zinc-500">Jobs poll automatically while active.</p>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {jobFilters.map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setJobFilter(filter)}
                    className={`h-8 rounded-md border px-3 text-xs font-semibold ${
                      jobFilter === filter
                        ? "border-blue-700 bg-blue-700 text-white"
                        : "border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-100"
                    }`}
                  >
                    {filter === "all" ? "All" : statusLabels[filter]}
                  </button>
                  ))}
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
                  {filteredJobs.map((job) => (
                    <tr key={job.job_id} className={selectedJob?.job_id === job.job_id ? "bg-blue-50/60" : "hover:bg-zinc-50"}>
                      <td className="px-5 py-3 font-medium text-zinc-950">{job.claim_id}</td>
                      <td className="max-w-64 truncate px-5 py-3 text-zinc-600">{job.filename}</td>
                      <td className="px-5 py-3 text-zinc-600">{job.page_count}</td>
                      <td className="px-5 py-3">
                        <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${statusStyles[job.status]}`}>
                          {statusLabels[job.status] ?? job.status}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-zinc-600">{formatDate(job.updated_at)}</td>
                      <td className="px-5 py-3">
                        <button
                          onClick={() => inspectJob(job)}
                          className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-800 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={job.status === "queued" || job.status === "processing"}
                        >
                          <FileText className="h-4 w-4" />
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!filteredJobs.length ? (
                    <tr>
                      <td colSpan={6} className="px-5 py-16 text-center text-sm text-zinc-500">
                        <div className="mx-auto flex max-w-sm flex-col items-center gap-2">
                          <FileText className="h-7 w-7 text-zinc-300" />
                          <span>No jobs match this view.</span>
                        </div>
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
                {selectedJob ? `${selectedJob.claim_id} - ${statusLabels[selectedJob.status] ?? selectedJob.status}` : "Select a completed or partial job to view extracted JSON."}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {result ? (
                <>
                  <button
                    onClick={downloadResult}
                    className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-800 hover:bg-zinc-100"
                  >
                    <Download className="h-4 w-4" />
                    Export JSON
                  </button>
                  <div className="flex rounded-md border border-zinc-300 bg-white p-1">
                    {(["summary", "json"] as ResultView[]).map((view) => (
                      <button
                        key={view}
                        onClick={() => setResultView(view)}
                        className={`h-8 rounded px-3 text-xs font-semibold capitalize ${
                          resultView === view ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-100"
                        }`}
                      >
                        {view}
                      </button>
                    ))}
                  </div>
                </>
              ) : null}
              {resultLoading ? <Loader2 className="h-5 w-5 animate-spin text-blue-700" /> : null}
            </div>
          </div>

          {result && resultView === "summary" ? <ResultSummary result={result} /> : null}

          {resultView === "json" || !result ? (
            <pre className="mt-4 max-h-[520px] overflow-auto rounded-md bg-zinc-950 p-4 text-xs leading-6 text-zinc-100">
              {result ? JSON.stringify(result, null, 2) : selectedJob?.error ?? "No result selected."}
            </pre>
          ) : null}
        </section>
      </div>
    </main>
  );
}

function AuthScreen({
  authMode,
  authError,
  companyName,
  username,
  password,
  onAuthModeChange,
  onCompanyNameChange,
  onUsernameChange,
  onPasswordChange,
  onSubmit
}: {
  authMode: AuthMode;
  authError: string | null;
  companyName: string;
  username: string;
  password: string;
  onAuthModeChange: (mode: AuthMode) => void;
  onCompanyNameChange: (value: string) => void;
  onUsernameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-5 py-8 text-zinc-950">
      <section className="w-full max-w-md rounded-lg border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-md bg-blue-50 text-blue-700">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-medium text-blue-700">ClaimOps</p>
            <h1 className="text-xl font-semibold tracking-normal">Company access</h1>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-2 rounded-md bg-zinc-100 p-1">
          {(["signin", "register"] as AuthMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => onAuthModeChange(mode)}
              className={`h-9 rounded text-sm font-semibold capitalize ${
                authMode === mode ? "bg-white text-zinc-950 shadow-sm" : "text-zinc-600 hover:text-zinc-950"
              }`}
            >
              {mode === "signin" ? "Sign in" : "Register"}
            </button>
          ))}
        </div>

        <form
          className="mt-5 space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit();
          }}
        >
          {authMode === "register" ? (
            <label className="block text-sm font-medium text-zinc-700">
              Company name
              <input
                value={companyName}
                onChange={(event) => onCompanyNameChange(event.target.value)}
                className="mt-1 h-11 w-full rounded-md border border-zinc-300 px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                placeholder="Northstar Claims Pvt Ltd"
              />
            </label>
          ) : null}

          <label className="block text-sm font-medium text-zinc-700">
            Username
            <input
              value={username}
              onChange={(event) => onUsernameChange(event.target.value)}
              className="mt-1 h-11 w-full rounded-md border border-zinc-300 px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              placeholder="demo"
              autoComplete="username"
            />
          </label>

          <label className="block text-sm font-medium text-zinc-700">
            Password
            <input
              value={password}
              onChange={(event) => onPasswordChange(event.target.value)}
              className="mt-1 h-11 w-full rounded-md border border-zinc-300 px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              placeholder="demo"
              type="password"
              autoComplete={authMode === "register" ? "new-password" : "current-password"}
            />
          </label>

          {authError ? (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{authError}</span>
            </div>
          ) : null}

          <button className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-blue-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-blue-800">
            <LogIn className="h-4 w-4" />
            {authMode === "signin" ? "Sign in" : "Register company"}
          </button>
        </form>

        <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          Use username <span className="font-semibold">demo</span> and password <span className="font-semibold">demo</span> to enter the demo tenant immediately.
        </div>
      </section>
    </main>
  );
}

function MetricCard({ label, value, icon }: { label: string; value: number; icon: ReactNode }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-500">{label}</span>
        <span className="rounded-md bg-blue-50 p-2 text-blue-700">{icon}</span>
      </div>
      <div className="mt-4 text-3xl font-semibold text-zinc-950">{value}</div>
    </div>
  );
}

function ResultSummary({ result }: { result: ClaimResponse }) {
  const identity = getRecord(result.extracted_data.identity);
  const discharge = getRecord(result.extracted_data.discharge_summary);
  const bill = getRecord(result.extracted_data.itemized_bill);
  const lineItems = Array.isArray(bill.line_items) ? bill.line_items : [];
  const summary = result.processing_summary;
  const agents = Array.isArray(summary.agents_ran) ? summary.agents_ran.map(String) : [];

  return (
    <div className="mt-5 grid gap-4 lg:grid-cols-3">
      <div className="rounded-lg border border-zinc-200 p-4">
        <h3 className="text-sm font-semibold text-zinc-950">Identity</h3>
        <dl className="mt-3 space-y-2 text-sm">
          <SummaryRow label="Patient" value={getString(identity.patient_name)} />
          <SummaryRow label="Policy" value={getString(identity.policy_number)} />
          <SummaryRow label="Insurer" value={getString(identity.insurance_provider)} />
          <SummaryRow label="Bank" value={getString(identity.bank_name)} />
        </dl>
      </div>
      <div className="rounded-lg border border-zinc-200 p-4">
        <h3 className="text-sm font-semibold text-zinc-950">Clinical</h3>
        <dl className="mt-3 space-y-2 text-sm">
          <SummaryRow label="Hospital" value={getString(discharge.hospital_name)} />
          <SummaryRow label="Diagnosis" value={getString(discharge.final_diagnosis)} />
          <SummaryRow label="Stay" value={getString(discharge.length_of_stay)} />
          <SummaryRow label="Physician" value={getString(discharge.attending_physician)} />
        </dl>
      </div>
      <div className="rounded-lg border border-zinc-200 p-4">
        <h3 className="text-sm font-semibold text-zinc-950">Billing</h3>
        <dl className="mt-3 space-y-2 text-sm">
          <SummaryRow label="Bill no." value={getString(bill.bill_number)} />
          <SummaryRow label="Total" value={formatCurrency(bill.total_amount)} />
          <SummaryRow label="Patient due" value={formatCurrency(bill.patient_responsibility)} />
          <SummaryRow label="Line items" value={String(lineItems.length)} />
        </dl>
      </div>
      <div className="rounded-lg border border-zinc-200 p-4 lg:col-span-3">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-zinc-950">Processing output</h3>
            <p className="mt-1 text-sm text-zinc-500">
              {String(summary.total_pages ?? result.page_classification.length)} pages, {result.page_classification.length} classifications, {result.errors.length} errors
            </p>
          </div>
          <div className="flex flex-wrap gap-2 md:justify-end">
            {agents.map((agent) => (
              <span key={agent} className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                {agent.replaceAll("_", " ")}
              </span>
            ))}
            {result.page_classification.map((page) => (
              <span key={`${page.page_number}-${page.document_type}`} className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-700">
                p{String(page.page_number)} {String(page.document_type).replaceAll("_", " ")}
              </span>
            ))}
          </div>
        </div>
        {result.errors.length ? (
          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {result.errors.join(" ")}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="shrink-0 text-zinc-500">{label}</dt>
      <dd className="text-right font-medium text-zinc-900">{value || "-"}</dd>
    </div>
  );
}

function getRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function getString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function formatCurrency(value: unknown): string {
  if (typeof value !== "number") {
    return "";
  }
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(value);
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
