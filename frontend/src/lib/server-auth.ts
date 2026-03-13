'use server';

import { cookies } from 'next/headers';

import type { UserMe } from './auth';

const SERVER_API_BASE =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  'http://localhost:8000';

export async function getServerSessionUser(): Promise<UserMe | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get('access_token');

  if (!token) {
    return null;
  }

  const response = await fetch(`${SERVER_API_BASE}/api/auth/me`, {
    headers: {
      Cookie: `access_token=${token.value}`,
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    return null;
  }

  return (await response.json()) as UserMe;
}
