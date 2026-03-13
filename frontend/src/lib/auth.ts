import { apiFetch } from './api-client';

export interface UserMe {
  id: string;
  org_id: string;
  name: string;
  email: string;
  role: string;
}

export function login(email: string, password: string) {
  return apiFetch<{ token_type: string }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function logout() {
  return apiFetch<{ detail: string }>('/api/auth/logout', {
    method: 'POST',
  });
}

export function getMe() {
  return apiFetch<UserMe>('/api/auth/me');
}
