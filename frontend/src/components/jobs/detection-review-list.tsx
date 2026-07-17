"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { Check, ChevronDown, RotateCcw, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useHue } from "@/hooks/use-hue";
import { PII_TYPE_COLORS, PII_TYPE_LABELS } from "@/lib/colors";
import { ALL_PII_TYPES, type DetectionOut, type PIIType, type ReviewDecision } from "@/lib/types";

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const tone = confidence >= 0.9 ? "#0ca30c" : confidence >= 0.75 ? "#fab219" : "#d03b3b";
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium tabular-nums" style={{ color: tone }}>
      {pct}%
    </span>
  );
}

function DetectionCard({
  detection,
  active,
  onHover,
  onReview,
  readOnly,
}: {
  detection: DetectionOut;
  active: boolean;
  onHover: (id: string | null) => void;
  onReview: (id: string, decision: ReviewDecision, newType?: PIIType) => void;
  readOnly?: boolean;
}) {
  const effectiveType = detection.new_pii_type ?? detection.pii_type;
  const color = useHue(PII_TYPE_COLORS[effectiveType]);
  const decision = detection.human_decision;

  return (
    <motion.div
      layout
      onMouseEnter={() => onHover(detection.id)}
      onMouseLeave={() => onHover(null)}
      className={cn(
        "rounded-xl border p-3.5 transition-colors",
        active ? "border-primary/50 bg-primary/5" : "border-border/70 bg-card",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="rounded-full px-2 py-0.5 text-[11px] font-semibold"
              style={{ backgroundColor: `${color}1c`, color }}
            >
              {PII_TYPE_LABELS[effectiveType]}
            </span>
            <ConfidenceBadge confidence={detection.confidence} />
          </div>
          <p className="mt-1.5 truncate font-mono text-sm" title={detection.raw_value}>
            {detection.raw_value}
          </p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">via {detection.source_detector}</p>
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <Button
            size="icon-sm"
            variant={decision === "accept" ? "default" : "outline"}
            aria-label="Accept"
            disabled={readOnly}
            onClick={() => onReview(detection.id, "accept")}
          >
            <Check className="size-3.5" />
          </Button>
          <Button
            size="icon-sm"
            variant={decision === "reject" ? "destructive" : "outline"}
            aria-label="Reject"
            disabled={readOnly}
            onClick={() => onReview(detection.id, "reject")}
          >
            <X className="size-3.5" />
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button
                  size="icon-sm"
                  variant={decision === "retype" ? "default" : "outline"}
                  aria-label="Retype"
                  disabled={readOnly}
                />
              }
            >
              <ChevronDown className="size-3.5" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {ALL_PII_TYPES.filter((t) => t !== effectiveType).map((type) => (
                <DropdownMenuItem key={type} onClick={() => onReview(detection.id, "retype", type)}>
                  {PII_TYPE_LABELS[type]}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {decision && decision !== "accept" && (
        <div className="mt-2 flex items-center gap-1 text-[11px] text-muted-foreground">
          <RotateCcw className="size-3" />
          {decision === "reject" ? "Marked not PII" : `Retyped to ${PII_TYPE_LABELS[effectiveType]}`}
        </div>
      )}
    </motion.div>
  );
}

export function DetectionReviewList({
  detections,
  activeId,
  onHover,
  onReview,
  readOnly,
}: {
  detections: DetectionOut[];
  activeId: string | null;
  onHover: (id: string | null) => void;
  onReview: (id: string, decision: ReviewDecision, newType?: PIIType) => void;
  readOnly?: boolean;
}) {
  if (detections.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border py-12 text-center text-sm text-muted-foreground">
        No PII detected for the selected types.
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {detections.map((detection) => (
        <DetectionCard
          key={detection.id}
          detection={detection}
          active={activeId === detection.id}
          onHover={onHover}
          onReview={onReview}
          readOnly={readOnly}
        />
      ))}
    </div>
  );
}
