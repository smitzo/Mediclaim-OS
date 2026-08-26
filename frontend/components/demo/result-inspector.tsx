import { useId, useState, type KeyboardEvent } from "react";
import { Download } from "lucide-react";
import type { DemoResult } from "@/lib/demo-sample";
import { downloadDemoResult } from "@/lib/demo-export";
import { ResultSummary } from "./result-summary";
import { BillSummary } from "./bill-summary";

const views = ["Summary", "JSON"] as const;

export function ResultInspector({ result }: { result: DemoResult }) {
  const [view, setView] = useState<(typeof views)[number]>("Summary");
  const id = useId();
  function navigate(event: KeyboardEvent<HTMLButtonElement>) {
    const offset = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!offset && event.key !== "Home" && event.key !== "End") return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? 1 : (views.indexOf(view) + offset + views.length) % views.length;
    setView(views[next]);
    const tabs = event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]');
    tabs?.[next].focus();
  }
  return (
    <>
      <div className="mt-4 flex flex-wrap items-end justify-between gap-3 border-b border-zinc-200">
        <div role="tablist" aria-label="Result view" className="flex gap-1">
          {views.map((item) => <button key={item} type="button" role="tab" id={`${id}-${item}`} aria-selected={view === item} aria-controls={`${id}-panel`} tabIndex={view === item ? 0 : -1} onKeyDown={navigate} onClick={() => setView(item)} className={`min-h-10 border-b-2 px-3 text-xs font-medium ${view === item ? "border-blue-600 text-blue-700" : "border-transparent text-zinc-500 hover:text-zinc-800"}`}>{item}</button>)}
        </div>
        <button type="button" onClick={() => downloadDemoResult(result)} className="mb-2 inline-flex min-h-9 items-center gap-1.5 rounded-md border border-zinc-300 px-2.5 text-xs font-medium text-zinc-700 hover:border-blue-300 hover:text-blue-700"><Download aria-hidden="true" className="h-3.5 w-3.5" /> Export JSON</button>
      </div>
      <div role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-${view}`} tabIndex={0} className="min-w-0 rounded-sm">
        {view === "Summary" ? <><ResultSummary result={result} /><BillSummary result={result} /></> : (
          <pre className="mt-4 max-h-[640px] max-w-full overflow-auto rounded-md bg-zinc-950 p-4 text-xs leading-6 text-zinc-100"><code>{JSON.stringify(result, null, 2)}</code></pre>
        )}
      </div>
    </>
  );
}
