import { CheckCircle2, Download, FileText, Loader2, PlayCircle } from "lucide-react";
import type { ReactNode } from "react";
import { demoSample } from "@/lib/demo-sample";
import type { DemoStatus } from "@/lib/use-demo";

export function DocumentPanel({ selected, status, onSelect, onRun, children }: {
  selected: boolean; status: DemoStatus; onSelect: () => void; onRun: () => void; children?: ReactNode;
}) {
  const loading = status === "loading";
  return (
    <section aria-labelledby="demo-document-heading" className="min-w-0 rounded-lg border border-zinc-200 bg-white p-4 sm:p-5">
      <div className="mb-4 flex items-center gap-2.5">
        <h2 id="demo-document-heading" className="text-base font-semibold">Demo document</h2>
        <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-600">Included sample</span>
      </div>
      <button
        type="button"
        aria-label={`Select demo PDF: ${demoSample.filename}`}
        aria-pressed={selected}
        onClick={onSelect}
        disabled={loading}
        className={`mb-3 flex min-h-[72px] w-full items-center gap-3 rounded-md border p-3 text-left transition-colors disabled:cursor-wait ${selected ? "border-blue-400 bg-blue-50" : "border-zinc-200 bg-zinc-50 hover:border-blue-300 hover:bg-blue-50/50"}`}
      >
        <FileText aria-hidden="true" className="h-8 w-8 shrink-0 text-red-500" />
        <span className="min-w-0 flex-1">
          <span className="block break-words text-sm font-semibold">{demoSample.filename}</span>
          <span className="mt-1 block text-xs text-zinc-500">3 pages · Synthetic sample</span>
        </span>
        {selected ? <CheckCircle2 aria-hidden="true" className="h-5 w-5 shrink-0 text-blue-600" /> : <span className="shrink-0 text-xs font-medium text-blue-700">Select</span>}
      </button>
      {children}
      <button
        type="button"
        onClick={onRun}
        disabled={!selected || loading}
        className="mt-3 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-zinc-200 disabled:text-zinc-500"
      >
        {loading ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : <PlayCircle aria-hidden="true" className="h-4 w-4" />}
        {loading ? "Loading sample…" : status === "complete" ? "Run demo again" : status === "error" ? "Try demo again" : "Run demo"}
      </button>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs leading-5">
        <p className="text-zinc-500">Uses prepared sample results.</p>
        <a href={demoSample.pdfHref} download={demoSample.filename} className="inline-flex min-h-8 items-center gap-1 font-medium text-blue-700 hover:underline">
          <Download aria-hidden="true" className="h-3.5 w-3.5" /> Download PDF
        </a>
      </div>
    </section>
  );
}
