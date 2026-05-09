import type { DocumentStatus } from "@/lib/api";

const STATUS_STYLES: Record<DocumentStatus, string> = {
  uploaded: "bg-slate-100 text-slate-600",
  processing: "bg-yellow-100 text-yellow-700 animate-pulse",
  ready: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<DocumentStatus, string> = {
  uploaded: "Uploaded",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

export default function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
