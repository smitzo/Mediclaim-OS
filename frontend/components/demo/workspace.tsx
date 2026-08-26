"use client";

import { useDemo } from "@/lib/use-demo";
import { DemoFrame } from "./frame";
import { DocumentPanel } from "./document-panel";
import { Info } from "lucide-react";
import { DemoProgress } from "./progress";
import { DocumentViewer } from "./document-viewer";
import { useState } from "react";
import { ResultsPanel } from "./results-panel";
import { ResultInspector } from "./result-inspector";

export function DemoWorkspace() {
  const demo = useDemo();
  const [page, setPage] = useState(1);
  function reset() { demo.reset(); setPage(1); }
  function viewSource(number: number) {
    setPage(number);
    const heading = document.getElementById("demo-document-heading");
    heading?.focus({ preventScroll: true });
    if (window.matchMedia("(max-width: 1023px)").matches) heading?.scrollIntoView({ block: "start", behavior: "auto" });
  }
  return (
    <DemoFrame onReset={reset}>
      <p role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {demo.status === "complete" ? "Demo complete. One claim and three pages loaded. Extracted data is ready to review." : demo.status === "loading" ? "Loading the demo PDF and prepared results." : demo.status === "error" ? "The demo could not be loaded. Please try again." : demo.selected ? "Sample selected. Run demo is available." : "Select the sample PDF to start the demo."}
      </p>
      <div className="mb-5 flex items-center gap-2 rounded-md border border-blue-100 bg-blue-50 px-3.5 py-2.5 text-xs font-medium text-blue-700 sm:text-sm">
        <Info aria-hidden="true" className="h-4 w-4 shrink-0" /> Interactive demo · Synthetic sample data
      </div>
      <DemoProgress selected={demo.selected} status={demo.status} result={demo.result} />
      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <DocumentPanel selected={demo.selected} status={demo.status} onSelect={demo.select} onRun={demo.run}>
          <DocumentViewer key={demo.revision} page={page} onPageChange={setPage} />
        </DocumentPanel>
        <ResultsPanel result={demo.result} status={demo.status} selected={demo.selected} error={demo.error}>
          {demo.result ? <ResultInspector result={demo.result} onSource={viewSource} /> : null}
        </ResultsPanel>
      </div>
    </DemoFrame>
  );
}
