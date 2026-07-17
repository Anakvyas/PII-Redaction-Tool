"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  // Deliberate: resolvedTheme is only meaningful after the client has
  // mounted (next-themes' inline script resolves it before hydration but
  // outside React's own render), so rendering off it directly causes a
  // hydration mismatch. Gating on `mounted` is the documented next-themes
  // pattern — not a case the set-state-in-effect lint rule should block.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  React.useEffect(() => setMounted(true), []);

  const isDark = resolvedTheme === "dark";

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label="Toggle theme"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="relative overflow-hidden"
    >
      <AnimatePresence mode="wait" initial={false}>
        {mounted && (
          <motion.span
            key={isDark ? "moon" : "sun"}
            initial={{ scale: 0.4, opacity: 0, rotate: -90 }}
            animate={{ scale: 1, opacity: 1, rotate: 0 }}
            exit={{ scale: 0.4, opacity: 0, rotate: 90 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="flex"
          >
            {isDark ? <Moon className="size-[1.15rem]" /> : <Sun className="size-[1.15rem]" />}
          </motion.span>
        )}
      </AnimatePresence>
    </Button>
  );
}
