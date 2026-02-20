/**
 * GET /api/get-upload-url?ext=pdf
 *
 * Creates a short-lived signed upload URL for Supabase Storage using the
 * service-role key (server-side only). The browser uses this URL to PUT
 * the file directly, bypassing RLS without exposing the service-role key.
 */
import { NextResponse } from 'next/server'

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const ext  = (searchParams.get('ext') || 'bin').replace(/[^a-z0-9]/gi, '')
  const path = `templates/${Date.now()}-${Math.random().toString(36).slice(2)}.${ext}`

  const supabaseUrl      = process.env.SUPABASE_URL      || process.env.NEXT_PUBLIC_SUPABASE_URL      || ''
  const serviceRoleKey   = process.env.SUPABASE_SERVICE_ROLE_KEY || ''

  if (!supabaseUrl || !serviceRoleKey) {
    return NextResponse.json({
      error:  'Storage not configured',
      hasUrl: !!supabaseUrl,
      hasSrk: !!serviceRoleKey,
    }, { status: 500 })
  }

  // Ask Supabase to create a signed upload URL for this path
  const signEndpoint = `${supabaseUrl}/storage/v1/object/sign/upload/pdf-creator/${path}`
  const res = await fetch(signEndpoint, {
    method:  'POST',
    headers: {
      'Authorization': `Bearer ${serviceRoleKey}`,
      'Content-Type':  'application/json',
    },
    body: JSON.stringify({ expiresIn: 300 }),
  })

  if (!res.ok) {
    const body = await res.text()
    return NextResponse.json({
      error:    `Supabase error (${res.status})`,
      detail:   body,
      endpoint: signEndpoint.replace(supabaseUrl, '[url]'),
    }, { status: 502 })
  }

  const json = await res.json()
  const token = json.token ?? json.signedToken ?? json.signed_url

  if (!token) {
    return NextResponse.json({ error: 'No token in Supabase response', raw: json }, { status: 502 })
  }

  // The browser will PUT to this URL with the raw file as the body
  const uploadUrl  = `${supabaseUrl}/storage/v1/object/upload/sign/pdf-creator/${path}?token=${token}`
  const publicUrl  = `${supabaseUrl}/storage/v1/object/public/pdf-creator/${path}`
  const deletePath = path

  return NextResponse.json({ uploadUrl, publicUrl, deletePath })
}
