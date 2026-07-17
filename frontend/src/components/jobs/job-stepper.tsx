import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { JobStatus } from "@/lib/types";

const STEPS: { key: JobStatus; label: string }[] = [
  { key: "detecting", label: "Detect" },
  { key: "needs_review", label: "Review" },
  { key: "redacting", label: "Redact" },
  { key: "completed", label: "Export" },
];

function stepIndex(status: JobStatus): number {
  if (status === "queued") return -1;
  if (status === "failed") return STEPS.length; // handled separately by caller
  return STEPS.findIndex((s) => s.key === status);
}

export function JobStepper({ status }: { status: JobStatus }) {
  const current = stepIndex(status);

  return (
    <div className="flex items-center">
      {STEPS.map((step, i) => {
        const done = status === "failed" ? false : i < current || status === "completed";
        const active = i === current && status !== "failed";
        return (
          <div key={step.key} className="flex flex-1 items-center last:flex-none">
            <div className="flex flex-col items-center gap-2">
              <div
                className={cn(
                  "flex size-8 items-center justify-center rounded-full border-2 text-xs font-semibold transition-colors",
                  done && "border-primary bg-primary text-primary-foreground",
                  active && !done && "border-primary text-primary",
                  !done && !active && "border-border text-muted-foreground",
                )}
              >
                {done ? <Check className="size-4" /> : active ? <Loader2 className="size-4 animate-spin" /> : i + 1}
              </div>
              <span
                className={cn(
                  "text-xs font-medium",
                  done || active ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={cn("mx-2 h-0.5 flex-1 rounded-full", i < current ? "bg-primary" : "bg-border")} />
            )}
          </div>
        );
      })}
    </div>
  );
}
