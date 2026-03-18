// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>
//
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

/**
 * Handle POST requests to logout by deleting the session cookie.
 *
 * @returns {Promise<NextResponse>} The Next.js response with success message
 */
export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete('iqoqo_session');

  return NextResponse.json({ success: true, message: 'Logged out successfully' });
}
