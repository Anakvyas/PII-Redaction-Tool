"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { PolicyOut } from "@/lib/types";

export function PolicySelect({
  policies,
  value,
  onChange,
}: {
  policies: PolicyOut[];
  value: string | null;
  onChange: (policyId: string) => void;
}) {
  return (
    <Select value={value ?? ""} onValueChange={(next) => onChange(next as string)}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder="Choose a redaction policy" />
      </SelectTrigger>
      <SelectContent>
        {policies.map((policy) => (
          <SelectItem key={policy.id} value={policy.id}>
            {policy.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
