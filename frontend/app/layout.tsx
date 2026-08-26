import type { Metadata } from "next";
import "./tailwind.css";

export const metadata: Metadata = {
  title: "ClaimOps Document Processor",
  description: "Explore a sample medical claim PDF and its structured patient, discharge, and billing data with ClaimOps."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
