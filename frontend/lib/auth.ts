export type CompanyAccount = {
  tenantId: string;
  companyName: string;
  username: string;
  password: string;
  createdAt: string;
};

export type AuthSession = {
  tenantId: string;
  companyName: string;
  username: string;
  demo: boolean;
};

export type AuthResult =
  | { ok: true; session: AuthSession }
  | { ok: false; message: string };

const ACCOUNTS_KEY = "claimops.companyAccounts";
const SESSION_KEY = "claimops.authSession";

const demoSession: AuthSession = {
  tenantId: "tenant-demo-bypass",
  companyName: "Demo Claims Company",
  username: "demo",
  demo: true
};

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

export function registerCompany(companyName: string, username: string, password: string): AuthResult {
  const normalizedCompany = companyName.trim();
  const normalizedUsername = username.trim().toLowerCase();
  if (!normalizedCompany || !normalizedUsername || !password) {
    return { ok: false, message: "Company name, username, and password are required." };
  }
  if (normalizedUsername === "demo") {
    return { ok: false, message: "The demo username is reserved for the bypass account." };
  }

  const accounts = loadAccounts();
  if (accounts.some((account) => account.username === normalizedUsername)) {
    return { ok: false, message: "That username is already registered." };
  }

  const account: CompanyAccount = {
    tenantId: `tenant-${normalizedUsername.replace(/[^a-z0-9]+/g, "-")}-${Date.now()}`,
    companyName: normalizedCompany,
    username: normalizedUsername,
    password,
    createdAt: new Date().toISOString()
  };
  saveAccounts([...accounts, account]);
  return createSession(account, false);
}

export function signInCompany(username: string, password: string): AuthResult {
  const normalizedUsername = username.trim().toLowerCase();
  if (normalizedUsername === "demo" && password === "demo") {
    saveSession(demoSession);
    return { ok: true, session: demoSession };
  }

  const account = loadAccounts().find((item) => item.username === normalizedUsername && item.password === password);
  if (!account) {
    return { ok: false, message: "Invalid company username or password." };
  }
  return createSession(account, false);
}

export function signOutCompany() {
  window.localStorage.removeItem(SESSION_KEY);
}

function createSession(account: CompanyAccount, demo: boolean): AuthResult {
  const session: AuthSession = {
    tenantId: account.tenantId,
    companyName: account.companyName,
    username: account.username,
    demo
  };
  saveSession(session);
  return { ok: true, session };
}

function loadAccounts(): CompanyAccount[] {
  const stored = window.localStorage.getItem(ACCOUNTS_KEY);
  if (!stored) {
    return [];
  }
  try {
    const parsed = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed as CompanyAccount[] : [];
  } catch {
    window.localStorage.removeItem(ACCOUNTS_KEY);
    return [];
  }
}

function saveAccounts(accounts: CompanyAccount[]) {
  window.localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(accounts));
}

function saveSession(session: AuthSession) {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}
