import { ArrowUpRight } from "lucide-react";

export function SourceLink({ page, section, onSource }: { page: number; section: string; onSource: (page: number) => void }) {
  return (
    <button type="button" aria-label={`View source page ${page} for ${section}`} aria-controls="demo-document-preview" onClick={() => onSource(page)} className="inline-flex min-h-8 shrink-0 items-center gap-1 rounded px-1 text-xs font-medium text-blue-700 hover:bg-blue-50">
      Page {page} <ArrowUpRight aria-hidden="true" className="h-3.5 w-3.5" />
    </button>
  );
}
