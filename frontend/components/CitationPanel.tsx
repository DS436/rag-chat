import type { Citation } from "@/lib/api";

interface Props {
  citations: Citation[];
}

export default function CitationPanel({ citations }: Props) {
  if (citations.length === 0) return null;

  return (
    <div className="border-t border-slate-100 px-5 py-3">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">Sources</p>
      <div className="flex flex-wrap gap-2">
        {citations.map((c) => (
          <div
            key={c.id}
            className="rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-700"
          >
            <span className="font-medium">{c.filename}</span>
            {c.page_start && (
              <span className="ml-1 text-slate-400">
                p. {c.page_start}
                {c.page_end && c.page_end !== c.page_start ? `–${c.page_end}` : ""}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
