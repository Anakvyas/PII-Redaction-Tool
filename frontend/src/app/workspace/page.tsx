"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Loader2, ScanSearch } from "lucide-react";
import { toast } from "sonner";
import { api, ApiRequestError } from "@/lib/api";
import { ALL_PII_TYPES, type DocumentOut, type JobOut, type PIIType, type PolicyOut } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dropzone } from "@/components/workspace/dropzone";
import { PolicySelect } from "@/components/workspace/policy-select";
import { PiiTypePicker } from "@/components/workspace/pii-type-picker";
import { JobList } from "@/components/jobs/job-list";
import { Reveal } from "@/components/landing/reveal";

export default function WorkspacePage() {
  const router = useRouter();

  const [file, setFile] = React.useState<File | null>(null);
  const [policies, setPolicies] = React.useState<PolicyOut[]>([]);
  const [policyId, setPolicyId] = React.useState<string | null>(null);
  const [piiTypes, setPiiTypes] = React.useState<PIIType[]>(ALL_PII_TYPES);
  const [submitting, setSubmitting] = React.useState(false);

  const [jobs, setJobs] = React.useState<JobOut[]>([]);
  const [documentsById, setDocumentsById] = React.useState<Record<string, DocumentOut>>({});
  const [loadingJobs, setLoadingJobs] = React.useState(true);

  const loadJobs = React.useCallback(async () => {
    try {
      const list = await api.jobs.list();
      setJobs(list);
      const uniqueDocIds = Array.from(new Set(list.map((j) => j.document_id)));
      const docs = await Promise.all(uniqueDocIds.map((id) => api.documents.get(id).catch(() => null)));
      const byId: Record<string, DocumentOut> = {};
      docs.forEach((doc) => {
        if (doc) byId[doc.id] = doc;
      });
      setDocumentsById(byId);
    } catch {
      // best-effort — an empty recent-jobs list just shows the empty state
    } finally {
      setLoadingJobs(false);
    }
  }, []);

  React.useEffect(() => {
    api.policies
      .list()
      .then((list) => {
        setPolicies(list);
        setPolicyId((current) => current ?? list[0]?.id ?? null);
      })
      .catch(() => toast.error("Could not load redaction policies."));
    // eslint-disable-next-line react-hooks/set-state-in-effect -- standard fetch-on-mount; loadJobs's setState calls all happen after its internal await.
    loadJobs();
  }, [loadJobs]);

  async function handleStart() {
    if (!file || !policyId || piiTypes.length === 0) return;
    setSubmitting(true);
    try {
      const document = await api.documents.upload(file);
      const job = await api.jobs.create({ document_id: document.id, policy_id: policyId, pii_types: piiTypes });
      toast.success(document.deduplicated ? "Matched an existing document — reusing it." : "Document uploaded.");
      router.push(`/workspace/jobs/${job.id}`);
    } catch (err) {
      const message = err instanceof ApiRequestError ? err.message : "Something went wrong starting the job.";
      toast.error(message);
      setSubmitting(false);
    }
  }

  const canStart = Boolean(file && policyId && piiTypes.length > 0 && !submitting);

  return (
    <div className="mx-auto max-w-5xl px-4 py-14 sm:px-6 lg:px-8">
      <Reveal>
        <h1 className="text-3xl font-semibold tracking-tight">Workspace</h1>
        <p className="mt-2 max-w-xl text-muted-foreground">
          Upload a document, pick a policy and the PII types to look for, then let the detection engine take a
          pass.
        </p>
      </Reveal>

      <Reveal delay={0.05}>
        <Card className="mt-8 gap-6 rounded-2xl border-border/70 p-6 sm:p-8">
          <div>
            <label className="mb-2 block text-sm font-medium">Document</label>
            <Dropzone file={file} onFileSelected={setFile} onFileCleared={() => setFile(null)} disabled={submitting} />
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium">Redaction policy</label>
              <PolicySelect policies={policies} value={policyId} onChange={setPolicyId} />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium">PII types to detect</label>
            <PiiTypePicker selected={piiTypes} onChange={setPiiTypes} />
          </div>

          <div className="flex justify-end">
            <motion.div whileTap={{ scale: 0.97 }}>
              <Button size="lg" disabled={!canStart} onClick={handleStart} className="gap-2 px-6">
                {submitting ? <Loader2 className="size-4 animate-spin" /> : <ScanSearch className="size-4" />}
                {submitting ? "Starting…" : "Start detection"}
              </Button>
            </motion.div>
          </div>
        </Card>
      </Reveal>

      <Reveal delay={0.1} className="mt-14">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold tracking-tight">Recent jobs</h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setLoadingJobs(true);
              loadJobs();
            }}
            disabled={loadingJobs}
          >
            Refresh
          </Button>
        </div>
        <JobList jobs={jobs} documentsById={documentsById} />
      </Reveal>
    </div>
  );
}
