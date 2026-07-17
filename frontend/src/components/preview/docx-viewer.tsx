"use client";

import * as React from "react";
import mammoth from "mammoth";
import { Loader2 } from "lucide-react";
import { applyTextHighlights } from "@/components/preview/apply-highlights";
import type { PreviewHighlight } from "@/components/preview/types";

export function DocxViewer({
  fileUrl,
  highlights,
  activeHighlightId,
  onHighlightHover,
}: {
  fileUrl: string;
  highlights: PreviewHighlight[];
  activeHighlightId?: string | null;
  onHighlightHover?: (id: string | null) => void;
}) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [html, setHtml] = React.useState<string | null>(null);
  const [status, setStatus] = React.useState<"loading" | "ready" | "error">("loading");

  React.useEffect(() => {
    let cancelled = false;

    fetch(fileUrl)
      .then((res) => {
        if (!res.ok) throw new Error("download failed");
        return res.arrayBuffer();
      })
      .then((buffer) => mammoth.convertToHtml({ arrayBuffer: buffer }))
      .then((result) => {
        if (cancelled) return;
        setHtml(result.value);
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [fileUrl]);

  React.useEffect(() => {
    if (status !== "ready" || !containerRef.current) return;
    applyTextHighlights(containerRef.current, highlights);
  }, [status, html, highlights]);

  React.useEffect(() => {
    const root = containerRef.current;
    if (!root || !onHighlightHover) return;

    function handleOver(event: Event) {
      const target = (event.target as HTMLElement)?.closest<HTMLElement>("[data-highlight-id]");
      onHighlightHover?.(target?.dataset.highlightId ?? null);
    }
    function handleOut() {
      onHighlightHover?.(null);
    }

    root.addEventListener("mouseover", handleOver);
    root.addEventListener("mouseout", handleOut);
    return () => {
      root.removeEventListener("mouseover", handleOver);
      root.removeEventListener("mouseout", handleOut);
    };
  }, [onHighlightHover, html]);

  React.useEffect(() => {
    const root = containerRef.current;
    if (!root) return;
    root.querySelectorAll<HTMLElement>("mark[data-highlight-id]").forEach((mark) => {
      const isActive = mark.dataset.highlightId === activeHighlightId;
      mark.style.outline = isActive ? "2px solid currentColor" : "none";
      mark.style.outlineOffset = "1px";
    });
  }, [activeHighlightId]);

  if (status === "loading") {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Rendering document…
      </div>
    );
  }

  if (status === "error") {
    return <div className="py-24 text-center text-sm text-destructive">Couldn&apos;t render this DOCX for preview.</div>;
  }

  return (
    <div
      ref={containerRef}
      className="docx-preview mx-auto max-w-[760px] rounded-lg border border-border/70 bg-white px-10 py-10 text-[13px] leading-relaxed text-black shadow-sm dark:bg-neutral-50"
      dangerouslySetInnerHTML={{ __html: html ?? "" }}
    />
  );
}
