"use client";

import { useState } from "react";
import type { Document } from "@/lib/api";
import StatusBadge from "./StatusBadge";

interface Props {
  documents: Document[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onDelete: (id: string) => void;
  onRetry: (id: string) => void;
}

function relativeTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function DocumentList({
  documents,
  selectedIds,
  onSelectionChange,
  onDelete,
  onRetry,
}: Props) {
  const [confirmId, setConfirmId] = useState<string | null>(null);

  function toggleSelect(id: string) {
    onSelectionChange(
      selectedIds.includes(id) ? selectedIds.filter((x) => x !== id) : [...selectedIds, id]
    );
  }

  if (documents.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-slate-400">No documents yet. Upload one above.</p>
    );
  }

  return (
    <ul className="space-y-2">
      {documents.map((doc) => (
        <li key={doc.id} className="rounded-md border border-slate-200 bg-white p-3">
          <div className="flex items-start gap-2">
            <input
              type="checkbox"
              checked={selectedIds.includes(doc.id)}
              onChange={() => toggleSelect(doc.id)}
              className="mt-0.5 h-4 w-4 accent-slate-950"
              title="Filter chat to this document"
            />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-800" title={doc.filename}>
                {doc.filename}
              </p>
              <div className="mt-1 flex items-center gap-2">
                <StatusBadge status={doc.status} />
                <span className="text-xs text-slate-400">{relativeTime(doc.created_at)}</span>
              </div>
              {doc.status === "failed" && doc.error_reason && (
                <p className="mt-1 truncate text-xs text-red-600" title={doc.error_reason}>
                  {doc.error_reason}
                </p>
              )}
            </div>

            <div className="flex shrink-0 items-center gap-1">
              {doc.status === "failed" && (
                <button
                  onClick={() => onRetry(doc.id)}
                  className="rounded px-2 py-0.5 text-xs font-medium text-blue-600 hover:bg-blue-50"
                >
                  Retry
                </button>
              )}
              {confirmId === doc.id ? (
                <>
                  <button
                    onClick={() => { onDelete(doc.id); setConfirmId(null); }}
                    className="rounded px-2 py-0.5 text-xs font-medium text-red-600 hover:bg-red-50"
                  >
                    Confirm
                  </button>
                  <button
                    onClick={() => setConfirmId(null)}
                    className="rounded px-2 py-0.5 text-xs text-slate-500 hover:bg-slate-100"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setConfirmId(doc.id)}
                  className="rounded px-2 py-0.5 text-xs text-slate-400 hover:bg-slate-100 hover:text-red-500"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
