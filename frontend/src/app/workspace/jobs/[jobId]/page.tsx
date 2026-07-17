"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { AlertTriangle, FileJson, FileSpreadsheet, FileText, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, ApiRequestError, resolveFileUrl } from "@/lib/api";
import type { DocumentOut, JobDetailOut, PIIType, ReviewDecision } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { JobStatusBadge } from "@/components/jobs/job-status-badge";
import { JobStepper } from "@/components/jobs/job-stepper";
import { DetectionReviewList } from "@/components/jobs/detection-review-list";
import { RedactionSummary } from "@/components/jobs/redaction-summary";
import { DownloadCard } from "@/components/jobs/download-card";
import { Reveal } from "@/components/landing/reveal";

// react-pdf touches browser-only globals (DOMMatrix) at import time, so the whole
// preview tree must never be evaluated during SSR — only after client hydration.
const DocumentPreview = dynamic(
  () => import("@/components/preview/document-preview").then((m) => m.DocumentPreview),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center gap-2 py-24 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Loading preview…
      </div>
    ),
  },
);

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();

  const [job, setJob] = React.useState<JobDetailOut | null>(null);
  const [document, setDocument] = React.useState<DocumentOut | null>(null);
  const [originalUrl, setOriginalUrl] = React.useState<string | null>(null);
  const [redactedUrl, setRedactedUrl] = React.useState<string | null>(null);
  const [mapUrl, setMapUrl] = React.useState<string | null>(null);
  const [auditUrl, setAuditUrl] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [redacting, setRedacting] = React.useState(false);
  const [activeHighlightId, setActiveHighlightId] = React.useState<string | null>(null);
  const [tab, setTab] = React.useState("original");
  // Default matches the backend's own auto-approval floor (see
  // DEFAULT_CONFIDENCE_FLOOR) — hides the low-confidence noise (e.g. "Offer",
  // "SEBI" tagged as a company at ~30%) by default, but the user can lower
  // it to see everything, or raise it to see only the most confident hits.
  const [minConfidence, setMinConfidence] = React.useState(0.75);

  const refresh = React.useCallback(async () => {
    const detail = await api.jobs.get(jobId);
    setJob(detail);
    return detail;
  }, [jobId]);

  React.useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const detail = await refresh();
        const doc = await api.documents.get(detail.document_id);
        if (cancelled) return;
        setDocument(doc);
        const download = await api.documents.downloadUrl(doc.id);
        if (!cancelled) setOriginalUrl(resolveFileUrl(download));
      } catch {
        toast.error("Could not load this job.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [jobId, refresh]);

  // Live-updates while the background detection task is running.
  React.useEffect(() => {
    if (!job || !["queued", "detecting"].includes(job.status)) return;

    const source = new EventSource(api.jobs.streamUrl(jobId));
    source.onmessage = () => {
      refresh().catch(() => undefined);
    };
    source.onerror = () => {
      source.close();
    };
    return () => source.close();
  }, [job, jobId, refresh]);

  // Once completed, load the redacted file + report artifact links.
  React.useEffect(() => {
    if (!job || job.status !== "completed") return;
    let cancelled = false;

    (async () => {
      try {
        const [download, artifacts] = await Promise.all([api.jobs.downloadUrl(jobId), api.jobs.artifacts(jobId)]);
        if (cancelled) return;
        setRedactedUrl(resolveFileUrl(download));
        if (artifacts.replacement_map) setMapUrl(resolveFileUrl(artifacts.replacement_map));
        if (artifacts.audit_log) setAuditUrl(resolveFileUrl(artifacts.audit_log));
        setTab("redacted");
      } catch {
        toast.error("Job completed, but the download links could not be loaded.");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [job, jobId]);

  async function handleReview(detectionId: string, decision: ReviewDecision, newType?: PIIType) {
    if (!job) return;
    const previous = job.detections;
    setJob({
      ...job,
      detections: job.detections.map((d) =>
        d.id === detectionId ? { ...d, human_decision: decision, human_verified: true, new_pii_type: newType ?? null } : d,
      ),
    });
    try {
      await api.jobs.reviewDetection(jobId, detectionId, decision, newType);
    } catch {
      setJob({ ...job, detections: previous });
      toast.error("Couldn't save that review decision.");
    }
  }

  async function handleRedact() {
    if (!job) return;
    setRedacting(true);
    try {
      const result = await api.jobs.redact(jobId);
      setJob({ ...job, ...result });
      toast.success("Document redacted.");
    } catch (err) {
      const message = err instanceof ApiRequestError ? err.message : "Redaction failed.";
      toast.error(message);
    } finally {
      setRedacting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-32 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" /> Loading job…
      </div>
    );
  }

  if (!job) {
    return <div className="py-32 text-center text-muted-foreground">Job not found.</div>;
  }

  const reviewable = job.status === "needs_review";
  const canRedact = reviewable && job.detections.length >= 0;

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
      <Reveal>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-muted-foreground">{document?.filename}</p>
            <h1 className="text-2xl font-semibold tracking-tight">Redaction job</h1>
          </div>
          <JobStatusBadge status={job.status} className="text-sm" />
        </div>

        {job.status !== "failed" && (
          <div className="mt-8">
            <JobStepper status={job.status} />
          </div>
        )}

        {job.status === "failed" && job.error && (
          <div className="mt-6 flex items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <p>{job.error}</p>
          </div>
        )}
      </Reveal>

      {(job.status === "queued" || job.status === "detecting") && (
        <Reveal delay={0.1} className="mt-16 flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
          <Loader2 className="size-6 animate-spin text-primary" />
          <p>Running detection across the document — this usually takes a few seconds.</p>
        </Reveal>
      )}

      {job.detections.length >= 0 && job.status !== "queued" && job.status !== "detecting" && document && originalUrl && (
        <Reveal delay={0.1} className="mt-10 grid gap-8 lg:grid-cols-[1fr_380px]">
          <div>
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                <TabsTrigger value="original">Original</TabsTrigger>
                <TabsTrigger value="redacted" disabled={!redactedUrl}>
                  Redacted
                </TabsTrigger>
              </TabsList>
              <TabsContent value="original" className="mt-4">
                <DocumentPreview
                  format={document.format}
                  fileUrl={originalUrl}
                  detections={job.detections}
                  activeHighlightId={activeHighlightId}
                  onHighlightHover={setActiveHighlightId}
                />
              </TabsContent>
              <TabsContent value="redacted" className="mt-4">
                {redactedUrl && <DocumentPreview format={document.format} fileUrl={redactedUrl} detections={[]} />}
              </TabsContent>
            </Tabs>
          </div>

          <div className="space-y-6">
            {job.status === "needs_review" && (
              <Card className="gap-3 rounded-2xl border-border/70 p-4">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold">Review detections</h2>
                  <span className="text-xs text-muted-foreground">{job.detections.length} found</span>
                </div>
                <div className="max-h-[520px] overflow-y-auto pr-1">
                  <DetectionReviewList
                    detections={job.detections}
                    activeId={activeHighlightId}
                    onHover={setActiveHighlightId}
                    onReview={handleReview}
                  />
                </div>
                <motion.div whileTap={{ scale: 0.97 }}>
                  <Button className="mt-1 w-full gap-2" disabled={!canRedact || redacting} onClick={handleRedact}>
                    {redacting ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                    {redacting ? "Redacting…" : "Redact document"}
                  </Button>
                </motion.div>
              </Card>
            )}

            {job.status === "redacting" && (
              <Card className="items-center gap-2 rounded-2xl border-border/70 p-6 text-center text-muted-foreground">
                <Loader2 className="size-5 animate-spin text-primary" />
                <p className="text-sm">Applying redactions…</p>
              </Card>
            )}

            {job.status === "completed" && job.summary && (
              <>
                <Card className="gap-3 rounded-2xl border-border/70 p-4">
                  <h2 className="font-semibold">Summary</h2>
                  <RedactionSummary
                    countsByType={job.summary.counts_by_type}
                    totalRedacted={job.summary.total_redacted}
                  />
                </Card>

                <div className="space-y-2.5">
                  {redactedUrl && (
                    <DownloadCard
                      icon={FileText}
                      title="Redacted document"
                      description={`${document.filename} (redacted)`}
                      href={redactedUrl}
                      filename={document.filename}
                    />
                  )}
                  {mapUrl && (
                    <DownloadCard
                      icon={FileJson}
                      title="replacement_map.json"
                      description="Original → replacement mapping"
                      href={mapUrl}
                      filename="replacement_map.json"
                    />
                  )}
                  {auditUrl && (
                    <DownloadCard
                      icon={FileSpreadsheet}
                      title="audit_log.json"
                      description="Full per-entity audit trail"
                      href={auditUrl}
                      filename="audit_log.json"
                    />
                  )}
                </div>
              </>
            )}

            {!reviewable && job.status !== "completed" && job.status !== "redacting" && job.detections.length > 0 && (
              <Card className="gap-3 rounded-2xl border-border/70 p-4">
                <h2 className="font-semibold">Detections</h2>
                <div className="max-h-[520px] overflow-y-auto pr-1">
                  <DetectionReviewList
                    detections={job.detections}
                    activeId={activeHighlightId}
                    onHover={setActiveHighlightId}
                    onReview={() => undefined}
                    readOnly
                  />
                </div>
              </Card>
            )}
          </div>
        </Reveal>
      )}
    </div>
  );
}
