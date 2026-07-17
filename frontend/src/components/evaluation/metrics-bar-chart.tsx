"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useHue } from "@/hooks/use-hue";
import { PII_TYPE_LABELS } from "@/lib/colors";
import type { EvaluationMetricsOut, PIIType } from "@/lib/types";

const SERIES = [
  { key: "precision", label: "Precision", hue: { light: "#2a78d6", dark: "#3987e5", needsLabel: false } },
  { key: "recall", label: "Recall", hue: { light: "#1baf7a", dark: "#199e70", needsLabel: true } },
  { key: "f1", label: "F1", hue: { light: "#eda100", dark: "#c98500", needsLabel: true } },
] as const;

function LineKeyTooltip({
  active,
  payload,
  label,
  colors,
}: {
  active?: boolean;
  payload?: { dataKey: string; value: number }[];
  label?: string;
  colors: Record<string, string>;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border/70 bg-popover px-3 py-2 text-xs shadow-md">
      <p className="mb-1.5 font-medium text-foreground">{label}</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-2 py-0.5">
          <span className="h-0.5 w-3 rounded-full" style={{ backgroundColor: colors[entry.dataKey] }} />
          <span className="font-semibold tabular-nums text-foreground">{Math.round(entry.value * 100)}%</span>
          <span className="text-muted-foreground capitalize">{entry.dataKey}</span>
        </div>
      ))}
    </div>
  );
}

export function MetricsBarChart({ perType }: { perType: Partial<Record<PIIType, EvaluationMetricsOut>> }) {
  const precisionColor = useHue(SERIES[0].hue);
  const recallColor = useHue(SERIES[1].hue);
  const f1Color = useHue(SERIES[2].hue);
  const colors = { precision: precisionColor, recall: recallColor, f1: f1Color };

  const data = (Object.entries(perType) as [PIIType, EvaluationMetricsOut][]).map(([type, metrics]) => ({
    type: PII_TYPE_LABELS[type],
    precision: metrics.precision,
    recall: metrics.recall,
    f1: metrics.f1,
  }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }} barGap={2} barCategoryGap="20%">
          <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="0" />
          <XAxis
            dataKey="type"
            tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            domain={[0, 1]}
            tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <Tooltip content={<LineKeyTooltip colors={colors} />} cursor={{ fill: "var(--muted)", opacity: 0.4 }} />
          <Legend
            iconType="plainline"
            wrapperStyle={{ fontSize: 12, color: "var(--muted-foreground)" }}
            formatter={(value) => <span className="text-muted-foreground capitalize">{value}</span>}
          />
          <Bar dataKey="precision" name="Precision" fill={precisionColor} radius={[4, 4, 0, 0]} maxBarSize={24} />
          <Bar dataKey="recall" name="Recall" fill={recallColor} radius={[4, 4, 0, 0]} maxBarSize={24} />
          <Bar dataKey="f1" name="F1" fill={f1Color} radius={[4, 4, 0, 0]} maxBarSize={24} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
