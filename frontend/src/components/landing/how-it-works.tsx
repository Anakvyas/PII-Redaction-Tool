import { CheckCheck, Eraser, ScanEye, UploadCloud } from "lucide-react";
import { Reveal } from "@/components/landing/reveal";

const STEPS = [
  {
    icon: UploadCloud,
    title: "Upload",
    description: "Drag in a DOCX or PDF. Files are deduplicated by checksum and validated against a size limit.",
  },
  {
    icon: ScanEye,
    title: "Detect & review",
    description:
      "Four detectors flag every PII span with a confidence score. Accept, reject, or retype each one before anything is redacted.",
  },
  {
    icon: Eraser,
    title: "Redact",
    description:
      "Approved detections are replaced in place per your policy — masked, generalized, black-boxed, or pseudonymized — with formatting untouched.",
  },
  {
    icon: CheckCheck,
    title: "Export & audit",
    description: "Download the redacted file plus a replacement map and audit log for full traceability.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-border/60 bg-secondary/20">
      <div className="mx-auto max-w-6xl px-4 py-24 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">From upload to audit, four steps</h2>
          <p className="mt-4 text-muted-foreground text-pretty">
            Nothing leaves the pipeline unreviewed, and nothing is redacted without a record of what changed.
          </p>
        </Reveal>

        <div className="relative mt-16 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div className="absolute top-6 right-0 left-0 hidden h-px bg-border lg:block" aria-hidden />
          {STEPS.map((step, i) => (
            <Reveal key={step.title} delay={i * 0.1} className="relative">
              <div className="relative z-10 flex size-12 items-center justify-center rounded-full border border-border bg-background shadow-sm">
                <step.icon className="size-5 text-primary" />
              </div>
              <div className="mt-5 flex items-baseline gap-2">
                <span className="text-sm font-medium text-muted-foreground">0{i + 1}</span>
                <h3 className="font-semibold">{step.title}</h3>
              </div>
              <p className="mt-2 text-sm text-muted-foreground text-pretty">{step.description}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
