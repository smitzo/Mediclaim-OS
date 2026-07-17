import { Check, Loader2 } from "lucide-react";
import type { DemoStatus } from "@/lib/use-demo";
import type { DemoResult } from "@/lib/demo-sample";
import { formatInr } from "@/lib/demo-format";

export function DemoProgress({ selected, status, result }: { selected: boolean; status: DemoStatus; result: DemoResult | null }) {
  const current = !selected ? 0 : status === "complete" ? 2 : 1;
  const labels = ["Select PDF", "Run demo", "Explore results"];
  const metrics = [
    ["Claims processed", result ? "1" : "0"],
    ["Pages classified", result ? String(result.page_classification.length) : "—"],
    ["Document types", result ? String(new Set(result.page_classification.map((page) => page.document_type)).size) : "—"],
    ["Claim total", result ? formatInr(result.extracted_data.itemized_bill.total_amount) : "—"],
  ];
  return (
    <>
      <ol aria-label="Demo steps" className="mb-6 flex flex-wrap items-center gap-x-4 gap-y-3 sm:gap-x-7">
        {labels.map((label, index) => (
          <li key={label} aria-current={index === current ? "step" : undefined} className="flex items-center gap-2 text-xs font-medium sm:text-sm">
            <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${index <= current ? "bg-blue-600 text-white" : "bg-zinc-200 text-zinc-500"}`}>
              {index < current ? <Check aria-hidden="true" className="h-3.5 w-3.5" /> : index === 1 && status === "loading" ? <Loader2 aria-hidden="true" className="h-3.5 w-3.5 animate-spin" /> : index + 1}
            </span>
            <span className={index === current ? "text-blue-700" : index < current ? "text-zinc-700" : "text-zinc-500"}>{label}</span>
            {index < 2 ? <span aria-hidden="true" className="ml-2 hidden h-px w-8 bg-zinc-300 sm:block" /> : null}
          </li>
        ))}
      </ol>
      <dl aria-label="Demo statistics" className="mb-5 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-zinc-200 bg-zinc-200 sm:grid-cols-4">
        {metrics.map(([label, value]) => (
          <div key={label} className="min-w-0 bg-white px-4 py-3.5 sm:px-5">
            <dt className="text-xs text-zinc-500 sm:text-sm">{label}</dt>
            <dd className="mt-1 text-xl font-semibold tabular-nums tracking-tight sm:text-2xl">{value}</dd>
          </div>
        ))}
      </dl>
    </>
  );
}
