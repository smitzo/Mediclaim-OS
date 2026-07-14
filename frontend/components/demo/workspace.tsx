"use client";

import { useDemo } from "@/lib/use-demo";
import { DemoFrame } from "./frame";

export function DemoWorkspace() {
  const demo = useDemo();
  return (
    <DemoFrame onReset={demo.reset}>
      <section aria-label="Demo workspace" className="grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]" />
    </DemoFrame>
  );
}
