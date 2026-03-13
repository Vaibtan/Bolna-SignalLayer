import { apiFetch } from './api-client';

export interface Stakeholder {
  id: string;
  deal_id: string;
  name: string;
  title: string | null;
  department: string | null;
  email: string | null;
  phone: string | null;
  role_label_current: string | null;
  role_confidence_current: number | null;
  stance_current: string | null;
  sentiment_current: string | null;
  last_contacted_at: string | null;
  source_type: string;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface StakeholderCreate {
  name: string;
  title?: string;
  department?: string;
  email?: string;
  phone?: string;
}

export interface StakeholderUpdate {
  name?: string;
  title?: string;
  department?: string;
  email?: string;
  phone?: string;
}

export function listStakeholders(dealId: string) {
  return apiFetch<Stakeholder[]>(`/api/deals/${dealId}/stakeholders`);
}

export function createStakeholder(dealId: string, data: StakeholderCreate) {
  return apiFetch<Stakeholder>(`/api/deals/${dealId}/stakeholders`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateStakeholder(
  dealId: string,
  stakeholderId: string,
  data: StakeholderUpdate,
) {
  return apiFetch<Stakeholder>(
    `/api/deals/${dealId}/stakeholders/${stakeholderId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    },
  );
}
