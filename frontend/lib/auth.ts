const AUTH_KEY = "rag_auth";

export interface AuthState {
  sessionToken: string;
  userId: string;
  email: string;
}

export function saveAuth(data: AuthState): void {
  localStorage.setItem(AUTH_KEY, JSON.stringify(data));
}

export function loadAuth(): AuthState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    return raw ? (JSON.parse(raw) as AuthState) : null;
  } catch {
    return null;
  }
}

export function clearAuth(): void {
  localStorage.removeItem(AUTH_KEY);
}
