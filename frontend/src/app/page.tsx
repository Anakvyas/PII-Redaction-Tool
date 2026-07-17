import { Hero } from "@/components/landing/hero";
import { StatsStrip } from "@/components/landing/stats-strip";
import { Features } from "@/components/landing/features";
import { HowItWorks } from "@/components/landing/how-it-works";
import { EvaluationTeaser } from "@/components/landing/evaluation-teaser";
import { CtaBanner } from "@/components/landing/cta-banner";

export default function Home() {
  return (
    <div className="flex flex-col">
      <Hero />
      <StatsStrip />
      <Features />
      <HowItWorks />
      <EvaluationTeaser />
      <CtaBanner />
    </div>
  );
}
