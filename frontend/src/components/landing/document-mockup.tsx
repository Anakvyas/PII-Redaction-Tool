"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { FileText } from "lucide-react";
import { PII_TYPE_COLORS, PII_TYPE_LABELS } from "@/lib/colors";
import type { PIIType } from "@/lib/types";

interface MockToken {
  text: string;
  pii?: PIIType;
}

const LINES: MockToken[][] = [
  [{ text: "Dear " }, { text: "Jane Doe", pii: "person" }, { text: ", thank you for your application." }],
  [{ text: "Reach her at " }, { text: "jane.doe@acme.com", pii: "email" }, { text: " or " }, { text: "98765 43210", pii: "phone" }, { text: "." }],
  [{ text: "Employer: " }, { text: "Initech Solutions Pvt. Ltd.", pii: "company" }],
  [{ text: "Address: " }, { text: "12 MG Road, Bengaluru, KA", pii: "address" }],
  [{ text: "DOB " }, { text: "14 Mar 1990", pii: "dob" }, { text: " · SSN " }, { text: "234-56-7890", pii: "ssn" }],
];

export function DocumentMockup() {
  const [redacted, setRedacted] = React.useState(false);

  React.useEffect(() => {
    const id = setInterval(() => setRedacted((v) => !v), 2600);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="relative mx-auto w-full max-w-md rounded-2xl border border-border/70 bg-card/80 shadow-2xl shadow-primary/10 backdrop-blur-xl">
      <div className="flex items-center gap-2 border-b border-border/70 px-4 py-3">
        <div className="flex gap-1.5">
          <span className="size-2.5 rounded-full bg-[#eb6864]" />
          <span className="size-2.5 rounded-full bg-[#eda100]" />
          <span className="size-2.5 rounded-full bg-[#1baf7a]" />
        </div>
        <div className="ml-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <FileText className="size-3.5" />
          offer_letter.docx
        </div>
        <motion.span
          key={redacted ? "redacted" : "original"}
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="ml-auto rounded-full border border-border/70 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-muted-foreground uppercase"
        >
          {redacted ? "Redacted" : "Original"}
        </motion.span>
      </div>

      <div className="space-y-3.5 px-5 py-6 text-[13px] leading-relaxed">
        {LINES.map((line, lineIdx) => (
          <p key={lineIdx} className="text-foreground/80">
            {line.map((token, tokenIdx) => {
              if (!token.pii) return <React.Fragment key={tokenIdx}>{token.text}</React.Fragment>;
              const hue = PII_TYPE_COLORS[token.pii];
              return (
                <span key={tokenIdx} className="relative inline-flex">
                  <motion.span
                    animate={{
                      backgroundColor: redacted ? "#0b0b0b" : `${hue.light}22`,
                      borderColor: redacted ? "#0b0b0b" : `${hue.light}55`,
                    }}
                    transition={{ duration: 0.5 }}
                    className="rounded-[4px] border px-1 py-px font-medium text-foreground"
                    title={PII_TYPE_LABELS[token.pii]}
                  >
                    {redacted ? " ".repeat(Math.max(4, token.text.length)) : token.text}
                  </motion.span>
                </span>
              );
            })}
          </p>
        ))}
      </div>

      <div className="flex items-center justify-between border-t border-border/70 px-5 py-3 text-xs text-muted-foreground">
        <span>{redacted ? "6 entities redacted" : "6 entities detected"}</span>
        <span className="flex items-center gap-1">
          <span className={`size-1.5 rounded-full ${redacted ? "bg-[#0ca30c]" : "bg-[#fab219]"}`} />
          {redacted ? "Ready to export" : "Awaiting review"}
        </span>
      </div>
    </div>
  );
}
