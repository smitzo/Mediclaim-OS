"use client";

import { useDemo } from "@/lib/use-demo";
import { DemoFrame } from "./frame";
import { DocumentPanel } from "./document-panel";
import { Info } from "lucide-react";
import { DemoProgress } from "./progress";
import { DocumentViewer } from "./document-viewer";
import { useState } from "react";
import { ResultsPanel } from "./results-panel";

export function DemoWorkspace() {
  const demo = useDemo();
  const [page, setPage] = useState(1);
  function reset() { demo.reset(); setPage(1); }
  return (
    <DemoFrame onReset={reset}>
      <div className="mb-5 flex items-center gap-2 rounded-md border border-blue-100 bg-blue-50 px-3.5 py-2.5 text-xs font-medium text-blue-700 sm:text-sm">
        <Info aria-hidden="true" className="h-4 w-4 shrink-0" /> Interactive demo · Synthetic sample data
      </div>
      <DemoProgress selected={demo.selected} status={demo.status} result={demo.result} />
      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <DocumentPanel selected={demo.selected} status={demo.status} onSelect={demo.select} onRun={demo.run}>
          <DocumentViewer key={demo.revision} page={page} onPageChange={setPage} />
        </DocumentPanel>
        <ResultsPanel result={demo.result} status={demo.status} selected={demo.selected} error={demo.error} />
      </div>
    </DemoFrame>
  );
}
