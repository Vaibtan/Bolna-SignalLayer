'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { FormEvent, useEffect, useState } from 'react';

import { ApiError } from '@/lib/api-client';
import { initiateCall } from '@/lib/calls';
import { Deal, getDeal } from '@/lib/deals';
import {
  ActionRecommendation,
  FollowupDraft,
  acceptRecommendation,
  dismissRecommendation,
  getDrafts,
  getRecommendations,
} from '@/lib/intelligence';
import {
  Stakeholder,
  StakeholderCreate,
  createStakeholder,
  listStakeholders,
} from '@/lib/stakeholders';

export default function DealWorkspacePage() {
  const { dealId } = useParams<{ dealId: string }>();
  const router = useRouter();

  const [deal, setDeal] = useState<Deal | null>(null);
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([]);
  const [recommendations, setRecommendations] = useState<ActionRecommendation[]>([]);
  const [drafts, setDrafts] = useState<FollowupDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [callTarget, setCallTarget] = useState<Stakeholder | null>(null);
  const hasLoadedDeal = deal !== null;

  useEffect(() => {
    Promise.all([
      getDeal(dealId),
      listStakeholders(dealId),
      getRecommendations(dealId).catch(() => []),
      getDrafts(dealId).catch(() => []),
    ])
      .then(([d, shs, recs, drfs]) => {
        setDeal(d);
        setStakeholders(shs);
        setRecommendations(recs);
        setDrafts(drfs);
        setErrorMsg('');
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          router.push('/login');
          return;
        }
        if (err instanceof ApiError) {
          setErrorMsg(err.detail);
          return;
        }
        setErrorMsg('Unable to load the deal workspace.');
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dealId]);

  useEffect(() => {
    if (loading || !hasLoadedDeal) {
      return;
    }
    if (recommendations.length > 0 && drafts.length > 0) {
      return;
    }

    let cancelled = false;
    let attempts = 0;
    const maxAttempts = 24;

    const intervalId = window.setInterval(() => {
      attempts += 1;
      void Promise.all([
        getDeal(dealId),
        getRecommendations(dealId),
        getDrafts(dealId),
      ])
        .then(([nextDeal, nextRecommendations, nextDrafts]) => {
          if (cancelled) {
            return;
          }
          setDeal(nextDeal);
          setRecommendations(nextRecommendations);
          setDrafts(nextDrafts);

          if (
            (nextRecommendations.length > 0 &&
              nextDrafts.length > 0) ||
            attempts >= maxAttempts
          ) {
            window.clearInterval(intervalId);
          }
        })
        .catch(() => {
          if (attempts >= maxAttempts) {
            window.clearInterval(intervalId);
          }
        });
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [
    deal?.id,
    dealId,
    drafts.length,
    hasLoadedDeal,
    loading,
    recommendations.length,
  ]);

  if (loading) {
    return (
      <main className='flex min-h-screen items-center justify-center bg-slate-50'>
        <p className='text-slate-500'>Loading deal...</p>
      </main>
    );
  }

  if (deal === null) {
    return (
      <main className='flex min-h-screen items-center justify-center bg-slate-50 px-4'>
        <div className='w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm'>
          <h1 className='text-xl font-semibold text-slate-950'>
            Deal unavailable
          </h1>
          <p className='mt-3 text-sm leading-6 text-slate-600'>
            {errorMsg || 'The requested deal could not be loaded.'}
          </p>
          <Link
            href='/deals'
            className='mt-6 inline-flex rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-700'
          >
            Back to deals
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className='min-h-screen bg-[radial-gradient(circle_at_top,_#fff7ed,_#e2e8f0_55%,_#cbd5e1)] px-6 py-10'>
      <div className='mx-auto max-w-5xl'>
        <Link
          href='/deals'
          className='text-sm font-medium text-orange-600 hover:underline'
        >
          &larr; All Deals
        </Link>

        <div className='mt-4 rounded-2xl border border-white/60 bg-white/75 p-8 backdrop-blur'>
          <div className='flex items-start justify-between'>
            <div>
              <h1 className='text-2xl font-semibold text-slate-950'>
                {deal.name}
              </h1>
              <p className='mt-1 text-sm text-slate-600'>
                {deal.account_name}
              </p>
            </div>
            <span className='rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700'>
              {deal.stage}
            </span>
          </div>

          {deal.summary_current && (
            <p className='mt-4 text-sm leading-6 text-slate-600'>
              {deal.summary_current}
            </p>
          )}

          <div className='mt-6 grid gap-3 sm:grid-cols-3'>
            <Stat
              label='Risk Score'
              value={deal.risk_score_current?.toString() ?? '—'}
            />
            <Stat
              label='Risk Level'
              value={deal.risk_level_current ?? '—'}
            />
            <Stat
              label='Coverage'
              value={deal.coverage_status_current ?? '—'}
            />
          </div>
        </div>

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <RecommendationsSection
            recommendations={recommendations}
            onUpdate={(updated) =>
              setRecommendations((prev) =>
                prev.map((r) => (r.id === updated.id ? updated : r)),
              )
            }
          />
        )}

        {/* Follow-up Drafts */}
        {drafts.length > 0 && <DraftsSection drafts={drafts} />}

        {/* Stakeholders */}
        <div className='mt-8'>
          <div className='flex items-center justify-between'>
            <h2 className='text-xl font-semibold text-slate-950'>
              Stakeholders
            </h2>
            <button
              onClick={() => setShowForm(!showForm)}
              className='rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-700'
            >
              {showForm ? 'Cancel' : 'Add Stakeholder'}
            </button>
          </div>

          {showForm && (
            <AddStakeholderForm
              dealId={dealId}
              onCreated={(sh) => {
                setStakeholders((prev) => [sh, ...prev]);
                setShowForm(false);
              }}
            />
          )}

          {stakeholders.length === 0 && !showForm ? (
            <p className='mt-4 text-sm text-slate-500'>
              No stakeholders yet. Add one to start tracking contacts.
            </p>
          ) : (
            <div className='mt-4 grid gap-3'>
              {stakeholders.map((sh) => (
                <div
                  key={sh.id}
                  className='rounded-xl border border-slate-200 bg-white/75 p-5 backdrop-blur'
                >
                  <div className='flex items-start justify-between'>
                    <div>
                      <p className='font-semibold text-slate-950'>{sh.name}</p>
                      {sh.title && (
                        <p className='text-sm text-slate-600'>
                          {sh.title}
                          {sh.department ? ` · ${sh.department}` : ''}
                        </p>
                      )}
                    </div>
                    <span className='rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500'>
                      {sh.source_type}
                    </span>
                  </div>
                  <div className='mt-2 flex items-center gap-4 text-xs text-slate-500'>
                    {sh.email && <span>{sh.email}</span>}
                    {sh.phone && <span>{sh.phone}</span>}
                    {sh.phone && (
                      <button
                        onClick={() => setCallTarget(sh)}
                        className='ml-auto rounded-lg bg-emerald-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-emerald-700'
                      >
                        Call with AI
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {callTarget && (
        <CallModal
          dealId={dealId}
          stakeholder={callTarget}
          onClose={() => setCallTarget(null)}
        />
      )}
    </main>
  );
}

function RecommendationsSection({
  recommendations,
  onUpdate,
}: {
  recommendations: ActionRecommendation[];
  onUpdate: (r: ActionRecommendation) => void;
}) {
  async function handleAccept(id: string) {
    const updated = await acceptRecommendation(id);
    onUpdate(updated);
  }
  async function handleDismiss(id: string) {
    const updated = await dismissRecommendation(id);
    onUpdate(updated);
  }

  return (
    <div className='mt-8'>
      <h2 className='text-xl font-semibold text-slate-950'>
        Recommendations
      </h2>
      <div className='mt-4 grid gap-3'>
        {recommendations.map((rec) => (
          <div
            key={rec.id}
            className='rounded-xl border border-slate-200 bg-white/75 p-5 backdrop-blur'
          >
            <div className='flex items-start justify-between'>
              <div>
                <p className='text-sm font-semibold text-slate-950'>
                  {rec.action_type.replace(/_/g, ' ')}
                </p>
                <p className='mt-1 text-sm leading-relaxed text-slate-600'>
                  {rec.reason}
                </p>
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  rec.status === 'accepted'
                    ? 'bg-green-100 text-green-700'
                    : rec.status === 'dismissed'
                      ? 'bg-slate-100 text-slate-500'
                      : 'bg-blue-100 text-blue-700'
                }`}
              >
                {rec.status}
              </span>
            </div>
            {rec.status === 'proposed' && (
              <div className='mt-3 flex gap-2'>
                <button
                  onClick={() => handleAccept(rec.id)}
                  className='rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-emerald-700'
                >
                  Accept
                </button>
                <button
                  onClick={() => handleDismiss(rec.id)}
                  className='rounded-lg bg-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-300'
                >
                  Dismiss
                </button>
              </div>
            )}
            {typeof rec.payload_json?.talk_track === 'string' && rec.payload_json.talk_track && (
              <p className='mt-2 rounded-lg bg-amber-50 p-3 text-xs leading-relaxed text-amber-800'>
                <span className='font-semibold'>Talk track: </span>
                {rec.payload_json.talk_track}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function DraftsSection({ drafts }: { drafts: FollowupDraft[] }) {
  return (
    <div className='mt-8'>
      <h2 className='text-xl font-semibold text-slate-950'>
        Follow-up Drafts
      </h2>
      <div className='mt-4 grid gap-3'>
        {drafts.map((draft) => (
          <div
            key={draft.id}
            className='rounded-xl border border-slate-200 bg-white/75 p-5 backdrop-blur'
          >
            <div className='flex items-center gap-2'>
              <span className='rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600'>
                {draft.draft_type.replace(/_/g, ' ')}
              </span>
              <span className='text-xs text-slate-400'>{draft.tone}</span>
            </div>
            {draft.subject && (
              <p className='mt-2 text-sm font-medium text-slate-800'>
                {draft.subject}
              </p>
            )}
            <p className='mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-600'>
              {draft.body_text}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className='rounded-xl border border-slate-200 bg-slate-50 p-4'>
      <p className='text-xs font-medium text-slate-500'>{label}</p>
      <p className='mt-1 text-lg font-semibold text-slate-950'>{value}</p>
    </div>
  );
}

function AddStakeholderForm({
  dealId,
  onCreated,
}: {
  dealId: string;
  onCreated: (sh: Stakeholder) => void;
}) {
  const [name, setName] = useState('');
  const [title, setTitle] = useState('');
  const [department, setDepartment] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg('');

    const data: StakeholderCreate = { name };
    if (title) data.title = title;
    if (department) data.department = department;
    if (email) data.email = email;
    if (phone) data.phone = phone;

    try {
      const sh = await createStakeholder(dealId, data);
      onCreated(sh);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        window.location.href = '/login';
      } else if (err instanceof ApiError) {
        setErrorMsg(err.detail);
      } else {
        setErrorMsg('An unexpected error occurred.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className='mt-4 rounded-xl border border-slate-200 bg-white/80 p-5 backdrop-blur'
    >
      {errorMsg && (
        <p className='mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700'>
          {errorMsg}
        </p>
      )}
      <div className='grid gap-3 sm:grid-cols-2'>
        <input
          type='text'
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder='Name *'
          className='rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500'
        />
        <input
          type='text'
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder='Title'
          className='rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500'
        />
        <input
          type='text'
          value={department}
          onChange={(e) => setDepartment(e.target.value)}
          placeholder='Department'
          className='rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500'
        />
        <input
          type='email'
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder='Email'
          className='rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500'
        />
        <input
          type='tel'
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder='Phone'
          className='rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500'
        />
      </div>
      <button
        type='submit'
        disabled={submitting}
        className='mt-4 rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-700 disabled:opacity-50'
      >
        {submitting ? 'Adding...' : 'Add Stakeholder'}
      </button>
    </form>
  );
}

type CallModalState = 'idle' | 'initiating' | 'failure' | 'throttled';

function CallModal({
  dealId,
  stakeholder,
  onClose,
}: {
  dealId: string;
  stakeholder: Stakeholder;
  onClose: () => void;
}) {
  const router = useRouter();
  const [objective, setObjective] = useState('discovery_qualification');
  const [topics, setTopics] = useState('');
  const [state, setState] = useState<CallModalState>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [retryAfter, setRetryAfter] = useState(0);

  async function handleInitiate(e: FormEvent) {
    e.preventDefault();
    setState('initiating');
    setErrorMsg('');

    try {
      const session = await initiateCall(dealId, {
        stakeholder_id: stakeholder.id,
        objective,
        topics: topics || undefined,
      });
      if (session.status === 'failed') {
        setErrorMsg(
          session.provider_metadata_json?.error
            ? String(session.provider_metadata_json.error)
            : 'The call provider could not place the call.',
        );
        setState('failure');
      } else {
        router.push(`/deals/${dealId}/call/${session.id}`);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        window.location.href = '/login';
        return;
      }
      if (err instanceof ApiError && err.status === 429) {
        setRetryAfter(err.retryAfter ?? 60);
        setState('throttled');
        return;
      }
      if (err instanceof ApiError) {
        setErrorMsg(err.detail);
      } else {
        setErrorMsg('An unexpected error occurred.');
      }
      setState('failure');
    }
  }

  return (
    <div className='fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm'>
      <div className='w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl'>
        <div className='flex items-start justify-between'>
          <h3 className='text-lg font-semibold text-slate-950'>
            Call with AI
          </h3>
          <button
            onClick={onClose}
            className='text-slate-400 transition hover:text-slate-600'
          >
            &times;
          </button>
        </div>

        <p className='mt-2 text-sm text-slate-600'>
          Calling <span className='font-medium'>{stakeholder.name}</span>
          {stakeholder.phone ? ` at ${stakeholder.phone}` : ''}
        </p>

        {state === 'idle' || state === 'failure' ? (
          <form onSubmit={handleInitiate} className='mt-4 space-y-3'>
            {errorMsg && (
              <p className='rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700'>
                {errorMsg}
              </p>
            )}

            <div>
              <label className='block text-xs font-medium text-slate-600'>
                Objective
              </label>
              <select
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                className='mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500'
              >
                <option value='discovery_qualification'>
                  Discovery &amp; Qualification
                </option>
                <option value='timeline_procurement_validation'>
                  Timeline &amp; Procurement Validation
                </option>
                <option value='blocker_clarification'>
                  Blocker Clarification
                </option>
              </select>
            </div>

            <div>
              <label className='block text-xs font-medium text-slate-600'>
                Topic notes (optional)
              </label>
              <textarea
                value={topics}
                onChange={(e) => setTopics(e.target.value)}
                maxLength={500}
                rows={2}
                placeholder='Key questions or context for the AI...'
                className='mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500'
              />
            </div>

            <button
              type='submit'
              className='w-full rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700'
            >
              Start Call
            </button>
          </form>
        ) : null}

        {state === 'initiating' && (
          <div className='mt-6 text-center'>
            <p className='text-sm text-slate-600'>Initiating call...</p>
          </div>
        )}

        {state === 'throttled' && (
          <div className='mt-4 rounded-lg bg-amber-50 p-4'>
            <p className='text-sm font-medium text-amber-800'>
              Rate limit reached
            </p>
            <p className='mt-1 text-xs text-amber-600'>
              Please wait {retryAfter} seconds before trying again.
            </p>
            <button
              onClick={onClose}
              className='mt-3 w-full rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-900'
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
