"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { demoSample, parseDemoResult, type DemoResult } from "./demo-sample";

export type DemoStatus = "idle" | "loading" | "complete" | "error";

export function useDemo() {
  const [selected, setSelected] = useState(false);
  const [status, setStatus] = useState<DemoStatus>("idle");
  const [result, setResult] = useState<DemoResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const request = useRef<AbortController | null>(null);
  const generation = useRef(0);

  useEffect(() => () => { generation.current += 1; request.current?.abort(); }, []);

  const reset = useCallback(() => {
    generation.current += 1;
    request.current?.abort();
    request.current = null;
    setSelected(false);
    setStatus("idle");
    setResult(null);
    setError(null);
    setRevision((value) => value + 1);
  }, []);

  const run = useCallback(async () => {
    if (!selected || request.current) return;
    const current = ++generation.current;
    const controller = new AbortController();
    request.current = controller;
    setStatus("loading");
    setResult(null);
    setError(null);
    try {
      const [pdf, response] = await Promise.all([
        fetch(demoSample.pdfHref, { signal: controller.signal }),
        fetch(demoSample.resultHref, { signal: controller.signal, cache: "no-cache" }),
      ]);
      if (!pdf.ok) throw new Error("The sample PDF could not be loaded. Please try again.");
      if (!response.ok) throw new Error("The sample results could not be loaded. Please try again.");
      const [bytes, payload] = await Promise.all([pdf.arrayBuffer(), response.json()]);
      if (new TextDecoder().decode(bytes.slice(0, 5)) !== "%PDF-") {
        throw new Error("The sample PDF is invalid. Please refresh and try again.");
      }
      const output = parseDemoResult(payload);
      if (generation.current !== current) return;
      setResult(output);
      setStatus("complete");
    } catch (exc) {
      if (generation.current !== current || controller.signal.aborted) return;
      setError(exc instanceof TypeError ? "The demo could not be loaded. Check your connection and try again." :
        exc instanceof SyntaxError ? "The sample results are invalid. Please try again." :
        exc instanceof Error ? exc.message : "Unable to load the demo. Please try again.");
      setStatus("error");
    } finally {
      if (generation.current === current) request.current = null;
    }
  }, [selected]);

  return { selected, select: () => setSelected(true), status, result, error, revision, run, reset };
}
