import Link from "next/link";
import { ArrowRight, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Reveal } from "@/components/landing/reveal";

const METRICS = [
  { label: "Precision", value: 92, color: "#2a78d6" },
  { label: "Recall", value: 88, color: "#1baf7a" },
  { label: "F1 score", value: 90, color: "#4a3aa7" },
];

export function EvaluationTeaser() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-24 sm:px-6 lg:px-8">
      <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
        <Reveal>
          <div className="inline-flex items-center gap-1.5 rounded-full border border-border/70 px-3 py-1 text-xs font-medium text-muted-foreground">
            <BarChart3 className="size-3.5 text-primary" />
            Evaluation dashboard
          </div>
          <h2 className="mt-5 text-3xl font-semibold tracking-tight sm:text-4xl">
            Know exactly how well detection performs
          </h2>
          <p className="mt-4 max-w-lg text-muted-foreground text-pretty">
            Run the bundled gold-standard evaluation against the detection pipeline, or compare your own
            ground-truth against predictions. Every run reports precision, recall, F1, a confusion matrix, and a
            per-entity classification report.
          </p>
          <Link href="/evaluation" className={cn(buttonVariants(), "group mt-7 gap-2")}>
            Open evaluation dashboard
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </Reveal>

        <Reveal delay={0.1}>
          <Card className="gap-5 rounded-2xl border-border/70 p-6">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>Bundled gold-standard run</span>
              <span className="font-medium text-foreground">v1</span>
            </div>
            <div className="space-y-4">
              {METRICS.map((metric) => (
                <div key={metric.label}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{metric.label}</span>
                    <span className="font-medium tabular-nums">{metric.value}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-secondary">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${metric.value}%`, backgroundColor: metric.color }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Reveal>
      </div>
    </section>
  );
}
