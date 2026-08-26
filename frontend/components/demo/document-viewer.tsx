import { useEffect, useRef, useState } from "react";
import { ExternalLink, Minus, Plus } from "lucide-react";
import { demoSample } from "@/lib/demo-sample";

export function DocumentViewer({ page, onPageChange }: { page: number; onPageChange: (page: number) => void }) {
  const viewport = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(100);
  const current = demoSample.pages.find((item) => item.number === page) ?? demoSample.pages[0];

  useEffect(() => { viewport.current?.scrollTo({ top: 0, left: 0 }); }, [page]);

  return (
    <div className="overflow-hidden rounded-md border border-zinc-200 bg-zinc-50">
      <div className="flex min-h-11 flex-wrap items-center gap-1.5 border-b border-zinc-200 px-2 py-1 text-xs text-zinc-600 sm:px-3">
        <label htmlFor="demo-page">Page</label>
        <select id="demo-page" value={page} onChange={(event) => onPageChange(Number(event.target.value))} className="min-h-8 rounded border border-transparent bg-transparent px-1 text-zinc-900 hover:border-zinc-300">
          {demoSample.pages.map((item) => <option key={item.number} value={item.number}>{item.number}</option>)}
        </select>
        <span>of {demoSample.pages.length}</span>
        <div role="group" aria-label="PDF zoom controls" className="ml-auto flex items-center gap-0.5">
          <button type="button" aria-label="Zoom out" disabled={zoom <= 50} onClick={() => setZoom((value) => Math.max(50, value - 25))} className="inline-flex h-8 w-8 items-center justify-center rounded hover:bg-zinc-200 disabled:opacity-30"><Minus aria-hidden="true" className="h-3.5 w-3.5" /></button>
          <button type="button" aria-label="Reset zoom" onClick={() => setZoom(100)} className="min-h-8 min-w-10 rounded px-1 tabular-nums hover:bg-zinc-200">{zoom}%</button>
          <button type="button" aria-label="Zoom in" disabled={zoom >= 150} onClick={() => setZoom((value) => Math.min(150, value + 25))} className="inline-flex h-8 w-8 items-center justify-center rounded hover:bg-zinc-200 disabled:opacity-30"><Plus aria-hidden="true" className="h-3.5 w-3.5" /></button>
          <a aria-label={`Open PDF at page ${page} in a new tab`} href={`${demoSample.pdfHref}#page=${page}`} target="_blank" rel="noopener noreferrer" className="ml-1 inline-flex h-8 w-8 items-center justify-center rounded border-l border-zinc-200 hover:bg-zinc-200"><ExternalLink aria-hidden="true" className="h-3.5 w-3.5" /></a>
        </div>
      </div>
      <div id="demo-document-preview" ref={viewport} tabIndex={0} role="region" aria-label={`${current.title} PDF preview, page ${page}`} className="h-[340px] overflow-auto bg-zinc-100 p-3 sm:h-[410px] sm:p-4 xl:h-[440px]">
        {/* A native image keeps the bundled PDF preview usable without a PDF browser plugin. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={current.preview} alt={`${current.title}, page ${page} of 3. Fictional sample claim.`} width={952} height={1348} style={{ width: `${zoom}%` }} className="mx-auto block h-auto max-w-none border border-zinc-200 bg-white shadow-sm" />
      </div>
      <div aria-label="Document pages" className="grid grid-cols-3 gap-3 border-t border-zinc-200 bg-zinc-50 p-3">
        {demoSample.pages.map((item) => (
          <button key={item.number} type="button" aria-label={`View page ${item.number}: ${item.title}`} aria-pressed={page === item.number} onClick={() => onPageChange(item.number)} className="group min-w-0 text-center">
            <span className={`block overflow-hidden rounded border-2 bg-white p-1 transition-colors ${page === item.number ? "border-blue-500" : "border-zinc-200 group-hover:border-blue-300"}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={item.preview} alt="" width={952} height={1348} loading="lazy" className="h-16 w-full object-cover object-top" />
            </span>
            <span className={`mt-1.5 block text-[11px] sm:text-xs ${page === item.number ? "font-medium text-blue-700" : "text-zinc-600"}`}>{item.title}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
