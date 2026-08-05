import { AlertCircle, CheckCircle2, FileSearch, Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { demoSample, type DemoResult } from "@/lib/demo-sample";
import type { DemoStatus } from "@/lib/use-demo";

export function ResultsPanel({ result, status, selected, error, children }: {
  result: DemoResult | null; status: DemoStatus; selected: boolean; error: string | null; children?: ReactNode;
}) {
  return (
    <section aria-labelledby="demo-results-heading" aria-busy={status === "loading"} className="min-w-0 rounded-lg border border-zinc-200 bg-white p-4 sm:p-5">
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id="demo-results-heading" className="text-base font-semibold">Extracted data</h2>
          <p className="mt-1 break-words text-xs text-zinc-500">{result ? demoSample.filename : "Results from the included sample will appear here."}</p>
        </div>
        {result ? <span className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700"><CheckCircle2 aria-hidden="true" className="h-3.5 w-3.5" /> Complete</span> : null}
      </header>
      {result ? children : (
        <div className="mt-5 flex min-h-[360px] items-center justify-center rounded-md border border-dashed border-zinc-200 bg-zinc-50/70 px-5 py-10 text-center sm:min-h-[524px]">
          <div className="max-w-xs">
            {status === "loading" ? <Loader2 aria-hidden="true" className="mx-auto h-9 w-9 animate-spin text-blue-600" /> : status === "error" ? <AlertCircle aria-hidden="true" className="mx-auto h-9 w-9 text-amber-600" /> : <FileSearch aria-hidden="true" className="mx-auto h-10 w-10 text-zinc-300" />}
            <p className="mt-4 text-sm font-semibold text-zinc-800">{status === "loading" ? "Loading the sample claim" : status === "error" ? "The demo needs another try" : selected ? "Your sample is ready" : "From PDF to structured data"}</p>
            {status === "error" ? <p role="alert" className="mt-2 text-sm leading-6 text-amber-800">{error} Use “Try demo again” to retry.</p> : <p className="mt-2 text-sm leading-6 text-zinc-500">{status === "loading" ? "Opening the PDF and its prepared sample results…" : selected ? "Choose Run demo to explore patient details, the discharge summary, and the itemized bill." : "Select the included demo PDF, then run the demo to see its matching results."}</p>}
            <p className="mt-5 text-xs leading-5 text-zinc-400">Fictional sample · No live extraction</p>
          </div>
        </div>
      )}
      {result ? <p className="mt-4 border-t border-zinc-100 pt-3 text-[11px] leading-5 text-zinc-500">Prepared results from a fictional sample claim. Completion indicates the sample was loaded, not a claim approval.</p> : null}
    </section>
  );
}
