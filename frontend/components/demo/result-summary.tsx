import { ClipboardPlus, UserRound } from "lucide-react";
import type { ReactNode } from "react";
import type { DemoResult } from "@/lib/demo-sample";
import { formatDemoDate } from "@/lib/demo-format";
import { SourceLink } from "./source-link";

export function DetailSection({ title, icon, children, source }: { title: string; icon: ReactNode; children: ReactNode; source?: ReactNode }) {
  return (
    <section aria-label={title} className="border-b border-zinc-100 py-4 last:border-b-0">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-900">{icon}{title}</h3>
        {source}
      </div>
      {children}
    </section>
  );
}

export function DetailFields({ fields }: { fields: Array<[string, string]> }) {
  return (
    <dl className="grid grid-cols-2 gap-x-5 gap-y-4 text-sm">
      {fields.map(([label, value]) => (
        <div key={label} className="min-w-0">
          <dt className="text-xs leading-5 text-zinc-500">{label}</dt>
          <dd className="mt-0.5 break-words font-medium leading-5 text-zinc-900">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ResultSummary({ result, onSource }: { result: DemoResult; onSource: (page: number) => void }) {
  const { identity, discharge_summary: discharge } = result.extracted_data;
  return (
    <div className="mt-3">
      <DetailSection title="Patient & policy" icon={<UserRound aria-hidden="true" className="h-4 w-4 text-zinc-600" />} source={<SourceLink page={1} section="patient and policy" onSource={onSource} />}>
        <DetailFields fields={[
          ["Patient name", identity.patient_name], ["Policy number", identity.policy_number],
          ["Hospital", discharge.hospital_name], ["Claim type", identity.claim_type],
        ]} />
      </DetailSection>
      <DetailSection title="Discharge summary" icon={<ClipboardPlus aria-hidden="true" className="h-4 w-4 text-zinc-600" />} source={<SourceLink page={2} section="discharge summary" onSource={onSource} />}>
        <DetailFields fields={[
          ["Admitted", formatDemoDate(discharge.admission_date)], ["Discharged", formatDemoDate(discharge.discharge_date)],
          ["Diagnosis", discharge.final_diagnosis], ["Condition at discharge", discharge.condition_at_discharge],
        ]} />
      </DetailSection>
    </div>
  );
}
