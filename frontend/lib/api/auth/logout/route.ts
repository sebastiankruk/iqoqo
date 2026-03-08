import { cookies } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const cookieStore = await cookies();
  cookieStore.delete('iqoqo_session');

  return NextResponse.json({ success: true, message: 'Logged out successfully' });
}
