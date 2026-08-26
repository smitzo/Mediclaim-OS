import { useEffect, useRef, useState } from "react";
import { ExternalLink, FileText, Minus, Plus } from "lucide-react";
import { demoSample } from "@/lib/demo-sample";

export function DocumentViewer({ page, onPageChange }: { page: number; onPageChange: (page: number) => void }) {
  const viewport = useRef<HTMLDivElement>(null);
  const preview = useRef<HTMLImageElement>(null);
  const [zoom, setZoom] = useState(100);
  const [failed, setFailed] = useState<Record<number, boolean>>({});
  const [retry, setRetry] = useState(0);
  const current = demoSample.pages.find((item) => item.number === page) ?? demoSample.pages[0];

  useEffect(() => { viewport.current?.scrollTo({ top: 0, left: 0 }); }, [page]);
  useEffect(() => {
    // An SSR image may fail before React attaches onError during hydration.
    if (preview.current?.complete && preview.current.naturalWidth === 0) {
      setFailed((value) => ({ ...value, [page]: true }));
    }
  }, [page, retry]);

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
        {failed[page] ? <div className="flex min-h-64 flex-col items-center justify-center gap-3 text-center text-sm text-zinc-600">
          <FileText aria-hidden="true" className="h-9 w-9 text-zinc-400" />
          <p>Page preview unavailable.</p>
          <a href={`${demoSample.pdfHref}#page=${page}`} target="_blank" rel="noopener noreferrer" className="text-blue-700 underline">Open the original PDF</a>
          <button type="button" onClick={() => { setRetry((value) => value + 1); setFailed((value) => ({ ...value, [page]: false })); }} className="min-h-9 rounded border border-zinc-300 bg-white px-3 text-xs">Retry preview</button>
        </div> : <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img ref={preview} src={`${current.preview}${retry ? `?retry=${retry}` : ""}`} alt={`${current.title}, page ${page} of 3. Fictional sample claim.`} onError={() => setFailed((value) => ({ ...value, [page]: true }))} width={952} height={1348} style={{ width: `${zoom}%` }} className="mx-auto block h-auto max-w-none border border-zinc-200 bg-white shadow-sm" />
        </>}
      </div>
      <div aria-label="Document pages" className="grid grid-cols-3 gap-3 border-t border-zinc-200 bg-zinc-50 p-3">
        {demoSample.pages.map((item) => (
          <button key={item.number} type="button" aria-label={`View page ${item.number}: ${item.title}`} aria-pressed={page === item.number} onClick={() => onPageChange(item.number)} className="group min-w-0 text-center">
            <span className={`block overflow-hidden rounded border-2 bg-white p-1 transition-colors ${page === item.number ? "border-blue-500" : "border-zinc-200 group-hover:border-blue-300"}`}>
              {failed[item.number] ? <span className="flex h-16 items-center justify-center"><FileText aria-hidden="true" className="h-7 w-7 text-zinc-300" /></span> : <>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`${item.preview}${retry ? `?retry=${retry}` : ""}`} alt="" onError={() => setFailed((value) => ({ ...value, [item.number]: true }))} width={952} height={1348} loading="lazy" className="h-16 w-full object-cover object-top" />
              </>}
            </span>
            <span className={`mt-1.5 block text-[11px] sm:text-xs ${page === item.number ? "font-medium text-blue-700" : "text-zinc-600"}`}>{item.title}</span>
          </button>
        ))}
      </div>
      <p aria-live="polite" className="sr-only">Previewing {current.title}, page {page} of 3.</p>
    </div>
  );
}
