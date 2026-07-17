"use client";

import { ALL_PII_TYPES, type PIIType } from "@/lib/types";
import { PII_TYPE_COLORS, PII_TYPE_LABELS } from "@/lib/colors";
import { useHue } from "@/hooks/use-hue";
import { cn } from "@/lib/utils";

function PiiTypeChip({ type, active, onToggle }: { type: PIIType; active: boolean; onToggle: () => void }) {
  const color = useHue(PII_TYPE_COLORS[type]);

  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={active}
      className={cn(
        "rounded-full border px-3 py-1.5 text-xs font-medium transition-all",
        active ? "shadow-sm" : "border-border bg-background text-muted-foreground hover:text-foreground",
      )}
      style={active ? { borderColor: `${color}55`, backgroundColor: `${color}18`, color } : undefined}
    >
      {PII_TYPE_LABELS[type]}
    </button>
  );
}

export function PiiTypePicker({
  selected,
  onChange,
}: {
  selected: PIIType[];
  onChange: (next: PIIType[]) => void;
}) {
  function toggle(type: PIIType) {
    if (selected.includes(type)) {
      onChange(selected.filter((t) => t !== type));
    } else {
      onChange([...selected, type]);
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {ALL_PII_TYPES.map((type) => (
        <PiiTypeChip key={type} type={type} active={selected.includes(type)} onToggle={() => toggle(type)} />
      ))}
    </div>
  );
}
