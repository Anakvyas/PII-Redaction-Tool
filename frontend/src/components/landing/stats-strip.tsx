import { Reveal } from "@/components/landing/reveal";

const STATS = [
  { value: "9", label: "PII entity types detected" },
  { value: "4", label: "Detection engines fused" },
  { value: "100%", label: "Formatting preserved" },
  { value: "0", label: "Duplicate name mappings" },
];

export function StatsStrip() {
  return (
    <section className="border-y border-border/60 bg-secondary/30">
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-8 px-4 py-12 sm:px-6 md:grid-cols-4 lg:px-8">
        {STATS.map((stat, i) => (
          <Reveal key={stat.label} delay={i * 0.08} className="text-center md:text-left">
            <div className="text-3xl font-semibold tracking-tight sm:text-4xl">{stat.value}</div>
            <div className="mt-1 text-sm text-muted-foreground">{stat.label}</div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
