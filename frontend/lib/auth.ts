import { apiFetch, setCsrfToken } from "./http";

export type AuthSession = {
  tenantId: string;
  companyName: string;
  username: string;
  role: "uploader" | "reviewer" | "administrator";
  demo: boolean;
};
export type AuthResult = { ok: true; session: AuthSession } | { ok: false; message: string };

export async function loadSession(): Promise<AuthSession | null> {
  window.localStorage.removeItem("claimops.authSession");
  try {
    const response = await apiFetch("/api/me", { cache: "no-store" });
    return response.ok ? normalizeSession(await response.json()) : null;
  } catch { return null; }
}
export async function registerCompany(companyName: string, username: string, password: string): Promise<AuthResult> {
  return authRequest("/api/auth/register-company", { company_name: companyName, username, password });
}
export async function signInCompany(username: string, password: string): Promise<AuthResult> {
  return authRequest("/api/auth/sign-in", { username, password });
}
export async function signOutCompany() {
  const response = await apiFetch("/api/auth/sign-out", { method: "POST" });
  if (!response.ok) throw new Error("Sign out failed. Please try again.");
  setCsrfToken("");
  window.localStorage.removeItem("claimops.authSession");
}
async function authRequest(path: string, body: Record<string, string>): Promise<AuthResult> {
  try {
    const response = await apiFetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const payload = await response.json();
    if (!response.ok) return { ok: false, message: String(payload?.detail ?? "Authentication failed.") };
    return { ok: true, session: normalizeSession(payload) };
  } catch (exc) { return { ok: false, message: exc instanceof Error ? exc.message : "Authentication failed." }; }
}
function normalizeSession(payload: Record<string, unknown>): AuthSession {
  setCsrfToken(String(payload.csrf_token ?? ""));
  return { tenantId: String(payload.tenant_id), companyName: String(payload.company_name), username: String(payload.username), role: payload.role as AuthSession["role"], demo: Boolean(payload.demo) };
}
