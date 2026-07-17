import { ClipboardCheck, FileClock, ScanSearch, ShieldCheck, SlidersHorizontal, Wand2 } from "lucide-react";
import { Reveal } from "@/components/landing/reveal";
import { Card } from "@/components/ui/card";

const FEATURES = [
  {
    icon: ScanSearch,
    title: "Multi-engine detection",
    description:
      "Regex, spaCy NER, and Microsoft Presidio run together with fuzzy and date heuristics, then corroboration boosting resolves overlaps into one confident call per entity.",
  },
  {
    icon: ShieldCheck,
    title: "Format-preserving redaction",
    description:
      "DOCX runs keep their font, bold, italic, and underline; tables, headers, footers, and hyperlinks are untouched. PDF redaction strips glyphs from the content stream, not a painted box.",
  },
  {
    icon: ClipboardCheck,
    title: "Human-in-the-loop review",
    description:
      "Every detection is accept, reject, or retype before it ships. Nothing gets redacted unless a policy or a reviewer approved it.",
  },
  {
    icon: Wand2,
    title: "Realistic pseudonymization",
    description:
      "Faker-backed replacements keep a stable mapping — every occurrence of a name becomes the same fake name, and linked emails, phones, and addresses stay consistent with it.",
  },
  {
    icon: SlidersHorizontal,
    title: "Per-type policy engine",
    description:
      "Mask, pseudonymize, generalize, or black-box — configured independently per PII type, with a confidence floor that routes low-confidence hits to manual review.",
  },
  {
    icon: FileClock,
    title: "Full audit trail",
    description:
      "Every redaction job produces a replacement map and an audit log — original value, replacement, span, detector, and confidence — exportable as JSON, CSV, or PDF.",
  },
];

export function Features() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-24 sm:px-6 lg:px-8">
      <Reveal className="mx-auto max-w-2xl text-center">
        <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Built for documents that matter</h2>
        <p className="mt-4 text-muted-foreground text-pretty">
          Every piece of the pipeline is designed around one rule: the redacted file should look untouched, except
          for the parts that had to go.
        </p>
      </Reveal>

      <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((feature, i) => (
          <Reveal key={feature.title} delay={(i % 3) * 0.08}>
            <Card className="group h-full gap-3 rounded-2xl border-border/70 p-6 transition-all hover:-translate-y-1 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5">
              <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                <feature.icon className="size-5" />
              </div>
              <h3 className="mt-1 font-semibold">{feature.title}</h3>
              <p className="text-sm text-muted-foreground text-pretty">{feature.description}</p>
            </Card>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
