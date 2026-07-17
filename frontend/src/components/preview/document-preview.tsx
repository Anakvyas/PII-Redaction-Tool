"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { PdfViewer } from "@/components/preview/pdf-viewer";
import { DocxViewer } from "@/components/preview/docx-viewer";
import type { PreviewHighlight } from "@/components/preview/types";
import { PII_TYPE_COLORS, PII_TYPE_LABELS } from "@/lib/colors";
import type { DetectionOut, DocumentFormat } from "@/lib/types";

export function DocumentPreview({
  format,
  fileUrl,
  detections,
  activeHighlightId,
  onHighlightHover,
}: {
  format: DocumentFormat;
  fileUrl: string;
  detections: DetectionOut[];
  activeHighlightId?: string | null;
  onHighlightHover?: (id: string | null) => void;
}) {
  const { resolvedTheme } = useTheme();
  const dark = resolvedTheme === "dark";

  const highlights: PreviewHighlight[] = React.useMemo(
    () =>
      detections
        .filter((d) => d.human_decision !== "reject")
        .map((d) => {
          const type = d.new_pii_type ?? d.pii_type;
          const token = PII_TYPE_COLORS[type];
          return {
            id: d.id,
            page: d.span.page,
            bbox: d.span.bbox,
            rawValue: d.raw_value,
            color: dark ? token.dark : token.light,
            label: `${PII_TYPE_LABELS[type]} · ${Math.round(d.confidence * 100)}% confidence`,
          };
        }),
    [detections, dark],
  );

  if (format === "pdf") {
    return (
      <PdfViewer
        key={fileUrl}
        fileUrl={fileUrl}
        highlights={highlights}
        activeHighlightId={activeHighlightId}
        onHighlightHover={onHighlightHover}
      />
    );
  }

  return (
    <DocxViewer
      key={fileUrl}
      fileUrl={fileUrl}
      highlights={highlights}
      activeHighlightId={activeHighlightId}
      onHighlightHover={onHighlightHover}
    />
  );
}
