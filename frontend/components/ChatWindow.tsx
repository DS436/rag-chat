"use client";

import { useEffect, useRef, useState } from "react";
import { streamMessage, getSession, type Citation } from "@/lib/api";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import CitationPanel from "./CitationPanel";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
}

interface Props {
  token: string;
  sessionId: string;
  documentIds: string[];
}

export default function ChatWindow({ token, sessionId, documentIds }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [lastCitations, setLastCitations] = useState<Citation[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    let mounted = true;
    getSession(sessionId, token).then((detail) => {
      if (!mounted) return;
      setMessages(
        detail.messages.map((m) => ({ role: m.role, content: m.content }))
      );
    });
    return () => { mounted = false; };
  }, [sessionId, token]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSend(message: string) {
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setLastCitations([]);

    const placeholderIndex = messages.length + 1;
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", isStreaming: true },
    ]);
    setStreaming(true);

    cancelRef.current = streamMessage(sessionId, message, documentIds, token, {
      onToken(delta) {
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = { ...last, content: last.content + delta };
          }
          return next;
        });
      },
      onDone(citations) {
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = { ...last, isStreaming: false, citations };
          }
          return next;
        });
        setLastCitations(citations);
        setStreaming(false);
      },
      onError(err) {
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = {
              ...last,
              content: `Error: ${err}`,
              isStreaming: false,
            };
          }
          return next;
        });
        setStreaming(false);
      },
    });

    void placeholderIndex; // used implicitly via closure
  }

  useEffect(() => {
    return () => { cancelRef.current?.(); };
  }, []);

  return (
    <div className="flex min-h-[680px] flex-col rounded-md border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-5 py-4">
        <h2 className="text-base font-semibold text-slate-900">Chat</h2>
        {documentIds.length > 0 && (
          <p className="text-xs text-slate-400">
            Searching {documentIds.length} selected document{documentIds.length !== 1 ? "s" : ""}
          </p>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-5 py-4">
        {messages.length === 0 && (
          <div className="flex flex-1 items-center justify-center text-sm text-slate-400">
            Ask a question about your uploaded documents.
          </div>
        )}
        {messages.map((m, i) => (
          <ChatMessage
            key={i}
            role={m.role}
            content={m.content}
            citations={m.citations}
            isStreaming={m.isStreaming}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      <CitationPanel citations={lastCitations} />

      <div className="border-t border-slate-200 p-4">
        <ChatInput onSend={handleSend} disabled={streaming} />
      </div>
    </div>
  );
}
