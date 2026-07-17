"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
import { DocumentMockup } from "@/components/landing/document-mockup";

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-aurora">
      <div className="absolute inset-0 bg-grid mask-fade-b opacity-40 dark:opacity-20" />
      <div className="relative mx-auto grid max-w-6xl gap-12 px-4 pt-20 pb-24 sm:px-6 lg:grid-cols-2 lg:items-center lg:pt-28 lg:pb-32 lg:px-8">
        <div>
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/60 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur"
          >
            <Sparkles className="size-3.5 text-primary" />
            Detection, review, and redaction in one pass
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.05 }}
            className="mt-6 text-4xl font-semibold tracking-tight text-balance sm:text-5xl lg:text-6xl"
          >
            Redact PII from documents
            <br />
            <span className="text-gradient">without breaking the formatting.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="mt-6 max-w-xl text-lg text-muted-foreground text-pretty"
          >
            Upload a DOCX or PDF, let the detection engine flag names, emails, phone numbers, addresses, and more,
            review each finding, then export a redacted file that keeps every font, table, and header exactly
            where it was.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="mt-9 flex flex-wrap items-center gap-3"
          >
            <Link href="/workspace" className={cn(buttonVariants({ size: "lg" }), "group gap-2 px-6")}>
              Start redacting
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link
              href="#how-it-works"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }), "px-6")}
            >
              See how it works
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-10 flex flex-wrap gap-x-8 gap-y-3 text-sm text-muted-foreground"
          >
            <span>9 PII types out of the box</span>
            <span className="hidden sm:inline">·</span>
            <span>DOCX + PDF</span>
            <span className="hidden sm:inline">·</span>
            <span>Full audit trail</span>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
        >
          <DocumentMockup />
        </motion.div>
      </div>
    </section>
  );
}
