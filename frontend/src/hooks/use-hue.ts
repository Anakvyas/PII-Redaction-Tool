"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import type { HueToken } from "@/lib/colors";

/** Resolves a light/dark hue token against the active theme (light until the provider settles). */
export function useHue(token: HueToken): string {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  // See theme-toggle.tsx: gating on mount avoids a hydration mismatch,
  // since resolvedTheme isn't reliable until after the client mounts.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  React.useEffect(() => setMounted(true), []);
  return mounted && resolvedTheme === "dark" ? token.dark : token.light;
}
