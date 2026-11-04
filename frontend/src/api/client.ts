/** Thin fetch wrapper. Admin calls pass the Bearer token from `getAdminToken()`. */

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }

  /** The server returns 503 `ai_unavailable` when an OpenAI call fails. */
  get isAiUnavailable(): boolean {
    return this.status === 503 && this.message === 'ai_unavailable';
  }
}

const TOKEN_KEY = 'admin_token';

export function getAdminToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAdminToken(token: string | null): void {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable */
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  // Let the browser set the multipart boundary for FormData bodies.
  if (init.body && !(init.body instanceof FormData))
    headers.set('Content-Type', 'application/json');
  const token = getAdminToken();
  if (token && path.startsWith('/admin')) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`/api${path}`, { ...init, headers });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: unknown };
    const message = typeof body.detail === 'string' ? body.detail : res.statusText;
    throw new ApiError(res.status, message);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}
