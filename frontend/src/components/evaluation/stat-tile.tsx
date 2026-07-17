import { cn } from "@/lib/utils";

export function StatTile({
  label,
  value,
  tone,
  className,
}: {
  label: string;
  value: string;
  tone?: string;
  className?: string;
}) {
  return (
    <div className={cn("rounded-2xl border border-border/70 bg-card p-5", className)}>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1.5 text-3xl font-semibold tracking-tight" style={tone ? { color: tone } : undefined}>
        {value}
      </p>
    </div>
  );
}
