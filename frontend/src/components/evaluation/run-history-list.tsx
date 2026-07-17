"use client";

import { cn } from "@/lib/utils";
import { formatRelative } from "@/lib/format";
import type { EvaluationRunOut } from "@/lib/types";

export function RunHistoryList({
  runs,
  selectedId,
  onSelect,
}: {
  runs: EvaluationRunOut[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  if (runs.length === 0) return null;

  return (
    <div>
      <p className="mb-2 text-xs text-muted-foreground">Runs from this session</p>
      <div className="flex flex-wrap gap-2">
        {runs.map((run) => (
          <button
            key={run.id}
            onClick={() => onSelect(run.id)}
            className={cn(
              "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
              selectedId === run.id
                ? "border-primary/50 bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            F1 {Math.round(run.overall.f1 * 100)}% · {formatRelative(run.started_at)}
          </button>
        ))}
      </div>
    </div>
  );
}
