"use client";

import Link from "next/link";

export function DemoWorkspace() {
  return (
    <main className="min-h-screen bg-zinc-50 p-8 text-zinc-950">
      <p className="font-semibold text-blue-700">ClaimOps</p>
      <h1 className="mt-4 text-3xl font-semibold">Document Processor</h1>
      <p className="mt-2 text-sm text-zinc-600">Try the sample PDF and explore its structured claim data.</p>
      <Link className="mt-6 inline-block text-sm text-blue-700 underline" href="/workspace">Company workspace</Link>
    </main>
  );
}
