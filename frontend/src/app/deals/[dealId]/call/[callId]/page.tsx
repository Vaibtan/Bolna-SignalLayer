'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { ApiError } from '@/lib/api-client';
import {
  CallTimelineEvent,
  TRANSCRIPT_READY_STATUSES,
  TranscriptUtterance,
  getCallTimeline,
  getCallTranscript,
} from '@/lib/calls';
import { useCallRealtime } from '@/hooks/use-call-realtime';

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  initiating: { bg: 'bg-slate-100', text: 'text-slate-700', label: 'Initiating' },
  queued: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Queued' },
  ringing: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Ringing' },
  in_progress: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'In Progress' },
  completed: { bg: 'bg-green-100', text: 'text-green-700', label: 'Completed' },
  no_answer: { bg: 'bg-orange-100', text: 'text-orange-700', label: 'No Answer' },
  busy: { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Busy' },
  failed: { bg: 'bg-red-100', text: 'text-red-700', label: 'Failed' },
  canceled: { bg: 'bg-slate-100', text: 'text-slate-600', label: 'Canceled' },
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? {
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    label: status,
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  );
}

function LiveDuration({ startedAt }: { startedAt: string }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = new Date(startedAt).getTime();
    const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  return (
    <span className='tabular-nums'>
      {formatDuration(elapsed)}
    </span>
  );
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function formatEventType(eventType: string): string {
  return eventType.replace(/[._]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function TranscriptSection({ callId, processingStatus }: { callId: string; processingStatus: string }) {
  const ready = TRANSCRIPT_READY_STATUSES.has(processingStatus);

  const { data: utterances, isLoading } = useQuery<TranscriptUtterance[]>({
    queryKey: ['call-transcript', callId],
    queryFn: () => getCallTranscript(callId),
    enabled: ready,
    staleTime: Infinity,
  });

  if (!ready) return null;

  return (
    <div className='mt-6 rounded-xl border border-slate-200 bg-slate-50 p-6'>
      <h2 className='text-sm font-semibold text-slate-700'>Transcript</h2>
      {isLoading ? (
        <p className='mt-2 text-sm text-slate-400'>Loading transcript...</p>
      ) : !utterances?.length ? (
        <p className='mt-2 text-sm text-slate-400'>No transcript available.</p>
      ) : (
        <div className='mt-3 max-h-96 space-y-3 overflow-y-auto'>
          {utterances.map((u) => (
            <div key={u.id} className='flex gap-3'>
              <span
                className={`mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  u.speaker === 'agent'
                    ? 'bg-orange-100 text-orange-700'
                    : u.speaker === 'prospect'
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-slate-200 text-slate-600'
                }`}
              >
                {u.speaker === 'agent' ? 'A' : u.speaker === 'prospect' ? 'P' : '?'}
              </span>
              <div>
                <p className='text-xs font-medium capitalize text-slate-500'>
                  {u.speaker}
                </p>
                <p className='text-sm leading-relaxed text-slate-800'>{u.text}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TimelineSection({ callId, isTerminal }: { callId: string; isTerminal: boolean }) {
  const { data: events } = useQuery<CallTimelineEvent[]>({
    queryKey: ['call-timeline', callId],
    queryFn: () => getCallTimeline(callId),
    enabled: isTerminal,
    staleTime: Infinity,
  });

  if (!isTerminal || !events || events.length === 0) return null;

  return (
    <div className='mt-6 rounded-xl border border-slate-200 bg-slate-50 p-6'>
      <h2 className='text-sm font-semibold text-slate-700'>Timeline</h2>
      <ol className='relative mt-3 border-l border-slate-300 ml-2'>
        {events.map((ev) => (
          <li key={ev.id} className='mb-4 ml-4 last:mb-0'>
            <div className='absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border border-white bg-slate-400' />
            <p className='text-sm font-medium text-slate-800'>
              {formatEventType(ev.event_type)}
            </p>
            <time className='text-xs text-slate-500'>
              {formatTime(ev.event_timestamp)}
            </time>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function CallPage() {
  const { dealId, callId } = useParams<{ dealId: string; callId: string }>();
  const router = useRouter();
  const { callSession, isLoading, isTerminal, isConnected, error } =
    useCallRealtime(callId);

  if (error) {
    if (error instanceof ApiError && error.status === 401) {
      router.push('/login');
      return null;
    }

    return (
      <main className='flex min-h-screen items-center justify-center bg-slate-50 px-4'>
        <div className='w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm'>
          <h1 className='text-xl font-semibold text-slate-950'>
            Call unavailable
          </h1>
          <p className='mt-3 text-sm leading-6 text-slate-600'>
            {error instanceof ApiError
              ? error.detail
              : 'Unable to load call status.'}
          </p>
          <Link
            href={`/deals/${dealId}`}
            className='mt-6 inline-flex rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-700'
          >
            Back to Deal
          </Link>
        </div>
      </main>
    );
  }

  if (isLoading || !callSession) {
    return (
      <main className='flex min-h-screen items-center justify-center bg-slate-50'>
        <p className='text-slate-500'>Loading call...</p>
      </main>
    );
  }

  const isActive = !isTerminal;

  return (
    <main className='min-h-screen bg-[radial-gradient(circle_at_top,_#fff7ed,_#e2e8f0_55%,_#cbd5e1)] px-6 py-10'>
      <div className='mx-auto max-w-2xl'>
        <Link
          href={`/deals/${dealId}`}
          className='text-sm font-medium text-orange-600 hover:underline'
        >
          &larr; Back to Deal
        </Link>

        <div className='mt-4 rounded-2xl border border-white/60 bg-white/75 p-8 backdrop-blur'>
          <div className='flex items-center justify-between'>
            <h1 className='text-xl font-semibold text-slate-950'>
              Call Monitor
            </h1>
            <div className='flex items-center gap-3'>
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-amber-400'}`}
                title={isConnected ? 'Live' : 'Polling'}
              />
              <span className='text-xs text-slate-500'>
                {isConnected ? 'Live' : 'Polling'}
              </span>
            </div>
          </div>

          <div className='mt-6 flex items-center gap-3'>
            <StatusBadge status={callSession.status} />
            {isActive && (
              <span className='text-xs text-slate-400 animate-pulse'>
                updating...
              </span>
            )}
          </div>

          <div className='mt-6 grid gap-4 sm:grid-cols-2'>
            {callSession.started_at && (
              <div className='rounded-xl border border-slate-200 bg-slate-50 p-4'>
                <p className='text-xs font-medium text-slate-500'>Started</p>
                <p className='mt-1 text-lg font-semibold text-slate-950'>
                  {formatTime(callSession.started_at)}
                </p>
              </div>
            )}

            <div className='rounded-xl border border-slate-200 bg-slate-50 p-4'>
              <p className='text-xs font-medium text-slate-500'>Duration</p>
              <p className='mt-1 text-lg font-semibold text-slate-950'>
                {callSession.duration_seconds != null ? (
                  formatDuration(callSession.duration_seconds)
                ) : callSession.started_at && isActive ? (
                  <LiveDuration startedAt={callSession.started_at} />
                ) : (
                  '—'
                )}
              </p>
            </div>

            {callSession.objective && (
              <div className='rounded-xl border border-slate-200 bg-slate-50 p-4 sm:col-span-2'>
                <p className='text-xs font-medium text-slate-500'>Objective</p>
                <p className='mt-1 text-sm text-slate-700'>
                  {callSession.objective.replace(/_/g, ' ')}
                </p>
              </div>
            )}

            {callSession.ended_at && (
              <div className='rounded-xl border border-slate-200 bg-slate-50 p-4'>
                <p className='text-xs font-medium text-slate-500'>Ended</p>
                <p className='mt-1 text-lg font-semibold text-slate-950'>
                  {formatTime(callSession.ended_at)}
                </p>
              </div>
            )}

            <div className='rounded-xl border border-slate-200 bg-slate-50 p-4'>
              <p className='text-xs font-medium text-slate-500'>Processing</p>
              <p className='mt-1 text-sm font-semibold text-slate-950'>
                {callSession.processing_status.replace(/_/g, ' ')}
              </p>
            </div>
          </div>

          <TranscriptSection callId={callId} processingStatus={callSession.processing_status} />
          <TimelineSection callId={callId} isTerminal={isTerminal} />

          {isTerminal && (
            <div className='mt-6'>
              <Link
                href={`/deals/${dealId}`}
                className='inline-flex rounded-lg bg-slate-800 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-900'
              >
                Return to Deal
              </Link>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
