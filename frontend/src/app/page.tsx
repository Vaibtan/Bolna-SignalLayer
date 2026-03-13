import { redirect } from 'next/navigation';

import { getServerSessionUser } from '@/lib/server-auth';

export default async function Home(): Promise<React.JSX.Element> {
  const currentUser = await getServerSessionUser();

  if (currentUser === null) {
    redirect('/login');
  }

  return (
    <main className='min-h-screen bg-[radial-gradient(circle_at_top,_#fff7ed,_#e2e8f0_55%,_#cbd5e1)] px-6 py-16 text-slate-950'>
      <section className='mx-auto flex max-w-5xl flex-col gap-10 rounded-[2rem] border border-white/60 bg-white/75 p-10 shadow-[0_30px_80px_rgba(15,23,42,0.12)] backdrop-blur md:p-14'>
        <div className='flex flex-col gap-4'>
          <p className='text-sm font-semibold uppercase tracking-[0.24em] text-orange-600'>
            DealGraph Voice OS
          </p>
          <h1 className='max-w-3xl text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl'>
            Welcome back, {currentUser.name}.
          </h1>
          <p className='max-w-2xl text-lg leading-8 text-slate-700'>
            Your authenticated workspace is active. Phase 2 now validates the
            session against the backend instead of trusting cookie presence
            alone.
          </p>
        </div>
        <div className='grid gap-4 md:grid-cols-3'>
          <article className='rounded-3xl border border-slate-200 bg-slate-50 p-6'>
            <p className='text-sm font-semibold text-slate-500'>Calls</p>
            <h2 className='mt-3 text-2xl font-semibold text-slate-950'>
              Bolna outbound pipeline
            </h2>
            <p className='mt-2 text-sm leading-6 text-slate-600'>
              Real-number outbound calling with webhook and polling failover is
              the core demo path.
            </p>
          </article>
          <article className='rounded-3xl border border-slate-200 bg-slate-50 p-6'>
            <p className='text-sm font-semibold text-slate-500'>Analysis</p>
            <h2 className='mt-3 text-2xl font-semibold text-slate-950'>
              Post-call intelligence
            </h2>
            <p className='mt-2 text-sm leading-6 text-slate-600'>
              Structured extraction, risk scoring, and follow-up drafting will
              land on top of the worker pipeline next.
            </p>
          </article>
          <article className='rounded-3xl border border-slate-200 bg-slate-50 p-6'>
            <p className='text-sm font-semibold text-slate-500'>Ops</p>
            <h2 className='mt-3 text-2xl font-semibold text-slate-950'>
              Self-hosted deployment
            </h2>
            <p className='mt-2 text-sm leading-6 text-slate-600'>
              The stack is designed for single-node deployment today with clean
              boundaries for later scale-out.
            </p>
          </article>
        </div>
      </section>
    </main>
  );
}
