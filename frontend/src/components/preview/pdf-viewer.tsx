"use client";

import * as React from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PreviewHighlight } from "@/components/preview/types";

pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

// Without these, pdf.js can't resolve embedded-font character maps or
// non-embedded standard fonts (common in Word/LaTeX-exported prospectuses) —
// it fails per-page text drawing silently, leaving a blank white canvas even
// though the document's page count loaded fine.
const PDF_OPTIONS = {
  cMapUrl: "/pdfjs/cmaps/",
  cMapPacked: true,
  standardFontDataUrl: "/pdfjs/standard_fonts/",
};

export function PdfViewer({
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
  const [containerWidth, setContainerWidth] = React.useState(760);
  const [numPages, setNumPages] = React.useState(0);
  const [scaleByPage, setScaleByPage] = React.useState<Record<number, number>>({});

  React.useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width;
      if (!width) return;
      const next = Math.min(width, 900);
      // Rendering a page can itself toggle a vertical scrollbar (blank
      // canvases were short; real content is tall), which nudges this
      // container's width, which re-renders the page, which toggles the
      // scrollbar again — an infinite ResizeObserver feedback loop. Only
      // commit when the width actually moved by more than rounding noise.
      setContainerWidth((prev) => (Math.abs(prev - next) < 1 ? prev : next));
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const highlightsByPage = React.useMemo(() => {
    const map = new Map<number, PreviewHighlight[]>();
    for (const h of highlights) {
      if (h.page == null || !h.bbox) continue;
      const list = map.get(h.page) ?? [];
      list.push(h);
      map.set(h.page, list);
    }
    return map;
  }, [highlights]);

  return (
    <div ref={containerRef} className="w-full space-y-4">
      <Document
        file={fileUrl}
        options={PDF_OPTIONS}
        onLoadSuccess={(doc) => setNumPages(doc.numPages)}
        loading={
          <div className="flex items-center justify-center gap-2 py-24 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> Loading document…
          </div>
        }
        error={
          <div className="py-24 text-center text-sm text-destructive">
            Couldn&apos;t load this PDF for preview.
          </div>
        }
      >
        {Array.from({ length: numPages }, (_, i) => i + 1).map((pageNumber) => {
          const scale = scaleByPage[pageNumber];
          const pageHighlights = highlightsByPage.get(pageNumber - 1) ?? [];
          return (
            <div key={pageNumber} className="relative mx-auto w-fit overflow-hidden rounded-lg border border-border/70 shadow-sm">
              <Page
                pageNumber={pageNumber}
                width={containerWidth}
                renderTextLayer={false}
                renderAnnotationLayer={false}
                onLoadSuccess={(page) => {
                  const nextScale = page.width / page.originalWidth;
                  setScaleByPage((prev) =>
                    prev[pageNumber] === nextScale ? prev : { ...prev, [pageNumber]: nextScale },
                  );
                }}
              />
              {scale &&
                pageHighlights.map((h) => (
                  <button
                    key={h.id}
                    type="button"
                    onMouseEnter={() => onHighlightHover?.(h.id)}
                    onMouseLeave={() => onHighlightHover?.(null)}
                    title={h.label}
                    className={cn(
                      "absolute rounded-[3px] border-2 transition-all",
                      activeHighlightId === h.id ? "z-10 ring-2 ring-offset-1" : "",
                    )}
                    style={{
                      left: h.bbox![0] * scale,
                      top: h.bbox![1] * scale,
                      width: (h.bbox![2] - h.bbox![0]) * scale,
                      height: (h.bbox![3] - h.bbox![1]) * scale,
                      borderColor: h.color,
                      backgroundColor: `${h.color}${activeHighlightId === h.id ? "55" : "2e"}`,
                    }}
                  />
                ))}
            </div>
          );
        })}
      </Document>
    </div>
  );
}
