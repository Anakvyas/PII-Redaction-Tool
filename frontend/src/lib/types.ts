/** Mirrors backend/schemas/*.py — keep in sync with the FastAPI response models. */

export type PIIType =
  | "person"
  | "email"
  | "phone"
  | "company"
  | "address"
  | "ssn"
  | "credit_card"
  | "dob"
  | "ip_address";

export const ALL_PII_TYPES: PIIType[] = [
  "person",
  "email",
  "phone",
  "company",
  "address",
  "ssn",
  "credit_card",
  "dob",
  "ip_address",
];

export type RedactionStrategy = "mask" | "pseudonymize" | "generalize" | "black_box";

export type DocumentFormat = "docx" | "pdf";

export type JobStatus =
  | "queued"
  | "detecting"
  | "needs_review"
  | "redacting"
  | "completed"
  | "failed";

export type ReviewDecision = "accept" | "reject" | "retype";

export interface TextSpan {
  start: number;
  end: number;
  page: number | null;
  bbox: [number, number, number, number] | null;
}

export interface DocumentOut {
  id: string;
  filename: string;
  format: DocumentFormat;
  mime_type: string;
  checksum: string;
  uploaded_at: string;
  deduplicated: boolean;
}

export interface DetectionOut {
  id: string;
  pii_type: PIIType;
  span: TextSpan;
  raw_value: string;
  confidence: number;
  source_detector: string;
  human_verified: boolean;
  human_decision: ReviewDecision | null;
  new_pii_type: PIIType | null;
}

export interface RedactionArtifactsOut {
  replacement_map: string | null;
  audit_log: string | null;
}

export interface RedactionSummaryOut {
  counts_by_type: Partial<Record<PIIType, number>>;
  total_redacted: number;
  artifacts: RedactionArtifactsOut | null;
}

export interface JobOut {
  id: string;
  document_id: string;
  policy_id: string;
  status: JobStatus;
  pii_types: PIIType[];
  error: string | null;
  summary: RedactionSummaryOut | null;
  created_at: string;
  completed_at: string | null;
}

export interface JobDetailOut extends JobOut {
  detections: DetectionOut[];
}

export interface DownloadOut {
  url: string;
  expires_in: number;
}

export interface ArtifactDownloadOut {
  replacement_map: DownloadOut | null;
  audit_log: DownloadOut | null;
}

export interface PolicyOut {
  id: string;
  name: string;
  strategy_map: Partial<Record<PIIType, RedactionStrategy>>;
  confidence_floor: number;
  created_at: string;
}

export interface PIITypeInfo {
  pii_type: PIIType;
  detectors: string[];
  example: string;
}

export interface EvaluationMetricsOut {
  precision: number;
  recall: number;
  f1: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
}

export interface EvaluationRunOut {
  id: string;
  dataset_id: string;
  detector_version: string;
  overall: EvaluationMetricsOut;
  per_type: Partial<Record<PIIType, EvaluationMetricsOut>>;
  started_at: string;
  completed_at: string;
}

/** replacement_map.json artifact content, written by replacement/faker_engine.py */
export interface ReplacementMapFile {
  generated_at: string;
  mapping_count: number;
  mappings: { pii_type: PIIType; original: string; replacement: string }[];
}

/** audit_log.json artifact content, written by replacement/faker_engine.py */
export interface AuditLogFile {
  generated_at: string;
  event_count: number;
  events: {
    entity_id: string;
    pii_type: PIIType;
    original: string;
    replacement: string;
    span: { start: number; end: number; page: number | null; bbox: number[] | null };
    source_detector: string;
    confidence: number;
  }[];
}

export interface ApiError {
  error: string;
  message: string;
  request_id: string;
}
