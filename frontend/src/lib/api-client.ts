const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
export const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000';

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public retryAfter?: number,
  ) {
    super(detail);
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const retryAfter = res.headers.get('Retry-After');
    throw new ApiError(
      res.status,
      body.detail ?? 'Request failed',
      retryAfter ? Number(retryAfter) : undefined,
    );
  }

  return res.json() as Promise<T>;
}
