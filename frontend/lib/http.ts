const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
let csrfToken = "";

export function setCsrfToken(token: string) {
  csrfToken = token;
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const method = (init.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && !csrfToken) {
    const bootstrap = await fetch(`${API_BASE_URL}/api/auth/csrf`, { credentials: "include", cache: "no-store" });
    if (!bootstrap.ok) throw new Error("Unable to initialize a secure session.");
    csrfToken = String((await bootstrap.json()).csrf_token);
  }
  const headers = new Headers(init.headers);
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) headers.set("X-CSRF-Token", csrfToken);
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers, credentials: "include" });
  if (response.status === 401 && typeof window !== "undefined") {
    csrfToken = "";
    window.dispatchEvent(new Event("claimops:session-expired"));
  }
  return response;
}
