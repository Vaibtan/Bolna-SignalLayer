import { redirect } from 'next/navigation';

import { getServerSessionUser } from '@/lib/server-auth';

export default async function Home(): Promise<never> {
  const currentUser = await getServerSessionUser();

  if (currentUser === null) {
    redirect('/login');
  }

  redirect('/deals');
}
