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
  // Pages get mounted (and stay mounted) once they scroll near the viewport,
  // instead of all at once — see the IntersectionObserver effect below.
  const [visiblePages, setVisiblePages] = React.useState<Set<number>>(() => new Set([1]));
  const [heightByPage, setHeightByPage] = React.useState<Record<number, number>>({});
  const pageWrapperRefs = React.useRef(new Map<number, HTMLDivElement>());

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
      // scrollbar again — an infinite ResizeObserver feedback loop.
      // `scrollbar-gutter: stable` (globals.css) stops the scrollbar itself
      // from moving this container, but this threshold stays as a second
      // line of defense against sub-scrollbar-width layout noise.
      setContainerWidth((prev) => (Math.abs(prev - next) < 4 ? prev : next));
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Lazily mount pages as they approach the viewport instead of rendering
  // every page's canvas up front — for large documents (100+ pages),
  // mounting everything at once is what pinned CPU/memory and made the
  // preview appear to freeze or crash.
  React.useEffect(() => {
    if (numPages === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const newlyVisible = entries.filter((e) => e.isIntersecting).map((e) => Number((e.target as HTMLElement).dataset.pageNumber));
        if (newlyVisible.length === 0) return;
        setVisiblePages((prev) => {
          const next = new Set(prev);
          let changed = false;
          for (const n of newlyVisible) {
            if (!next.has(n)) {
              next.add(n);
              changed = true;
            }
          }
          return changed ? next : prev;
        });
      },
      { rootMargin: "600px 0px" },
    );
    pageWrapperRefs.current.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [numPages]);

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
          const isVisible = visiblePages.has(pageNumber);
          // US Letter aspect ratio as a placeholder guess until the page has
          // rendered once and told us its real height — keeps scroll height
          // roughly stable so pages don't jump as they mount in.
          const placeholderHeight = heightByPage[pageNumber] ?? containerWidth * 1.294;

          return (
            <div
              key={pageNumber}
              data-page-number={pageNumber}
              ref={(el) => {
                if (el) pageWrapperRefs.current.set(pageNumber, el);
                else pageWrapperRefs.current.delete(pageNumber);
              }}
              className="relative mx-auto w-fit overflow-hidden rounded-lg border border-border/70 shadow-sm"
            >
              {isVisible ? (
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
                    setHeightByPage((prev) =>
                      prev[pageNumber] === page.height ? prev : { ...prev, [pageNumber]: page.height },
                    );
                  }}
                />
              ) : (
                <div
                  className="flex items-center justify-center bg-muted/30 text-xs text-muted-foreground"
                  style={{ width: containerWidth, height: placeholderHeight }}
                >
                  Page {pageNumber}
                </div>
              )}
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
