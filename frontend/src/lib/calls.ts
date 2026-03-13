import { apiFetch } from './api-client';

export interface CallSession {
  id: string;
  deal_id: string;
  stakeholder_id: string;
  provider_name: string;
  provider_call_id: string | null;
  status: string;
  processing_status: string;
  objective: string | null;
  initiated_by_user_id: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  recording_url: string | null;
  provider_metadata_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CallInitiateRequest {
  stakeholder_id: string;
  objective: string;
  topics?: string;
}

export function initiateCall(
  dealId: string,
  data: CallInitiateRequest,
): Promise<CallSession> {
  return apiFetch<CallSession>(`/api/deals/${dealId}/calls`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function getCallSession(callId: string): Promise<CallSession> {
  return apiFetch<CallSession>(`/api/calls/${callId}`);
}

export const TERMINAL_CALL_STATUSES = new Set([
  'completed',
  'no_answer',
  'busy',
  'failed',
  'canceled',
]);
