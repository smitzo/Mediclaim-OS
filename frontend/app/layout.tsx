import type { Metadata } from "next";
import "./tailwind.css";

export const metadata: Metadata = {
  title: "ClaimOps Document Processor",
  description: "Distributed medical claim invoice processing dashboard"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
