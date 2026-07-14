import Link from "next/link";
import { ArrowUpRight, Download, FileText, RotateCcw } from "lucide-react";
import type { ReactNode } from "react";
import { demoSample } from "@/lib/demo-sample";

export function DemoFrame({ children, onReset }: { children: ReactNode; onReset: () => void }) {
  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-950">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-[1504px] flex-wrap items-center justify-between gap-3 px-5 py-4 sm:px-8">
          <Link href="/" className="inline-flex items-center gap-2.5 font-semibold tracking-tight">
            <FileText aria-hidden="true" className="h-7 w-7 text-blue-600" />
            <span className="text-lg">ClaimOps</span>
          </Link>
          <nav aria-label="Workspace" className="flex flex-wrap items-center gap-3 text-xs sm:gap-5 sm:text-sm">
            <span className="rounded-md bg-blue-50 px-2.5 py-1.5 font-medium text-blue-700">Demo workspace</span>
            <button onClick={onReset} className="inline-flex min-h-9 items-center gap-1.5 font-medium text-zinc-600 hover:text-blue-700">
              <RotateCcw aria-hidden="true" className="h-3.5 w-3.5" /> Reset demo
            </button>
            <Link href="/workspace" className="inline-flex min-h-9 items-center gap-1 font-medium text-blue-700 hover:underline">
              Company workspace <ArrowUpRight aria-hidden="true" className="h-3.5 w-3.5" />
            </Link>
          </nav>
        </div>
      </header>
      <main id="main-content" className="mx-auto max-w-[1504px] px-5 py-6 sm:px-8 sm:py-8">
        <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="mb-2 text-xs text-zinc-500">Workspace <span aria-hidden="true" className="px-1.5">/</span> Demo</p>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Document Processor</h1>
            <p className="mt-2 text-sm leading-6 text-zinc-600">Try the sample PDF and explore its structured claim data.</p>
          </div>
          <a href={demoSample.pdfHref} download={demoSample.filename} className="inline-flex min-h-10 shrink-0 items-center justify-center gap-2 self-start rounded-md border border-zinc-300 bg-white px-3.5 text-sm font-medium text-zinc-700 hover:border-blue-300 hover:text-blue-700">
            <Download aria-hidden="true" className="h-4 w-4" /> Download sample PDF
          </a>
        </div>
        {children}
      </main>
      <footer className="mx-auto flex max-w-[1504px] flex-wrap justify-between gap-2 px-5 pb-6 text-xs leading-5 text-zinc-500 sm:px-8">
        <p>ClaimOps · Document processing, made readable.</p>
        <p>Demo preview · Fictional claim · Prepared sample results</p>
      </footer>
    </div>
  );
}
