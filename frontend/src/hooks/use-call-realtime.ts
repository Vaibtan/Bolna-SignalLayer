'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { WS_BASE } from '@/lib/api-client';
import {
  ACTIVE_MONITOR_PROCESSING_STATUSES,
  CallSession,
  TERMINAL_CALL_STATUSES,
  getCallSession,
} from '@/lib/calls';

const POLL_INTERVAL = Number(
  process.env.NEXT_PUBLIC_ACTIVE_STATE_POLL_INTERVAL_MS ?? 5000,
);
const POST_CALL_GRACE_MS = 120_000;

function shouldMonitorCall(session: CallSession | undefined): boolean {
  if (!session) {
    return true;
  }

  if (!TERMINAL_CALL_STATUSES.has(session.status)) {
    return true;
  }

  if (
    !ACTIVE_MONITOR_PROCESSING_STATUSES.has(
      session.processing_status,
    )
  ) {
    return false;
  }

  if (!session.ended_at) {
    return true;
  }

  const endedAt = new Date(session.ended_at).getTime();
  return Date.now() - endedAt < POST_CALL_GRACE_MS;
}

/**
 * Hook for real-time call monitoring.
 *
 * - Polls the call session REST endpoint every 5 s while the call is active.
 * - Connects a WebSocket to `/ws/calls/{callId}` for instant hints.
 * - On any WS message, immediately invalidates the query to refetch.
 * - On WS reconnect, invalidates to catch up on missed events.
 * - Keeps monitoring briefly after terminal call status so post-call
 *   processing transitions can still reach the page.
 */
export function useCallRealtime(callId: string) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closingRef = useRef(false);
  const [isConnected, setIsConnected] = useState(false);

  const { data: callSession, isLoading, error } = useQuery<CallSession, Error>({
    queryKey: ['call', callId],
    queryFn: () => getCallSession(callId),
    refetchInterval: (query) => {
      const session = query.state.data;
      if (!shouldMonitorCall(session)) {
        return false;
      }
      return POLL_INTERVAL;
    },
  });

  const isTerminal = callSession
    ? TERMINAL_CALL_STATUSES.has(callSession.status)
    : false;
  const shouldMonitor = shouldMonitorCall(callSession);
  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['call', callId] });
  }, [queryClient, callId]);

  useEffect(() => {
    if (
      !callSession ||
      !TERMINAL_CALL_STATUSES.has(callSession.status) ||
      !ACTIVE_MONITOR_PROCESSING_STATUSES.has(
        callSession.processing_status,
      ) ||
      !callSession.ended_at
    ) {
      return;
    }

    const deadline =
      new Date(callSession.ended_at).getTime() +
      POST_CALL_GRACE_MS;
    const delay = deadline - Date.now();
    const timeoutId = window.setTimeout(() => {
      invalidate();
    }, Math.max(delay, 0));

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [
    callSession,
    invalidate,
  ]);

  useEffect(() => {
    closingRef.current = false;

    if (!shouldMonitor) return;

    function connect() {
      const ws = new WebSocket(`${WS_BASE}/ws/calls/${callId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        // Catch up on events missed while disconnected
        invalidate();
      };

      ws.onmessage = () => {
        invalidate();
      };

      ws.onclose = () => {
        wsRef.current = null;
        setIsConnected(false);
        // Only reconnect if this wasn't an intentional close
        // (effect cleanup or terminal state transition)
        if (!closingRef.current) {
          reconnectRef.current = setTimeout(connect, 2000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      closingRef.current = true;
      if (reconnectRef.current != null) {
        clearTimeout(reconnectRef.current);
        reconnectRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [callId, invalidate, shouldMonitor]);

  return {
    callSession: callSession ?? null,
    isLoading,
    isTerminal,
    isConnected,
    error: error ?? null,
  };
}
