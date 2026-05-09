const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type DocumentStatus = "uploaded" | "processing" | "ready" | "failed";

export interface Document {
  id: string;
  filename: string;
  mime_type: string;
  status: DocumentStatus;
  page_count: number | null;
  error_reason: string | null;
  created_at: string;
}

export interface DocumentDetail extends Document {
  chunk_count: number;
}

export interface ChatSession {
  session_id: string;
  title: string | null;
  created_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface SessionDetail {
  session_id: string;
  title: string | null;
  created_at: string;
  messages: ChatMessage[];
}

export interface Citation {
  id: string;
  filename: string;
  page_start: string;
  page_end: string;
}

export interface AuthResult {
  session_token: string;
  user_id: string;
  email: string;
}

export interface StreamCallbacks {
  onToken: (delta: string) => void;
  onDone: (citations: Citation[], messageId: string) => void;
  onError: (err: string) => void;
}

function authHeaders(token: string): HeadersInit {
  return { "X-Session-Token": token, "Content-Type": "application/json" };
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<AuthResult> {
  return request("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function register(email: string, password: string): Promise<AuthResult> {
  return request("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(token: string): Promise<void> {
  await fetch(`${BASE_URL}/auth/logout`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function uploadDocument(file: File, token: string): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/documents`, {
    method: "POST",
    headers: { "X-Session-Token": token },
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `Upload failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function listDocuments(token: string): Promise<Document[]> {
  return request("/documents", { headers: authHeaders(token) });
}

export async function getDocument(id: string, token: string): Promise<DocumentDetail> {
  return request(`/documents/${id}`, { headers: authHeaders(token) });
}

export async function deleteDocument(id: string, token: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/documents/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!res.ok && res.status !== 204) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `Delete failed: HTTP ${res.status}`);
  }
}

export async function retryDocument(id: string, token: string): Promise<Document> {
  return request(`/documents/${id}/retry`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function createSession(token: string): Promise<ChatSession> {
  return request("/chat/sessions", {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function listSessions(token: string): Promise<ChatSession[]> {
  return request("/chat/sessions", { headers: authHeaders(token) });
}

export async function getSession(id: string, token: string): Promise<SessionDetail> {
  return request(`/chat/sessions/${id}`, { headers: authHeaders(token) });
}

export function streamMessage(
  sessionId: string,
  message: string,
  documentIds: string[],
  token: string,
  callbacks: StreamCallbacks
): () => void {
  let cancelled = false;
  let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

  (async () => {
    try {
      const res = await fetch(`${BASE_URL}/chat/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify({ message, document_ids: documentIds }),
      });

      if (!res.ok || !res.body) {
        const body = await res.json().catch(() => ({}));
        callbacks.onError(body?.detail ?? `HTTP ${res.status}`);
        return;
      }

      reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!cancelled) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") return;

          try {
            const event = JSON.parse(payload);
            if (event.type === "token") {
              callbacks.onToken(event.content as string);
            } else if (event.type === "done") {
              callbacks.onDone(event.citations as Citation[], event.message_id as string);
            } else if (event.type === "error") {
              callbacks.onError(event.detail as string);
            }
          } catch {
            // Ignore malformed SSE frames
          }
        }
      }
    } catch (err) {
      if (!cancelled) {
        callbacks.onError(err instanceof Error ? err.message : "Unknown error");
      }
    }
  })();

  return () => {
    cancelled = true;
    reader?.cancel();
  };
}
