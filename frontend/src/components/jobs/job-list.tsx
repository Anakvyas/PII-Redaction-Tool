"use client";

import Link from "next/link";
import { ArrowUpRight, FileText } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { JobStatusBadge } from "@/components/jobs/job-status-badge";
import { formatRelative } from "@/lib/format";
import type { DocumentOut, JobOut } from "@/lib/types";

export function JobList({
  jobs,
  documentsById,
}: {
  jobs: JobOut[];
  documentsById: Record<string, DocumentOut>;
}) {
  if (jobs.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border py-16 text-center text-sm text-muted-foreground">
        No jobs yet. Upload a document above to get started.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border/70">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Document</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>PII types</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">&nbsp;</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.map((job) => {
            const document = documentsById[job.document_id];
            return (
              <TableRow key={job.id}>
                <TableCell className="max-w-64 truncate font-medium">
                  <span className="flex items-center gap-2">
                    <FileText className="size-4 shrink-0 text-muted-foreground" />
                    <span className="truncate">{document?.filename ?? job.document_id}</span>
                  </span>
                </TableCell>
                <TableCell>
                  <JobStatusBadge status={job.status} />
                </TableCell>
                <TableCell className="text-muted-foreground">{job.pii_types.length} types</TableCell>
                <TableCell className="text-muted-foreground">{formatRelative(job.created_at)}</TableCell>
                <TableCell className="text-right">
                  <Link
                    href={`/workspace/jobs/${job.id}`}
                    className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                  >
                    View <ArrowUpRight className="size-3.5" />
                  </Link>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
