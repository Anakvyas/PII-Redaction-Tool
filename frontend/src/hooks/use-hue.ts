"use client";

import { useTheme } from "next-themes";
import type { HueToken } from "@/lib/colors";

/** Resolves a light/dark hue token against the active theme (light until the provider settles). */
export function useHue(token: HueToken): string {
  const { resolvedTheme } = useTheme();
  return resolvedTheme === "dark" ? token.dark : token.light;
}
