'use client';

import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { ApiError } from '@/lib/api-client';
import { createDeal } from '@/lib/deals';

export default function NewDealPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [accountName, setAccountName] = useState('');
  const [stage, setStage] = useState('discovery');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg('');

    try {
      const deal = await createDeal({
        name,
        account_name: accountName,
        stage,
      });
      router.push(`/deals/${deal.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push('/login');
      } else if (err instanceof ApiError) {
        setErrorMsg(err.detail);
      } else {
        setErrorMsg('An unexpected error occurred.');
      }
      setSubmitting(false);
    }
  }

  return (
    <main className='flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_#fff7ed,_#e2e8f0_55%,_#cbd5e1)] px-4'>
      <form
        onSubmit={handleSubmit}
        className='w-full max-w-md rounded-2xl border border-white/60 bg-white/80 p-8 shadow-xl backdrop-blur'
      >
        <p className='text-sm font-semibold uppercase tracking-[0.24em] text-orange-600'>
          Signal Layer OS
        </p>
        <h1 className='mt-2 text-2xl font-semibold text-slate-950'>
          Create Deal
        </h1>

        {errorMsg && (
          <p className='mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700'>
            {errorMsg}
          </p>
        )}

        <label className='mt-6 block'>
          <span className='text-sm font-medium text-slate-700'>Deal Name</span>
          <input
            type='text'
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder='e.g. Acme Corp Enterprise License'
            className='mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500'
          />
        </label>

        <label className='mt-4 block'>
          <span className='text-sm font-medium text-slate-700'>
            Account Name
          </span>
          <input
            type='text'
            required
            value={accountName}
            onChange={(e) => setAccountName(e.target.value)}
            placeholder='e.g. Acme Corp'
            className='mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500'
          />
        </label>

        <label className='mt-4 block'>
          <span className='text-sm font-medium text-slate-700'>Stage</span>
          <select
            value={stage}
            onChange={(e) => setStage(e.target.value)}
            className='mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500'
          >
            <option value='discovery'>Discovery</option>
            <option value='qualification'>Qualification</option>
            <option value='proposal'>Proposal</option>
            <option value='negotiation'>Negotiation</option>
            <option value='closed_won'>Closed Won</option>
            <option value='closed_lost'>Closed Lost</option>
          </select>
        </label>

        <button
          type='submit'
          disabled={submitting}
          className='mt-6 w-full rounded-lg bg-orange-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-700 disabled:opacity-50'
        >
          {submitting ? 'Creating...' : 'Create Deal'}
        </button>
      </form>
    </main>
  );
}
