"use client";

import { useRef, useState } from "react";
import { uploadDocument, type Document } from "@/lib/api";

interface Props {
  token: string;
  onUploaded: (doc: Document) => void;
}

const ALLOWED_TYPES = new Set(["application/pdf", "text/plain", "text/markdown"]);
const MAX_SIZE_MB = 50;

export default function DocumentUpload({ token, onUploaded }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function validate(f: File): string | null {
    if (!ALLOWED_TYPES.has(f.type)) return "Only PDF, TXT, and Markdown files are supported.";
    if (f.size / (1024 * 1024) > MAX_SIZE_MB) return `File must be under ${MAX_SIZE_MB} MB.`;
    return null;
  }

  function selectFile(f: File) {
    const err = validate(f);
    if (err) { setError(err); setFile(null); return; }
    setError(null);
    setFile(f);
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const doc = await uploadDocument(file, token);
      onUploaded(doc);
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const f = e.dataTransfer.files[0];
          if (f) selectFile(f);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed px-4 py-6 transition-colors ${
          dragging ? "border-slate-500 bg-slate-50" : "border-slate-300 bg-white hover:border-slate-400"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.md,text/plain,text/markdown,application/pdf"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) selectFile(f); }}
        />
        {file ? (
          <div className="text-center">
            <p className="text-sm font-medium text-slate-800">{file.name}</p>
            <p className="mt-0.5 text-xs text-slate-500">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
          </div>
        ) : (
          <div className="text-center">
            <p className="text-sm text-slate-500">Drop a file or click to browse</p>
            <p className="mt-0.5 text-xs text-slate-400">PDF, TXT, Markdown · max {MAX_SIZE_MB} MB</p>
          </div>
        )}
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}

      {file && (
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="w-full rounded-md bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {uploading ? "Uploading…" : "Upload"}
        </button>
      )}
    </div>
  );
}
