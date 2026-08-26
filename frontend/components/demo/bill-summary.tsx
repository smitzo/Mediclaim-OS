import { ReceiptText } from "lucide-react";
import type { ReactNode } from "react";
import type { DemoResult } from "@/lib/demo-sample";
import { formatInr } from "@/lib/demo-format";
import { DetailSection } from "./result-summary";

export function BillSummary({ result, source }: { result: DemoResult; source?: ReactNode }) {
  const bill = result.extracted_data.itemized_bill;
  return (
    <DetailSection title="Itemized bill" icon={<ReceiptText aria-hidden="true" className="h-4 w-4 text-zinc-600" />} source={source}>
      <div className="overflow-hidden rounded-md border border-zinc-200">
        <table className="w-full text-left text-xs sm:text-sm">
          <caption className="sr-only">Fictional itemized hospital bill in Indian rupees (INR)</caption>
          <thead className="bg-zinc-50 text-xs text-zinc-500">
            <tr>
              <th scope="col" className="px-3 py-2 font-medium">Description</th>
              <th scope="col" className="px-2 py-2 text-center font-medium">Qty</th>
              <th scope="col" className="px-3 py-2 text-right font-medium">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {bill.line_items.map((item) => (
              <tr key={item.description}>
                <th scope="row" className="px-3 py-2.5 font-normal text-zinc-700">{item.description}</th>
                <td className="px-2 py-2.5 text-center tabular-nums text-zinc-600">{item.quantity}</td>
                <td className="whitespace-nowrap px-3 py-2.5 text-right tabular-nums text-zinc-800">{formatInr(item.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot className="border-t border-zinc-200 bg-zinc-50 font-semibold">
            <tr><th scope="row" colSpan={2} className="px-3 py-3">Total billed <span className="ml-1 font-normal text-zinc-500">INR</span></th><td className="whitespace-nowrap px-3 py-3 text-right tabular-nums">{formatInr(bill.total_amount)}</td></tr>
          </tfoot>
        </table>
      </div>
    </DetailSection>
  );
}
