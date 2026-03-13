import { apiFetch } from './api-client';

export interface Deal {
  id: string;
  org_id: string;
  name: string;
  account_name: string;
  stage: string;
  owner_user_id: string | null;
  risk_score_current: number | null;
  risk_level_current: string | null;
  coverage_status_current: string | null;
  summary_current: string | null;
  created_at: string;
  updated_at: string;
}

export interface DealCreate {
  name: string;
  account_name: string;
  stage?: string;
}

export interface DealUpdate {
  name?: string;
  account_name?: string;
  stage?: string;
}

export function listDeals() {
  return apiFetch<Deal[]>('/api/deals');
}

export function getDeal(id: string) {
  return apiFetch<Deal>(`/api/deals/${id}`);
}

export function createDeal(data: DealCreate) {
  return apiFetch<Deal>('/api/deals', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateDeal(id: string, data: DealUpdate) {
  return apiFetch<Deal>(`/api/deals/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}
