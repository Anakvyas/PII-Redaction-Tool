import type { LucideIcon } from "lucide-react";
import { Download } from "lucide-react";

export function DownloadCard({
  icon: Icon,
  title,
  description,
  href,
  filename,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  href: string;
  filename?: string;
}) {
  return (
    <a
      href={href}
      download={filename}
      target={filename ? undefined : "_blank"}
      rel="noopener noreferrer"
      className="group flex items-center gap-3 rounded-xl border border-border/70 bg-card p-4 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
    >
      <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="size-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-medium">{title}</p>
        <p className="truncate text-xs text-muted-foreground">{description}</p>
      </div>
      <Download className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-primary" />
    </a>
  );
}
