"use client";

import * as React from "react";
import { Eye, EyeOff } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Switch } from "@/components/ui/switch";
import { PII_TYPE_COLORS, PII_TYPE_LABELS } from "@/lib/colors";
import { useHue } from "@/hooks/use-hue";
import type { AuditLogFile } from "@/lib/types";
import type { PIIType } from "@/lib/types";

function mask(value: string): string {
  if (value.length <= 2) return "••";
  return `${value[0]}${"•".repeat(Math.min(value.length - 2, 8))}${value[value.length - 1]}`;
}

function TypeTag({ type }: { type: PIIType }) {
  const color = useHue(PII_TYPE_COLORS[type]);
  return (
    <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ backgroundColor: `${color}1c`, color }}>
      {PII_TYPE_LABELS[type]}
    </span>
  );
}

export function AuditLogTable({ log }: { log: AuditLogFile }) {
  const [reveal, setReveal] = React.useState(false);

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          <span className="font-semibold text-foreground">{log.event_count}</span> redaction events
        </p>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          {reveal ? <Eye className="size-4" /> : <EyeOff className="size-4" />}
          Show original values
          <Switch checked={reveal} onCheckedChange={setReveal} />
        </label>
      </div>

      <div className="rounded-xl border border-border/70">
        <div className="max-h-[420px] overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Original</TableHead>
                <TableHead>Replacement</TableHead>
                <TableHead>Detector</TableHead>
                <TableHead className="text-right">Confidence</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {log.events.map((event, i) => (
                <TableRow key={`${event.entity_id}-${i}`}>
                  <TableCell>
                    <TypeTag type={event.pii_type} />
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {reveal ? event.original : mask(event.original)}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{event.replacement}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{event.source_detector}</TableCell>
                  <TableCell className="text-right tabular-nums text-xs">
                    {Math.round(event.confidence * 100)}%
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
