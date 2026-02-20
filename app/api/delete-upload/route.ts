/**
 * DELETE /api/delete-upload
 * Body: { "path": "templates/xxx.pdf" }
 *
 * Deletes a file from Supabase Storage using the service-role key.
 * Called fire-and-forget after the conversion completes.
 */
import { NextResponse } from 'next/server'

export async function DELETE(req: Request) {
  const { path } = await req.json().catch(() => ({ path: '' }))
  if (!path) return NextResponse.json({ ok: false }, { status: 400 })

  const supabaseUrl    = process.env.SUPABASE_URL    || process.env.NEXT_PUBLIC_SUPABASE_URL    || ''
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY || ''

  if (!supabaseUrl || !serviceRoleKey) {
    return NextResponse.json({ ok: false }, { status: 500 })
  }

  await fetch(`${supabaseUrl}/storage/v1/object/pdf-creator/${path}`, {
    method:  'DELETE',
    headers: { 'Authorization': `Bearer ${serviceRoleKey}` },
  }).catch(() => { /* ignore */ })

  return NextResponse.json({ ok: true })
}
