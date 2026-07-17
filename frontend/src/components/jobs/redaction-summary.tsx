"use client";

import { PII_TYPE_COLORS, PII_TYPE_LABELS } from "@/lib/colors";
import { useHue } from "@/hooks/use-hue";
import type { PIIType } from "@/lib/types";

function CountChip({ type, count }: { type: PIIType; count: number }) {
  const color = useHue(PII_TYPE_COLORS[type]);
  return (
    <div
      className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm"
      style={{ borderColor: `${color}30`, backgroundColor: `${color}0f` }}
    >
      <span className="font-medium" style={{ color }}>
        {PII_TYPE_LABELS[type]}
      </span>
      <span className="tabular-nums text-muted-foreground">{count}</span>
    </div>
  );
}

export function RedactionSummary({
  countsByType,
  totalRedacted,
}: {
  countsByType: Partial<Record<PIIType, number>>;
  totalRedacted: number;
}) {
  const entries = Object.entries(countsByType) as [PIIType, number][];

  return (
    <div>
      <p className="text-sm text-muted-foreground">
        <span className="font-semibold text-foreground">{totalRedacted}</span> entities redacted
      </p>
      {entries.length > 0 && (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {entries.map(([type, count]) => (
            <CountChip key={type} type={type} count={count} />
          ))}
        </div>
      )}
    </div>
  );
}
