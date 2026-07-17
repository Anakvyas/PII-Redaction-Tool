export interface PreviewHighlight {
  id: string;
  /** 0-indexed PDF page; null for DOCX (matched by text instead). */
  page: number | null;
  /** PDF word bbox in page-point space (top-left origin, matches PyMuPDF); null for DOCX. */
  bbox: [number, number, number, number] | null;
  /** Exact original text, used to locate occurrences in the DOCX preview HTML. */
  rawValue: string;
  color: string;
  label: string;
}
