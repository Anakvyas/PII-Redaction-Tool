import Link from "next/link";
import { ShieldCheck } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-border/60 bg-background">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-10 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <ShieldCheck className="size-4" />
          <span>Redactly &mdash; on-prem PII detection &amp; redaction.</span>
        </div>
        <div className="flex items-center gap-6 text-sm text-muted-foreground">
          <Link href="/workspace" className="hover:text-foreground transition-colors">
            Workspace
          </Link>
          <Link href="/evaluation" className="hover:text-foreground transition-colors">
            Evaluation
          </Link>
          <span className="text-muted-foreground/70">&copy; {new Date().getFullYear()}</span>
        </div>
      </div>
    </footer>
  );
}
