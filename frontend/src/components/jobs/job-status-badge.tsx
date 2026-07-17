import { CheckCircle2, Clock, Eye, Loader2, ScanSearch, XCircle } from "lucide-react";
import { STATUS_COLORS, JOB_STATUS_ROLE } from "@/lib/colors";
import type { JobStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const LABELS: Record<JobStatus, string> = {
  queued: "Queued",
  detecting: "Detecting",
  needs_review: "Needs review",
  redacting: "Redacting",
  completed: "Completed",
  failed: "Failed",
};

const ICONS: Record<JobStatus, React.ComponentType<{ className?: string }>> = {
  queued: Clock,
  detecting: ScanSearch,
  needs_review: Eye,
  redacting: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
};

const SPINNING: JobStatus[] = ["detecting", "redacting", "queued"];

export function JobStatusBadge({ status, className }: { status: JobStatus; className?: string }) {
  const role = JOB_STATUS_ROLE[status];
  const color = STATUS_COLORS[role];
  const Icon = ICONS[status];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        className,
      )}
      style={{
        color: color.light,
        borderColor: `${color.light}40`,
        backgroundColor: `${color.light}14`,
      }}
    >
      <Icon className={cn("size-3.5", SPINNING.includes(status) && "animate-spin")} />
      {LABELS[status]}
    </span>
  );
}
