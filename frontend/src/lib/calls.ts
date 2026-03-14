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

/** Processing statuses at which the transcript is available. */
export const TRANSCRIPT_READY_STATUSES = new Set([
  'transcript_finalized',
  'extraction_running',
  'extraction_completed',
  'snapshots_updating',
  'risk_running',
  'recommendation_completed',
]);

/** Processing states that still warrant post-call live monitoring. */
export const ACTIVE_MONITOR_PROCESSING_STATUSES = new Set([
  'pending',
  'transcript_partial',
  'transcript_finalized',
  'extraction_running',
  'extraction_completed',
  'snapshots_updating',
  'risk_running',
]);

export interface TranscriptUtterance {
  id: string;
  call_session_id: string;
  provider_segment_id: string | null;
  speaker: string;
  text: string;
  start_ms: number | null;
  end_ms: number | null;
  sequence_number: number;
  is_final: boolean;
  created_at: string;
}

export interface CallTimelineEvent {
  id: string;
  call_session_id: string;
  provider_event_id: string | null;
  event_type: string;
  event_timestamp: string;
  sequence_number: number | null;
  created_at: string;
}

export function getCallTranscript(
  callId: string,
): Promise<TranscriptUtterance[]> {
  return apiFetch<TranscriptUtterance[]>(
    `/api/calls/${callId}/transcript`,
  );
}

export function getCallTimeline(
  callId: string,
): Promise<CallTimelineEvent[]> {
  return apiFetch<CallTimelineEvent[]>(
    `/api/calls/${callId}/timeline`,
  );
}
