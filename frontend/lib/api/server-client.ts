import { cookies } from 'next/headers';

	export async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
	  const cookieStore = await cookies();
	  const token = cookieStore.get('iqoqo_session')?.value;

	  const headers = new Headers(options.headers);
	  headers.set('Content-Type', 'application/json');

	  if (token) {
	    headers.set('Authorization', `Bearer ${token}`);
	  }

	  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${endpoint}`, {
	    ...options,
	    headers,
	  });

	  return res;
	}
