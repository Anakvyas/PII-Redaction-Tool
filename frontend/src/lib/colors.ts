/**
 * Validated categorical + status palette (see dataviz skill: references/palette.md).
 * Fixed hue order — never cycled, never reassigned when the type list is filtered.
 * ip_address is deliberately excluded from the categorical set and rendered as a
 * neutral "other/technical" bucket instead of a generated 9th hue.
 */
import type { PIIType, JobStatus } from "@/lib/types";

export interface HueToken {
  light: string;
  dark: string;
  /** true when this slot falls below 3:1 contrast on its own surface and needs a visible label, never color alone */
  needsLabel: boolean;
}

export const PII_TYPE_COLORS: Record<PIIType, HueToken> = {
  person: { light: "#2a78d6", dark: "#3987e5", needsLabel: false }, // blue
  email: { light: "#1baf7a", dark: "#199e70", needsLabel: true }, // aqua
  phone: { light: "#eda100", dark: "#c98500", needsLabel: true }, // yellow
  address: { light: "#008300", dark: "#008300", needsLabel: false }, // green
  company: { light: "#4a3aa7", dark: "#9085e9", needsLabel: false }, // violet
  ssn: { light: "#e34948", dark: "#e66767", needsLabel: false }, // red
  credit_card: { light: "#e87ba4", dark: "#d55181", needsLabel: true }, // magenta
  dob: { light: "#eb6834", dark: "#d95926", needsLabel: false }, // orange
  ip_address: { light: "#898781", dark: "#898781", needsLabel: false }, // muted/"other"
};

export const PII_TYPE_LABELS: Record<PIIType, string> = {
  person: "Person",
  email: "Email",
  phone: "Phone",
  address: "Address",
  company: "Company",
  ssn: "SSN",
  credit_card: "Credit Card",
  dob: "Date of Birth",
  ip_address: "IP Address",
};

export const STATUS_COLORS = {
  good: { light: "#0ca30c", dark: "#0ca30c" },
  warning: { light: "#fab219", dark: "#fab219" },
  serious: { light: "#ec835a", dark: "#ec835a" },
  critical: { light: "#d03b3b", dark: "#d03b3b" },
} as const;

export type StatusRole = keyof typeof STATUS_COLORS;

export const JOB_STATUS_ROLE: Record<JobStatus, StatusRole> = {
  queued: "warning",
  detecting: "warning",
  needs_review: "warning",
  redacting: "warning",
  completed: "good",
  failed: "critical",
};

/** Sequential blue ramp, light -> dark, for magnitude encodings (bars, heat cells). */
export const SEQUENTIAL_BLUE = [
  "#cde2fb",
  "#9ec5f4",
  "#6da7ec",
  "#3987e5",
  "#256abf",
  "#184f95",
  "#0d366b",
];
