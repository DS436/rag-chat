"use client";

import { useEffect, useRef, useState } from "react";
import {
  listDocuments,
  listSessions,
  createSession,
  deleteDocument,
  retryDocument,
  logout,
  type Document,
  type ChatSession,
} from "@/lib/api";
import { loadAuth, clearAuth, type AuthState } from "@/lib/auth";
import AuthForm from "@/components/AuthForm";
import DocumentUpload from "@/components/DocumentUpload";
import DocumentList from "@/components/DocumentList";
import ChatWindow from "@/components/ChatWindow";

const POLL_INTERVAL_MS = 3000;

function needsPolling(docs: Document[]): boolean {
  return docs.some((d) => d.status === "uploaded" || d.status === "processing");
}

export default function Home() {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [mounted, setMounted] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Avoid SSR mismatch — load auth client-side only
  useEffect(() => {
    setMounted(true);
    const saved = loadAuth();
    setAuth(saved);
  }, []);

  // Load data after auth is known
  useEffect(() => {
    if (!auth) return;
    void initData(auth.sessionToken);
  }, [auth]);

  // Poll for status changes while any doc is processing
  useEffect(() => {
    if (!auth || !needsPolling(documents)) {
      pollRef.current && clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      const docs = await listDocuments(auth.sessionToken).catch(() => []);
      setDocuments(docs);
      if (!needsPolling(docs)) {
        clearInterval(pollRef.current!);
      }
    }, POLL_INTERVAL_MS);
    return () => { pollRef.current && clearInterval(pollRef.current); };
  }, [auth, documents]);

  async function initData(token: string) {
    const [docs, sList] = await Promise.all([
      listDocuments(token).catch(() => [] as Document[]),
      listSessions(token).catch(() => [] as ChatSession[]),
    ]);
    setDocuments(docs);
    setSessions(sList);

    if (sList.length > 0) {
      setCurrentSessionId(sList[0].session_id);
    } else {
      const newSession = await createSession(token).catch(() => null);
      if (newSession) {
        setSessions([newSession]);
        setCurrentSessionId(newSession.session_id);
      }
    }
  }

  async function handleAuth(sessionToken: string, userId: string, email: string) {
    setAuth({ sessionToken, userId, email });
  }

  async function handleSignOut() {
    if (auth) await logout(auth.sessionToken).catch(() => {});
    clearAuth();
    setAuth(null);
    setDocuments([]);
    setSessions([]);
    setCurrentSessionId(null);
  }

  function handleUploaded(doc: Document) {
    setDocuments((prev) => [doc, ...prev]);
  }

  async function handleDelete(id: string) {
    if (!auth) return;
    await deleteDocument(id, auth.sessionToken).catch(() => {});
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    setSelectedIds((prev) => prev.filter((x) => x !== id));
  }

  async function handleRetry(id: string) {
    if (!auth) return;
    const updated = await retryDocument(id, auth.sessionToken).catch(() => null);
    if (updated) {
      setDocuments((prev) => prev.map((d) => (d.id === id ? updated : d)));
    }
  }

  async function handleNewChat() {
    if (!auth) return;
    const session = await createSession(auth.sessionToken).catch(() => null);
    if (session) {
      setSessions((prev) => [session, ...prev]);
      setCurrentSessionId(session.session_id);
    }
  }

  if (!mounted) return null;

  if (!auth) {
    return <AuthForm onAuth={handleAuth} />;
  }

  return (
    <main className="min-h-screen bg-[#f6f7f9] text-slate-950">
      <div className="mx-auto grid min-h-screen max-w-6xl grid-cols-1 gap-8 px-6 py-8 lg:grid-cols-[320px_1fr]">
        {/* Sidebar */}
        <aside className="flex flex-col gap-4 border-r border-slate-200 pr-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold">Knowledge Base</h1>
              <p className="text-xs text-slate-400">{auth.email}</p>
            </div>
            <button
              onClick={handleSignOut}
              className="rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-100"
            >
              Sign out
            </button>
          </div>

          <div className="space-y-1">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Upload</p>
            <DocumentUpload token={auth.sessionToken} onUploaded={handleUploaded} />
          </div>

          <div className="flex-1 space-y-1 overflow-y-auto">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
              Documents{selectedIds.length > 0 && ` · ${selectedIds.length} selected`}
            </p>
            <DocumentList
              documents={documents}
              selectedIds={selectedIds}
              onSelectionChange={setSelectedIds}
              onDelete={handleDelete}
              onRetry={handleRetry}
            />
          </div>

          {/* Session picker */}
          <div className="space-y-1 border-t border-slate-200 pt-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Sessions</p>
            <div className="flex gap-2">
              <select
                value={currentSessionId ?? ""}
                onChange={(e) => setCurrentSessionId(e.target.value)}
                className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm text-slate-800 outline-none"
              >
                {sessions.map((s) => (
                  <option key={s.session_id} value={s.session_id}>
                    {s.title ?? `Session ${s.session_id.slice(0, 8)}`}
                  </option>
                ))}
              </select>
              <button
                onClick={handleNewChat}
                className="rounded-md border border-slate-300 px-3 py-1 text-sm text-slate-700 hover:bg-slate-50"
              >
                New
              </button>
            </div>
          </div>
        </aside>

        {/* Chat area */}
        <section>
          {currentSessionId ? (
            <ChatWindow
              token={auth.sessionToken}
              sessionId={currentSessionId}
              documentIds={selectedIds}
            />
          ) : (
            <div className="flex min-h-[680px] items-center justify-center rounded-md border border-slate-200 bg-white text-sm text-slate-400">
              Create or select a session to start chatting.
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
