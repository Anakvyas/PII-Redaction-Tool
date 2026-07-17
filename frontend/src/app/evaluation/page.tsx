"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { FileSearch, Loader2, PlayCircle } from "lucide-react";
import { toast } from "sonner";
import { api, ApiRequestError } from "@/lib/api";
import type { AuditLogFile, EvaluationRunOut, JobOut } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Reveal } from "@/components/landing/reveal";
import { StatTile } from "@/components/evaluation/stat-tile";
import { MetricsBarChart } from "@/components/evaluation/metrics-bar-chart";
import { ConfusionBreakdownChart } from "@/components/evaluation/confusion-breakdown-chart";
import { RunHistoryList } from "@/components/evaluation/run-history-list";
import { AuditLogTable } from "@/components/evaluation/audit-log-table";
import { formatPercent } from "@/lib/format";

export default function EvaluationPage() {
  const [runs, setRuns] = React.useState<EvaluationRunOut[]>([]);
  const [selectedRunId, setSelectedRunId] = React.useState<string | null>(null);
  const [running, setRunning] = React.useState(false);

  const [completedJobs, setCompletedJobs] = React.useState<JobOut[]>([]);
  const [selectedJobId, setSelectedJobId] = React.useState<string | null>(null);
  const [auditLog, setAuditLog] = React.useState<AuditLogFile | null>(null);
  const [loadingAudit, setLoadingAudit] = React.useState(false);

  const selectedRun = runs.find((r) => r.id === selectedRunId) ?? null;

  React.useEffect(() => {
    api.jobs
      .list()
      .then((jobs) => setCompletedJobs(jobs.filter((j) => j.status === "completed")))
      .catch(() => undefined);
  }, []);

  async function runEvaluation() {
    setRunning(true);
    try {
      const run = await api.evaluation.createRun();
      setRuns((prev) => [run, ...prev]);
      setSelectedRunId(run.id);
    } catch (err) {
      const message = err instanceof ApiRequestError ? err.message : "Evaluation run failed.";
      toast.error(message);
    } finally {
      setRunning(false);
    }
  }

  async function loadAuditLog(jobId: string) {
    setSelectedJobId(jobId);
    setLoadingAudit(true);
    setAuditLog(null);
    try {
      const artifacts = await api.jobs.artifacts(jobId);
      if (!artifacts.audit_log) {
        toast.error("This job has no audit log artifact.");
        return;
      }
      const log = await api.artifacts.auditLog(artifacts.audit_log);
      setAuditLog(log);
    } catch {
      toast.error("Could not load the audit log for that job.");
    } finally {
      setLoadingAudit(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 lg:px-8">
      <Reveal className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Evaluation dashboard</h1>
          <p className="mt-2 max-w-xl text-muted-foreground">
            Score the detection pipeline against the bundled gold-standard dataset — precision, recall, F1, and a
            per-type breakdown of true/false positives and negatives.
          </p>
        </div>
        <motion.div whileTap={{ scale: 0.97 }}>
          <Button size="lg" className="gap-2" onClick={runEvaluation} disabled={running}>
            {running ? <Loader2 className="size-4 animate-spin" /> : <PlayCircle className="size-4" />}
            {running ? "Running…" : "Run evaluation"}
          </Button>
        </motion.div>
      </Reveal>

      {runs.length > 0 && (
        <Reveal delay={0.05} className="mt-8">
          <RunHistoryList runs={runs} selectedId={selectedRunId} onSelect={setSelectedRunId} />
        </Reveal>
      )}

      {!selectedRun && runs.length === 0 && (
        <Reveal delay={0.1} className="mt-14 flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border py-20 text-center text-muted-foreground">
          <FileSearch className="size-8" />
          <p>No evaluation runs yet. Run the bundled gold-standard evaluation to see metrics here.</p>
        </Reveal>
      )}

      {selectedRun && (
        <>
          <Reveal delay={0.1} className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatTile label="Precision" value={formatPercent(selectedRun.overall.precision)} tone="#2a78d6" />
            <StatTile label="Recall" value={formatPercent(selectedRun.overall.recall)} tone="#1baf7a" />
            <StatTile label="F1 score" value={formatPercent(selectedRun.overall.f1)} tone="#eda100" />
            <StatTile
              label="Entities scored"
              value={String(
                selectedRun.overall.true_positives + selectedRun.overall.false_negatives,
              )}
            />
          </Reveal>

          <Reveal delay={0.15} className="mt-6">
            <Card className="gap-4 rounded-2xl border-border/70 p-6">
              <h2 className="font-semibold">Precision · Recall · F1 by entity type</h2>
              <MetricsBarChart perType={selectedRun.per_type} />
            </Card>
          </Reveal>

          <Reveal delay={0.2} className="mt-6">
            <Card className="gap-4 rounded-2xl border-border/70 p-6">
              <h2 className="font-semibold">True / false positives &amp; negatives by type</h2>
              <ConfusionBreakdownChart perType={selectedRun.per_type} />
            </Card>
          </Reveal>
        </>
      )}

      <Reveal delay={0.25} className="mt-14">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">Audit log</h2>
            <p className="text-sm text-muted-foreground">Full redaction event trail for a completed job.</p>
          </div>
          <Select value={selectedJobId ?? undefined} onValueChange={(v) => loadAuditLog(v as string)}>
            <SelectTrigger className="w-64">
              <SelectValue placeholder="Choose a completed job" />
            </SelectTrigger>
            <SelectContent>
              {completedJobs.map((job) => (
                <SelectItem key={job.id} value={job.id}>
                  {job.id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {loadingAudit && (
          <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> Loading audit log…
          </div>
        )}

        {!loadingAudit && auditLog && <AuditLogTable log={auditLog} />}

        {!loadingAudit && !auditLog && completedJobs.length === 0 && (
          <div className="rounded-2xl border border-dashed border-border py-16 text-center text-sm text-muted-foreground">
            No completed redaction jobs yet — finish one in the workspace to see its audit trail here.
          </div>
        )}

        {!loadingAudit && !auditLog && completedJobs.length > 0 && (
          <div className="rounded-2xl border border-dashed border-border py-16 text-center text-sm text-muted-foreground">
            Pick a completed job above to load its audit log.
          </div>
        )}
      </Reveal>
    </div>
  );
}
