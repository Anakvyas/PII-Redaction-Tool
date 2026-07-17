"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Check, TriangleAlert, X } from "lucide-react";
import { STATUS_COLORS } from "@/lib/colors";
import { PII_TYPE_LABELS } from "@/lib/colors";
import type { EvaluationMetricsOut, PIIType } from "@/lib/types";

const SEGMENTS = [
  { key: "true_positives", label: "True positive", color: STATUS_COLORS.good.light, Icon: Check },
  { key: "false_positives", label: "False positive", color: STATUS_COLORS.critical.light, Icon: X },
  { key: "false_negatives", label: "False negative", color: STATUS_COLORS.warning.light, Icon: TriangleAlert },
] as const;

function BreakdownTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { dataKey: string; value: number }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border/70 bg-popover px-3 py-2 text-xs shadow-md">
      <p className="mb-1.5 font-medium text-foreground">{label}</p>
      {SEGMENTS.map((seg) => {
        const entry = payload.find((p) => p.dataKey === seg.key);
        if (!entry) return null;
        return (
          <div key={seg.key} className="flex items-center gap-2 py-0.5">
            <seg.Icon className="size-3" style={{ color: seg.color }} />
            <span className="font-semibold tabular-nums text-foreground">{entry.value}</span>
            <span className="text-muted-foreground">{seg.label}</span>
          </div>
        );
      })}
    </div>
  );
}

export function ConfusionBreakdownChart({ perType }: { perType: Partial<Record<PIIType, EvaluationMetricsOut>> }) {
  const data = (Object.entries(perType) as [PIIType, EvaluationMetricsOut][]).map(([type, metrics]) => ({
    type: PII_TYPE_LABELS[type],
    true_positives: metrics.true_positives,
    false_positives: metrics.false_positives,
    false_negatives: metrics.false_negatives,
  }));

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-4">
        {SEGMENTS.map((seg) => (
          <span key={seg.key} className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <seg.Icon className="size-3.5" style={{ color: seg.color }} />
            {seg.label}
          </span>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }} barCategoryGap="24%">
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis
            dataKey="type"
            tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={32}
          />
          <Tooltip content={<BreakdownTooltip />} cursor={{ fill: "var(--muted)", opacity: 0.4 }} />
          {SEGMENTS.map((seg, i) => (
            <Bar
              key={seg.key}
              dataKey={seg.key}
              stackId="entities"
              fill={seg.color}
              maxBarSize={28}
              radius={i === SEGMENTS.length - 1 ? [4, 4, 0, 0] : 0}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
