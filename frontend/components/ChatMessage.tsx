"use client";

import { useState } from "react";
import type { Citation } from "@/lib/api";

interface Props {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
}

export default function ChatMessage({ role, content, citations, isStreaming }: Props) {
  const [citationsOpen, setCitationsOpen] = useState(false);
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[80%] ${isUser ? "order-1" : ""}`}>
        <div
          className={`rounded-lg px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-slate-950 text-white"
              : "border border-slate-200 bg-white text-slate-900"
          }`}
        >
          <span style={{ whiteSpace: "pre-wrap" }}>{content}</span>
          {isStreaming && (
            <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-current opacity-70" />
          )}
        </div>

        {!isUser && citations && citations.length > 0 && (
          <div className="mt-1">
            <button
              onClick={() => setCitationsOpen((o) => !o)}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              {citationsOpen ? "Hide" : "Show"} {citations.length} source
              {citations.length !== 1 ? "s" : ""}
            </button>
            {citationsOpen && (
              <div className="mt-1 space-y-1">
                {citations.map((c) => (
                  <div
                    key={c.id}
                    className="rounded-md border border-slate-100 bg-slate-50 px-3 py-1.5 text-xs text-slate-600"
                  >
                    <span className="font-medium">{c.filename}</span>
                    {c.page_start && (
                      <span className="ml-1 text-slate-400">
                        · p. {c.page_start}
                        {c.page_end && c.page_end !== c.page_start ? `–${c.page_end}` : ""}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
