'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ApiError } from '@/lib/api-client';
import { Deal, listDeals } from '@/lib/deals';

export default function DealsPage() {
  const router = useRouter();
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listDeals()
      .then(setDeals)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          router.push('/login');
        }
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <main className='flex min-h-screen items-center justify-center bg-slate-50'>
        <p className='text-slate-500'>Loading deals...</p>
      </main>
    );
  }

  return (
    <main className='min-h-screen bg-[radial-gradient(circle_at_top,_#fff7ed,_#e2e8f0_55%,_#cbd5e1)] px-6 py-10'>
      <div className='mx-auto max-w-5xl'>
        <div className='flex items-center justify-between'>
          <div>
            <p className='text-sm font-semibold uppercase tracking-[0.24em] text-orange-600'>
              DealGraph Voice OS
            </p>
            <h1 className='mt-1 text-3xl font-semibold text-slate-950'>
              Deals
            </h1>
          </div>
          <Link
            href='/deals/new'
            className='rounded-lg bg-orange-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-700'
          >
            New Deal
          </Link>
        </div>

        {deals.length === 0 ? (
          <div className='mt-12 rounded-2xl border border-slate-200 bg-white/75 p-10 text-center backdrop-blur'>
            <p className='text-slate-500'>
              No deals yet.{' '}
              <Link
                href='/deals/new'
                className='font-medium text-orange-600 underline'
              >
                Create your first deal
              </Link>{' '}
              to get started.
            </p>
          </div>
        ) : (
          <div className='mt-8 grid gap-4'>
            {deals.map((deal) => (
              <Link
                key={deal.id}
                href={`/deals/${deal.id}`}
                className='rounded-2xl border border-slate-200 bg-white/75 p-6 backdrop-blur transition hover:border-orange-300 hover:shadow-md'
              >
                <div className='flex items-start justify-between'>
                  <div>
                    <h2 className='text-lg font-semibold text-slate-950'>
                      {deal.name}
                    </h2>
                    <p className='mt-1 text-sm text-slate-600'>
                      {deal.account_name}
                    </p>
                  </div>
                  <span className='rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700'>
                    {deal.stage}
                  </span>
                </div>
                {deal.summary_current && (
                  <p className='mt-3 text-sm leading-6 text-slate-600'>
                    {deal.summary_current}
                  </p>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
