/**
 * GET /api/supabase-config
 *
 * Returns the Supabase project URL and anon key to the browser.
 * Reads from server-side env vars so this works regardless of whether
 * variables are prefixed with NEXT_PUBLIC_ or not in the Vercel dashboard.
 *
 * The anon key is intentionally public (it's a Row-Level-Security key
 * designed to be shipped to browsers). Never expose the service_role key here.
 */

import { NextResponse } from 'next/server'

export async function GET() {
  // Accept either naming convention
  const url = (
    process.env.NEXT_PUBLIC_SUPABASE_URL ||
    process.env.SUPABASE_URL             ||
    ''
  ).trim()

  const anonKey = (
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    process.env.SUPABASE_ANON_KEY             ||
    process.env.SUPABASE_KEY                  ||
    ''
  ).trim()

  if (!url || !anonKey) {
    return NextResponse.json(
      { error: 'Supabase environment variables not configured on this server.' },
      { status: 500 },
    )
  }

  return NextResponse.json({ url, anonKey })
}
