export type DemoPdf = {
  id: string;
  label: string;
  filename: string;
  href: string;
  pages: number;
  sizeLabel: string;
};

export const demoPdfs: DemoPdf[] = [
  {
    id: "demo-claim-short-1",
    label: "Sample claim PDF 1",
    filename: "demo_claim_short_1.pdf",
    href: "/demo_pdfs/demo_claim_short_1.pdf",
    pages: 3,
    sizeLabel: "710 KB"
  },
  {
    id: "demo-claim-short-2",
    label: "Sample claim PDF 2",
    filename: "demo_claim_short_2.pdf",
    href: "/demo_pdfs/demo_claim_short_2.pdf",
    pages: 3,
    sizeLabel: "991 KB"
  },
  {
    id: "demo-claim-short-3",
    label: "Sample claim PDF 3",
    filename: "demo_claim_short_3.pdf",
    href: "/demo_pdfs/demo_claim_short_3.pdf",
    pages: 3,
    sizeLabel: "1.1 MB"
  }
];

export async function demoPdfToFile(pdf: DemoPdf): Promise<File> {
  const response = await fetch(pdf.href);
  if (!response.ok) {
    throw new Error(`Unable to load ${pdf.filename}`);
  }
  const blob = await response.blob();
  return new File([blob], pdf.filename, { type: "application/pdf" });
}
