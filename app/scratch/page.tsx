'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import {
  Sparkles, Download, FileText, AlertCircle,
  Loader2, CheckCircle2, Image as ImageIcon, Wand2, ArrowLeft,
} from 'lucide-react'
import DropZone from '@/components/DropZone'
import type { BrandFile, GenStatus } from '@/lib/types'

// ── Status helpers ─────────────────────────────────────────────────────────────

const STATUS_STEPS: { key: GenStatus; label: string }[] = [
  { key: 'uploading',  label: 'Encoding brand materials' },
  { key: 'analyzing',  label: 'AI analysing your brand'  },
  { key: 'generating', label: 'Building your PDF'        },
]

const LOADING_STATUSES: GenStatus[] = ['uploading', 'analyzing', 'generating']

// ── File helper ────────────────────────────────────────────────────────────────

const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.readAsDataURL(file)
    reader.onload  = () => resolve(reader.result as string)
    reader.onerror = error => reject(error)
  })
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function ScratchPage() {
  const router = useRouter()

  // ── Form state ──────────────────────────────────────────────────────────────
  const [brandFiles,    setBrandFiles]    = useState<BrandFile[]>([])
  const [companyName,   setCompanyName]   = useState('')
  const [documentTitle, setDocumentTitle] = useState('')
  const [copyText,      setCopyText]      = useState('')
  const [pageSize,      setPageSize]      = useState<'a4' | 'letter'>('letter')
  const [footerText,    setFooterText]    = useState('')

  // ── Generation state ────────────────────────────────────────────────────────
  const [status,       setStatus]       = useState<GenStatus>('idle')
  const [pdfBlob,      setPdfBlob]      = useState<Blob | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const isLoading   = LOADING_STATUSES.includes(status)
  const canGenerate = (copyText.trim().length > 0 || brandFiles.length > 0) && !isLoading

  // ── Generate handler ────────────────────────────────────────────────────────
  const handleGenerate = useCallback(async () => {
    try {
      setStatus('uploading')
      setErrorMessage(null)
      setPdfBlob(null)

      const fileData: string[] = []
      for (const bf of brandFiles) {
        fileData.push(await fileToBase64(bf.file))
      }

      setStatus('analyzing')
      setStatus('generating')

      const res = await fetch('/api/generate', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name:   companyName,
          document_title: documentTitle,
          copy_text:      copyText,
          page_size:      pageSize,
          footer_text:    footerText,
          file_data:      fileData,
          use_ai:         true,
        }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        throw new Error(err.error || `HTTP ${res.status}`)
      }

      setPdfBlob(await res.blob())
      setStatus('done')
    } catch (err: unknown) {
      setStatus('error')
      setErrorMessage(err instanceof Error ? err.message : 'An unexpected error occurred.')
    }
  }, [brandFiles, companyName, documentTitle, copyText, pageSize, footerText])

  // ── Download handler ────────────────────────────────────────────────────────
  const handleDownload = useCallback(() => {
    if (!pdfBlob) return
    const url  = URL.createObjectURL(pdfBlob)
    const a    = document.createElement('a')
    a.href     = url
    const slug = (documentTitle || companyName || 'document')
                   .toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
    a.download = `${slug || 'branded_form'}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  }, [pdfBlob, documentTitle, companyName])

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen px-4 py-14 max-w-5xl mx-auto">

      {/* Back link */}
      <button
        onClick={() => router.push('/')}
        className="flex items-center gap-1.5 text-[#8085a4] text-sm mb-10
                   hover:text-white transition-colors duration-150"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="text-center mb-14">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full
                        bg-violet-500/10 border border-violet-500/20
                        text-violet-300 text-xs font-semibold tracking-widest uppercase mb-6">
          <Sparkles className="w-3 h-3" />
          AI-Powered Brand Intelligence
        </div>

        <h1 className="text-5xl font-extrabold tracking-tight text-white mb-4
                       bg-gradient-to-br from-white to-slate-400 bg-clip-text text-transparent">
          Branded PDF Creator
        </h1>
        <p className="text-[#8085a4] text-lg max-w-lg mx-auto leading-relaxed">
          Drop your logo, describe your form — get a pixel-perfect, fillable PDF
          that matches your brand identity.
        </p>
      </header>

      {/* ── Two-panel grid ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8">

        {/* LEFT: Brand materials */}
        <div className="card flex flex-col gap-5">
          <PanelHeader
            icon={<ImageIcon className="w-4 h-4 text-violet-400" />}
            iconBg="bg-violet-500/15"
            title="Brand Materials"
            subtitle="Logo + inspiration images"
          />

          <DropZone
            files={brandFiles}
            onFilesChange={setBrandFiles}
            disabled={isLoading}
          />

          <p className="text-xs text-[#4a4f6a] leading-relaxed">
            The <span className="text-violet-400 font-medium">first image</span> is
            used as the logo header. All images are analysed by AI for colours, style
            and tone — no manual colour-picking required.
          </p>
        </div>

        {/* RIGHT: Document details */}
        <div className="card flex flex-col gap-4">
          <PanelHeader
            icon={<FileText className="w-4 h-4 text-blue-400" />}
            iconBg="bg-blue-500/15"
            title="Document Details"
            subtitle="Tell the AI what to build"
          />

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Company Name</label>
              <input
                className="field"
                placeholder="Acme Corporation"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <div>
              <label className="label">Document Title</label>
              <input
                className="field"
                placeholder="Client Intake Form"
                value={documentTitle}
                onChange={e => setDocumentTitle(e.target.value)}
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="flex-1 flex flex-col">
            <label className="label">
              Describe your form
              <span className="text-violet-400 ml-1">*</span>
            </label>
            <textarea
              className="field flex-1 resize-none min-h-[140px]"
              placeholder={
                'e.g. We need a client intake form with:\n' +
                '• Contact details (name, email, phone)\n' +
                '• Project description and budget range\n' +
                '• Preferred timeline (dropdown)\n' +
                '• Terms & conditions checkbox\n' +
                '• Signature block at the end'
              }
              value={copyText}
              onChange={e => setCopyText(e.target.value)}
              disabled={isLoading}
            />
            <p className="text-xs text-[#4a4f6a] mt-1.5">
              AI will structure this into sections and choose the right field types.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Page Size</label>
              <select
                className="field"
                value={pageSize}
                onChange={e => setPageSize(e.target.value as 'a4' | 'letter')}
                disabled={isLoading}
              >
                <option value="a4">A4 (210 × 297 mm)</option>
                <option value="letter">US Letter (8.5 × 11 in)</option>
              </select>
            </div>
            <div>
              <label className="label">Footer Text <span className="normal-case font-normal">(optional)</span></label>
              <input
                className="field"
                placeholder="Acme Corp · Confidential · 2026"
                value={footerText}
                onChange={e => setFooterText(e.target.value)}
                disabled={isLoading}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── Action area ─────────────────────────────────────────────────────── */}
      <div className="flex flex-col items-center gap-5">

        <button
          className="btn-primary text-base px-10 py-4"
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
              <Wand2 className="w-4 h-4" />
              Generate Branded PDF
            </>
          )}
        </button>

        {isLoading && (
          <div className="flex items-center gap-3 animate-fade-in">
            {STATUS_STEPS.map((step, idx) => {
              const currentIdx = STATUS_STEPS.findIndex(s => s.key === status)
              const isDone   = idx < currentIdx
              const isActive = idx === currentIdx
              return (
                <div key={step.key} className="flex items-center gap-2">
                  {idx > 0 && (
                    <div className={`h-px w-6 ${isDone ? 'bg-violet-500' : 'bg-white/10'}`} />
                  )}
                  <div className="flex items-center gap-1.5">
                    <div className={`step-badge ${
                      isDone   ? 'border-violet-500 bg-violet-500/20 text-violet-300' :
                      isActive ? 'border-violet-400 bg-violet-400/10 text-violet-300' :
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

        {status === 'done' && pdfBlob && (
          <div className="flex flex-col items-center gap-3 animate-fade-in">
            <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium">
              <CheckCircle2 className="w-4 h-4" />
              Your PDF is ready!
            </div>
            <button className="btn-download text-base px-10 py-4" onClick={handleDownload}>
              <Download className="w-4 h-4" />
              Download PDF
            </button>
          </div>
        )}

        {status === 'error' && errorMessage && (
          <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20
                          text-red-300 text-sm rounded-xl px-5 py-4 max-w-lg animate-fade-in">
            <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold mb-0.5">Generation failed</p>
              <p className="text-red-400/80">{errorMessage}</p>
            </div>
          </div>
        )}
      </div>

      {/* ── How it works ────────────────────────────────────────────────────── */}
      <section className="mt-24 border-t border-white/5 pt-16">
        <p className="text-center text-xs font-semibold tracking-widest uppercase
                      text-[#4a4f6a] mb-10">
          How it works
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <HowItWorksStep number="01" title="Upload brand materials"
            description="Drop your logo and any inspiration images. The AI reads colours, style and tone directly from the visuals." />
          <HowItWorksStep number="02" title="Describe your form"
            description="Write in plain English what the form needs to capture. The AI structures it into sections, fields and smart defaults." />
          <HowItWorksStep number="03" title="Download your PDF"
            description="A fully branded, fillable PDF is generated in seconds — ready to send, embed, or print." />
        </div>
      </section>

    </main>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function PanelHeader({ icon, iconBg, title, subtitle }: {
  icon: React.ReactNode; iconBg: string; title: string; subtitle: string
}) {
  return (
    <div className="flex items-center gap-3">
      <div className={`w-9 h-9 rounded-xl ${iconBg} flex items-center justify-center shrink-0`}>
        {icon}
      </div>
      <div>
        <p className="font-semibold text-white leading-tight">{title}</p>
        <p className="text-xs text-[#8085a4]">{subtitle}</p>
      </div>
    </div>
  )
}

function HowItWorksStep({ number, title, description }: {
  number: string; title: string; description: string
}) {
  return (
    <div className="card hover:border-violet-500/25 transition-colors duration-200">
      <p className="text-3xl font-black text-violet-500/30 mb-3 leading-none">{number}</p>
      <p className="font-semibold text-white mb-2">{title}</p>
      <p className="text-sm text-[#8085a4] leading-relaxed">{description}</p>
    </div>
  )
}
