import { apiFetch } from './api-client';

export interface ActionRecommendation {
  id: string;
  deal_id: string;
  call_session_id: string | null;
  target_stakeholder_id: string | null;
  action_type: string;
  reason: string;
  confidence: number | null;
  status: string;
  payload_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface FollowupDraft {
  id: string;
  deal_id: string;
  call_session_id: string;
  draft_type: string;
  subject: string | null;
  body_text: string;
  tone: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface RiskSnapshot {
  id: string;
  deal_id: string;
  call_session_id: string | null;
  score: number;
  level: string;
  factors_json: Record<string, unknown> | null;
  change_summary_json: Record<string, unknown> | null;
  created_at: string;
}

export function getRecommendations(
  dealId: string,
): Promise<ActionRecommendation[]> {
  return apiFetch<ActionRecommendation[]>(
    `/api/deals/${dealId}/recommendations`,
  );
}

export function getDrafts(
  dealId: string,
): Promise<FollowupDraft[]> {
  return apiFetch<FollowupDraft[]>(
    `/api/deals/${dealId}/drafts`,
  );
}

export function getRisk(
  dealId: string,
): Promise<RiskSnapshot | null> {
  return apiFetch<RiskSnapshot | null>(
    `/api/deals/${dealId}/risk`,
  );
}

export function acceptRecommendation(
  recommendationId: string,
): Promise<ActionRecommendation> {
  return apiFetch<ActionRecommendation>(
    `/api/recommendations/${recommendationId}/accept`,
    { method: 'POST' },
  );
}

export function dismissRecommendation(
  recommendationId: string,
): Promise<ActionRecommendation> {
  return apiFetch<ActionRecommendation>(
    `/api/recommendations/${recommendationId}/dismiss`,
    { method: 'POST' },
  );
}
