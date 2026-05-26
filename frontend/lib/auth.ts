export type AuthSession = {
  tenantId: string;
  companyName: string;
  username: string;
  token: string;
  demo: boolean;
};

export type AuthResult =
  | { ok: true; session: AuthSession }
  | { ok: false; message: string };

const SESSION_KEY = "claimops.authSession";
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export function loadSession(): AuthSession | null {
  const stored = window.localStorage.getItem(SESSION_KEY);
  if (!stored) {
    return null;
  }
  try {
    return JSON.parse(stored) as AuthSession;
  } catch {
    window.localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export async function registerCompany(companyName: string, username: string, password: string): Promise<AuthResult> {
  return authRequest("/api/auth/register-company", { company_name: companyName, username, password });
}

export async function signInCompany(username: string, password: string): Promise<AuthResult> {
  return authRequest("/api/auth/sign-in", { username, password });
}

export async function signOutCompany(token?: string) {
  if (token) {
    await fetch(`${API_BASE_URL}/api/auth/sign-out`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` }
    }).catch(() => undefined);
  }
  window.localStorage.removeItem(SESSION_KEY);
}

async function authRequest(path: string, body: Record<string, string>): Promise<AuthResult> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const payload = await response.json();
    if (!response.ok) {
      return { ok: false, message: String(payload?.detail ?? "Authentication failed.") };
    }
    const session = normalizeSession(payload);
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    return { ok: true, session };
  } catch (exc) {
    return { ok: false, message: exc instanceof Error ? exc.message : "Authentication failed." };
  }
}

function normalizeSession(payload: Record<string, unknown>): AuthSession {
  return {
    tenantId: String(payload.tenant_id ?? ""),
    companyName: String(payload.company_name ?? ""),
    username: String(payload.username ?? ""),
    token: String(payload.token ?? ""),
    demo: Boolean(payload.demo)
  };
}
