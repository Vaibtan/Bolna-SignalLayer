'use client';

import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { ApiError } from '@/lib/api-client';
import { login } from '@/lib/auth';

type FormState = 'idle' | 'loading' | 'error' | 'locked';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [state, setState] = useState<FormState>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setState('loading');
    setErrorMsg('');

    try {
      await login(email, password);
      router.push('/');
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setState('locked');
        setErrorMsg(
          `Too many attempts. Try again in ${err.retryAfter ?? 60}s.`,
        );
      } else if (err instanceof ApiError) {
        setState('error');
        setErrorMsg(err.detail);
      } else {
        setState('error');
        setErrorMsg('An unexpected error occurred.');
      }
    }
  }

  const disabled = state === 'loading' || state === 'locked';

  return (
    <main className='flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_#fff7ed,_#e2e8f0_55%,_#cbd5e1)] px-4'>
      <form
        onSubmit={handleSubmit}
        className='w-full max-w-sm rounded-2xl border border-white/60 bg-white/80 p-8 shadow-xl backdrop-blur'
      >
        <p className='text-sm font-semibold uppercase tracking-[0.24em] text-orange-600'>
          DealGraph Voice OS
        </p>
        <h1 className='mt-2 text-2xl font-semibold text-slate-950'>Sign in</h1>

        {errorMsg && (
          <p className='mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700'>
            {errorMsg}
          </p>
        )}

        <label className='mt-6 block'>
          <span className='text-sm font-medium text-slate-700'>Email</span>
          <input
            type='email'
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className='mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500'
          />
        </label>

        <label className='mt-4 block'>
          <span className='text-sm font-medium text-slate-700'>Password</span>
          <input
            type='password'
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className='mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500'
          />
        </label>

        <button
          type='submit'
          disabled={disabled}
          className='mt-6 w-full rounded-lg bg-orange-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-700 disabled:opacity-50'
        >
          {state === 'loading' ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </main>
  );
}
