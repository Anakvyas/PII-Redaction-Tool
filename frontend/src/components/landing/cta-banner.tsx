import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
import { Reveal } from "@/components/landing/reveal";

export function CtaBanner() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-24 sm:px-6 lg:px-8">
      <Reveal>
        <div className="relative overflow-hidden rounded-3xl border border-border/70 bg-primary px-8 py-16 text-center text-primary-foreground sm:px-16">
          <div className="absolute inset-0 bg-[radial-gradient(60%_60%_at_50%_0%,rgba(255,255,255,0.16),transparent)]" />
          <div className="relative">
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Your first redacted document is minutes away
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-primary-foreground/80 text-pretty">
              Upload a file, review the findings, export a clean copy — with a full audit trail waiting on the
              other side.
            </p>
            <Link
              href="/workspace"
              className={cn(
                buttonVariants({ size: "lg", variant: "secondary" }),
                "group mt-8 gap-2 bg-background px-7 text-foreground hover:bg-background/90",
              )}
            >
              Start redacting
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
