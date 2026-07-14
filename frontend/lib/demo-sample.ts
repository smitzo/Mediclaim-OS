import fixture from "@/public/demo/sample-claim.json";
import type { ClaimResponse } from "./api";

export type DemoPage = { number: number; title: string; documentType: string; preview: string };
export type DemoBillLine = { description: string; quantity: number; unit_price: string; amount: string };
export type DemoResult = ClaimResponse & {
  extracted_data: {
    identity: { patient_name: string; policy_number: string; insurance_provider: string; claim_type: string };
    discharge_summary: {
      hospital_name: string; admission_date: string; discharge_date: string;
      final_diagnosis: string; treatment_summary: string; attending_physician: string; condition_at_discharge: string;
    };
    itemized_bill: {
      bill_number: string; bill_date: string; hospital_name: string; patient_name: string;
      currency: string; line_items: DemoBillLine[]; subtotal: string; tax: string; discount: string; total_amount: string;
    };
  };
};

export const demoSample = {
  id: fixture.id,
  filename: fixture.filename,
  pdfHref: fixture.pdfHref,
  resultHref: "/demo/sample-claim.json",
  pages: fixture.pages satisfies DemoPage[],
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === "object" && !Array.isArray(value);

/** Treat static assets as untrusted input too: a bad deployment must not show success. */
export function parseDemoResult(payload: unknown): DemoResult {
  if (!isRecord(payload) || payload.id !== demoSample.id || !isRecord(payload.result)) {
    throw new Error("The sample results are unavailable or invalid. Please try again.");
  }
  // A fixed, synthetic fixture is the acceptance contract for this public demo.
  // Requiring the same schema and values prevents a mismatched asset deployment.
  if (JSON.stringify(payload.result) !== JSON.stringify(fixture.result)) {
    throw new Error("The sample results do not match this demo PDF. Please refresh and try again.");
  }
  return payload.result as DemoResult;
}
