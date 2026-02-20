/**
 * TEMPORARY — GET /api/debug-env
 * Lists the NAMES (not values) of every env var that contains the word
 * "supabase" (case-insensitive). Delete this file once the mystery is solved.
 */
import { NextResponse } from 'next/server'

export async function GET() {
  const keys = Object.keys(process.env)
    .filter(k => k.toLowerCase().includes('supabase'))
    .sort()

  const preview: Record<string, string> = {}
  for (const k of keys) {
    const v = process.env[k] ?? ''
    // Show first 12 chars so we can identify the value without fully exposing it
    preview[k] = v.slice(0, 12) + (v.length > 12 ? '…' : '')
  }

  return NextResponse.json({ keys, preview })
}
