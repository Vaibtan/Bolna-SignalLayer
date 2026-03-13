'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { WS_BASE } from '@/lib/api-client';
import { CallSession, TERMINAL_CALL_STATUSES, getCallSession } from '@/lib/calls';

const POLL_INTERVAL = Number(
  process.env.NEXT_PUBLIC_ACTIVE_STATE_POLL_INTERVAL_MS ?? 5000,
);

/**
 * Hook for real-time call monitoring.
 *
 * - Polls the call session REST endpoint every 5 s while the call is active.
 * - Connects a WebSocket to `/ws/calls/{callId}` for instant hints.
 * - On any WS message, immediately invalidates the query to refetch.
 * - On WS reconnect, invalidates to catch up on missed events.
 * - Stops both WS and polling once the call reaches a terminal status.
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
      if (session && TERMINAL_CALL_STATUSES.has(session.status)) return false;
      return POLL_INTERVAL;
    },
  });

  const isTerminal = callSession
    ? TERMINAL_CALL_STATUSES.has(callSession.status)
    : false;

  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['call', callId] });
  }, [queryClient, callId]);

  useEffect(() => {
    closingRef.current = false;

    if (isTerminal) return;

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
  }, [callId, isTerminal, invalidate]);

  return {
    callSession: callSession ?? null,
    isLoading,
    isTerminal,
    isConnected,
    error: error ?? null,
  };
}
