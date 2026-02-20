'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import {
  Upload, Download, AlertCircle, Loader2,
  CheckCircle2, ArrowLeft, Sparkles, ScanSearch,
} from 'lucide-react'
import SingleDropZone from '@/components/SingleDropZone'

// ── Status type ────────────────────────────────────────────────────────────────

type ConvertStatus = 'idle' | 'uploading' | 'detecting' | 'building' | 'done' | 'error'

const STATUS_STEPS: { key: ConvertStatus; label: string }[] = [
  { key: 'uploading', label: 'Uploading template'     },
  { key: 'detecting', label: 'AI detecting fields'    },
  { key: 'building',  label: 'Building fillable PDF'  },
]

const LOADING_STATUSES: ConvertStatus[] = ['uploading', 'detecting', 'building']

// ── Page ───────────────────────────────────────────────────────────────────────

export default function TemplatePage() {
  const router = useRouter()

  const [templateFile,  setTemplateFile]  = useState<File | null>(null)
  const [documentTitle, setDocumentTitle] = useState('')
  const [status,        setStatus]        = useState<ConvertStatus>('idle')
  const [pdfBlob,       setPdfBlob]       = useState<Blob | null>(null)
  const [errorMessage,  setErrorMessage]  = useState<string | null>(null)
  const [fieldCount,    setFieldCount]    = useState<number | null>(null)

  const isLoading   = LOADING_STATUSES.includes(status)
  const canGenerate = !!templateFile && !isLoading

  // ── Convert handler ─────────────────────────────────────────────────────────
  const handleGenerate = useCallback(async () => {
    if (!templateFile) return
    const ext  = templateFile.name.split('.').pop() || 'bin'
    const path = `templates/${Date.now()}-${Math.random().toString(36).slice(2)}.${ext}`
    let supabaseUrl = ''
    let supabaseKey = ''
    try {
      setStatus('uploading')

      // Fetch Supabase creds server-side so naming convention doesn't matter
      const cfgRes = await fetch('/api/supabase-config')
      if (!cfgRes.ok) throw new Error('Could not load storage configuration')
      const cfg = await cfgRes.json()
      supabaseUrl = cfg.url
      supabaseKey = cfg.anonKey
      setErrorMessage(null)
      setPdfBlob(null)
      setFieldCount(null)

      // Upload directly to Supabase Storage — avoids Vercel's 4.5 MB body limit
      const uploadRes = await fetch(
        `${supabaseUrl}/storage/v1/object/pdf-creator/${path}`,
        {
          method:  'POST',
          headers: {
            'Authorization': `Bearer ${supabaseKey}`,
            'Content-Type':  templateFile.type || 'application/octet-stream',
          },
          body: templateFile,
        },
      )
      if (!uploadRes.ok) {
        const text = await uploadRes.text().catch(() => `HTTP ${uploadRes.status}`)
        throw new Error(`Upload failed: ${text}`)
      }

      const fileUrl = `${supabaseUrl}/storage/v1/object/public/pdf-creator/${path}`

      setStatus('detecting')

      const res = await fetch('/api/convert_template', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_url:       fileUrl,
          document_title: documentTitle || templateFile.name.replace(/\.(png|pdf)$/i, ''),
        }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        throw new Error(err.error || `HTTP ${res.status}`)
      }

      setStatus('building')

      const count = parseInt(res.headers.get('X-Field-Count') ?? '0', 10)
      if (count) setFieldCount(count)

      setPdfBlob(await res.blob())
      setStatus('done')
    } catch (err: unknown) {
      setStatus('error')
      setErrorMessage(err instanceof Error ? err.message : 'An unexpected error occurred.')
    } finally {
      // Clean up the staging file (fire-and-forget)
      fetch(
        `${supabaseUrl}/storage/v1/object/pdf-creator/${path}`,
        { method: 'DELETE', headers: { 'Authorization': `Bearer ${supabaseKey}` } },
      ).catch(() => { /* ignore */ })
    }
  }, [templateFile, documentTitle])

  // ── Download handler ────────────────────────────────────────────────────────
  const handleDownload = useCallback(() => {
    if (!pdfBlob) return
    const url  = URL.createObjectURL(pdfBlob)
    const a    = document.createElement('a')
    a.href     = url
    const slug = (documentTitle || templateFile?.name.replace(/\.(png|pdf)$/i, '') || 'form')
                   .toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
    a.download = `${slug || 'fillable_form'}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  }, [pdfBlob, documentTitle, templateFile])

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen px-4 py-14 max-w-2xl mx-auto">

      {/* Back link */}
      <button
        onClick={() => router.push('/')}
        className="flex items-center gap-1.5 text-[#8085a4] text-sm mb-10
                   hover:text-white transition-colors duration-150"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="text-center mb-12">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full
                        bg-emerald-500/10 border border-emerald-500/20
                        text-emerald-300 text-xs font-semibold tracking-widest uppercase mb-6">
          <ScanSearch className="w-3 h-3" />
          Template Converter
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white mb-4
                       bg-gradient-to-br from-white to-slate-400 bg-clip-text text-transparent">
          Template → Fillable PDF
        </h1>
        <p className="text-[#8085a4] text-base max-w-md mx-auto leading-relaxed">
          Upload your form template as a <span className="text-emerald-300 font-medium">PNG or PDF</span>.
          AI detects every input area — including boxed fields <em>and</em> blank spaces
          beneath labels — and makes them all live, fillable fields.
        </p>
      </header>

      {/* ── Main card ──────────────────────────────────────────────────────── */}
      <div className="card flex flex-col gap-6">

        {/* Section header */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/15 flex items-center justify-center shrink-0">
            <Upload className="w-4 h-4 text-emerald-400" />
          </div>
          <div>
            <p className="font-semibold text-white leading-tight">Your Template</p>
          <p className="text-xs text-[#8085a4]">PNG or PDF from Canva, Word, Figma, etc.</p>
          </div>
        </div>

        {/* Drop zone */}
        <SingleDropZone
          file={templateFile}
          onFileChange={setTemplateFile}
          disabled={isLoading}
        />

        <p className="text-xs text-[#4a4f6a] leading-relaxed -mt-2">
          Export from <span className="text-emerald-400 font-medium">Canva, Word, Google Docs, Figma</span>,
          or any tool as a PNG or PDF. AI detects both
          explicitly-bordered boxes <em>and</em> blank areas beneath labels like
          &ldquo;Full Name:&rdquo; or &ldquo;Notes:&rdquo; — so every fillable space gets a live field
          whether or not it has a visible border.
        </p>

        {/* Optional title */}
        <div>
          <label className="label">
            Document Title <span className="normal-case font-normal">(optional)</span>
          </label>
          <input
            className="field"
            placeholder="Client Intake Form"
            value={documentTitle}
            onChange={e => setDocumentTitle(e.target.value)}
            disabled={isLoading}
          />
        </div>

        {/* Generate button */}
        <button
          className="btn-emerald text-base px-10 py-4 self-center"
          onClick={handleGenerate}
          disabled={!canGenerate}
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {STATUS_STEPS.find(s => s.key === status)?.label ?? 'Working…'}
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Generate Fillable PDF
            </>
          )}
        </button>

        {/* Progress steps */}
        {isLoading && (
          <div className="flex items-center justify-center gap-3 animate-fade-in">
            {STATUS_STEPS.map((step, idx) => {
              const currentIdx = STATUS_STEPS.findIndex(s => s.key === status)
              const isDone   = idx < currentIdx
              const isActive = idx === currentIdx
              return (
                <div key={step.key} className="flex items-center gap-2">
                  {idx > 0 && (
                    <div className={`h-px w-6 ${isDone ? 'bg-emerald-500' : 'bg-white/10'}`} />
                  )}
                  <div className="flex items-center gap-1.5">
                    <div className={`step-badge ${
                      isDone   ? 'border-emerald-500 bg-emerald-500/20 text-emerald-300' :
                      isActive ? 'border-emerald-400 bg-emerald-400/10 text-emerald-300' :
                                 'border-white/10 bg-transparent text-[#4a4f6a]'
                    }`}>
                      {isDone ? <CheckCircle2 className="w-3 h-3" /> : idx + 1}
                    </div>
                    <span className={`text-xs ${isActive ? 'text-white' : 'text-[#4a4f6a]'}`}>
                      {step.label}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Success */}
        {status === 'done' && pdfBlob && (
          <div className="flex flex-col items-center gap-3 animate-fade-in">
            <div className="flex flex-col items-center gap-1">
              <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium">
                <CheckCircle2 className="w-4 h-4" />
                Your fillable PDF is ready!
              </div>
              {fieldCount !== null && fieldCount > 0 && (
                <p className="text-xs text-[#8085a4]">
                  {fieldCount} fillable field{fieldCount !== 1 ? 's' : ''} detected and added
                </p>
              )}
            </div>
            <button className="btn-download text-base px-10 py-4" onClick={handleDownload}>
              <Download className="w-4 h-4" />
              Download PDF
            </button>
          </div>
        )}

        {/* Error */}
        {status === 'error' && errorMessage && (
          <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20
                          text-red-300 text-sm rounded-xl px-5 py-4 animate-fade-in">
            <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold mb-0.5">Conversion failed</p>
              <p className="text-red-400/80">{errorMessage}</p>
            </div>
          </div>
        )}
      </div>

      {/* ── How it works ────────────────────────────────────────────────────── */}
      <section className="mt-16 border-t border-white/5 pt-12">
        <p className="text-center text-xs font-semibold tracking-widest uppercase
                      text-[#4a4f6a] mb-8">
          How it works
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              n: '01',
              title: 'Design your form',
              desc:  'Create your form in Canva, Word, Google Docs, or anywhere. Use boxes or simply labels — AI handles both.',
            },
            {
              n: '02',
              title: 'Upload PNG or PDF',
              desc:  'Drop the file here. AI scans each field box and every blank area beneath a label and infers its purpose.',
            },
            {
              n: '03',
              title: 'Get a live PDF',
              desc:  'Download a PDF that looks exactly like your design with every input — boxed or implied — now fillable.',
            },
          ].map(s => (
            <div key={s.n} className="card hover:border-emerald-500/25 transition-colors duration-200">
              <p className="text-3xl font-black text-emerald-500/25 mb-3 leading-none">{s.n}</p>
              <p className="font-semibold text-white mb-2">{s.title}</p>
              <p className="text-sm text-[#8085a4] leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

    </main>
  )
}
