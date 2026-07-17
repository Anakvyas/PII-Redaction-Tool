"use client";

import * as React from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { motion } from "framer-motion";
import { File as FileIcon, UploadCloud, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatBytes } from "@/lib/format";
import { Button } from "@/components/ui/button";

const ACCEPT = {
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/pdf": [".pdf"],
};

const MAX_SIZE = 25 * 1024 * 1024;

export function Dropzone({
  file,
  onFileSelected,
  onFileCleared,
  disabled,
}: {
  file: File | null;
  onFileSelected: (file: File) => void;
  onFileCleared: () => void;
  disabled?: boolean;
}) {
  const [error, setError] = React.useState<string | null>(null);

  const onDrop = React.useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      if (rejected.length > 0) {
        setError(rejected[0]?.errors[0]?.message ?? "That file can't be used.");
        return;
      }
      setError(null);
      if (accepted[0]) onFileSelected(accepted[0]);
    },
    [onFileSelected],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    maxSize: MAX_SIZE,
    multiple: false,
    disabled,
  });

  if (file) {
    return (
      <div className="flex items-center gap-4 rounded-2xl border border-border/70 bg-card px-5 py-4">
        <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <FileIcon className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{file.name}</p>
          <p className="text-xs text-muted-foreground">{formatBytes(file.size)}</p>
        </div>
        {!disabled && (
          <Button variant="ghost" size="icon" onClick={onFileCleared} aria-label="Remove file">
            <X className="size-4" />
          </Button>
        )}
      </div>
    );
  }

  return (
    <div>
      <div
        {...getRootProps()}
        className={cn(
          "group relative cursor-pointer overflow-hidden rounded-2xl border-2 border-dashed border-border bg-secondary/20 px-6 py-14 text-center transition-colors",
          isDragActive && "border-primary bg-primary/5",
          disabled && "pointer-events-none opacity-60",
        )}
      >
        <input {...getInputProps()} />
        <motion.div
          animate={isDragActive ? { y: -4, scale: 1.05 } : { y: 0, scale: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary"
        >
          <UploadCloud className="size-6" />
        </motion.div>
        <p className="mt-5 text-base font-medium">
          {isDragActive ? "Drop it right here" : "Drag & drop a DOCX or PDF"}
        </p>
        <p className="mt-1.5 text-sm text-muted-foreground">or click to browse — up to 25MB</p>
      </div>
      {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
    </div>
  );
}
