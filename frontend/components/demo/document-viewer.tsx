import { useEffect, useRef } from "react";
import { demoSample } from "@/lib/demo-sample";

export function DocumentViewer({ page, onPageChange }: { page: number; onPageChange: (page: number) => void }) {
  const viewport = useRef<HTMLDivElement>(null);
  const current = demoSample.pages.find((item) => item.number === page) ?? demoSample.pages[0];

  useEffect(() => { viewport.current?.scrollTo({ top: 0, left: 0 }); }, [page]);

  return (
    <div className="overflow-hidden rounded-md border border-zinc-200 bg-zinc-50">
      <div className="flex min-h-10 items-center gap-2 border-b border-zinc-200 px-3 text-xs text-zinc-600">
        <label htmlFor="demo-page">Page</label>
        <select id="demo-page" value={page} onChange={(event) => onPageChange(Number(event.target.value))} className="min-h-8 rounded border border-transparent bg-transparent px-1 text-zinc-900 hover:border-zinc-300">
          {demoSample.pages.map((item) => <option key={item.number} value={item.number}>{item.number}</option>)}
        </select>
        <span>of {demoSample.pages.length}</span>
        <span className="ml-auto text-zinc-500">{current.title}</span>
      </div>
      <div ref={viewport} tabIndex={0} role="region" aria-label={`${current.title} PDF preview, page ${page}`} className="h-[340px] overflow-auto bg-zinc-100 p-3 sm:h-[410px] sm:p-4 xl:h-[440px]">
        {/* A native image keeps the bundled PDF preview usable without a PDF browser plugin. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={current.preview} alt={`${current.title}, page ${page} of 3. Fictional sample claim.`} width={952} height={1348} className="mx-auto block h-auto w-full border border-zinc-200 bg-white shadow-sm" />
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
