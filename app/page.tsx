'use client'

import { useRouter } from 'next/navigation'
import { Sparkles, Wand2, Upload, ArrowRight, CheckCircle2 } from 'lucide-react'

// ── Welcome / mode-select page ─────────────────────────────────────────────────

export default function Home() {
  const router = useRouter()

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 py-14">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="text-center mb-16">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full
                        bg-violet-500/10 border border-violet-500/20
                        text-violet-300 text-xs font-semibold tracking-widest uppercase mb-6">
          <Sparkles className="w-3 h-3" />
          AI-Powered PDF Forms
        </div>

        <h1 className="text-5xl font-extrabold tracking-tight text-white mb-4
                       bg-gradient-to-br from-white to-slate-400 bg-clip-text text-transparent">
          PDF Creator
        </h1>
        <p className="text-[#8085a4] text-lg max-w-md mx-auto leading-relaxed">
          How would you like to create your fillable PDF?
        </p>
      </header>

      {/* ── Mode Cards ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 w-full max-w-2xl">

        {/* Build from Scratch */}
        <button
          onClick={() => router.push('/scratch')}
          className="group card text-left flex flex-col gap-4 cursor-pointer
                     hover:border-violet-500/50 hover:bg-[#1a1e38]
                     transition-all duration-200 hover:-translate-y-0.5
                     hover:shadow-[0_8px_40px_rgba(124,58,237,0.18)]"
        >
          <div className="w-12 h-12 rounded-2xl bg-violet-500/15 flex items-center
                          justify-center group-hover:bg-violet-500/25 transition-colors duration-200">
            <Wand2 className="w-6 h-6 text-violet-400" />
          </div>

          <div className="flex-1">
            <p className="font-bold text-white text-lg mb-1.5 leading-tight">
              Build from Scratch
            </p>
            <p className="text-sm text-[#8085a4] leading-relaxed">
              Upload your logo, describe your form in plain
              English — AI designs and generates a branded,
              fillable PDF for you.
            </p>
          </div>

          <ul className="space-y-1.5">
            {[
              'AI-generated layout & branding',
              'Automatic colour extraction',
              'Smart field structuring',
            ].map(f => (
              <li key={f} className="flex items-center gap-2 text-xs text-[#8085a4]">
                <CheckCircle2 className="w-3.5 h-3.5 text-violet-500 shrink-0" />
                {f}
              </li>
            ))}
          </ul>

          <div className="flex items-center gap-1.5 text-violet-400 text-sm font-semibold
                          group-hover:gap-2.5 transition-all duration-200">
            Get started <ArrowRight className="w-4 h-4" />
          </div>
        </button>

        {/* I Have a Template */}
        <button
          onClick={() => router.push('/template')}
          className="group card text-left flex flex-col gap-4 cursor-pointer
                     hover:border-emerald-500/50 hover:bg-[#1a1e38]
                     transition-all duration-200 hover:-translate-y-0.5
                     hover:shadow-[0_8px_40px_rgba(16,185,129,0.15)]"
        >
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/15 flex items-center
                          justify-center group-hover:bg-emerald-500/25 transition-colors duration-200">
            <Upload className="w-6 h-6 text-emerald-400" />
          </div>

          <div className="flex-1">
            <p className="font-bold text-white text-lg mb-1.5 leading-tight">
              I Have a Template
            </p>
            <p className="text-sm text-[#8085a4] leading-relaxed">
              Already designed your form in Canva, Word, or similar?
              Upload it as a <strong className="text-white font-medium">PNG or PDF</strong> — AI detects every
              input area and makes them live, fillable fields.
            </p>
          </div>

          <ul className="space-y-1.5">
            {[
              'Accepts PNG and PDF templates',
              'Detects boxed fields & implied areas',
              'Preserves your exact visual design',
            ].map(f => (
              <li key={f} className="flex items-center gap-2 text-xs text-[#8085a4]">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                {f}
              </li>
            ))}
          </ul>

          <div className="flex items-center gap-1.5 text-emerald-400 text-sm font-semibold
                          group-hover:gap-2.5 transition-all duration-200">
            Upload template <ArrowRight className="w-4 h-4" />
          </div>
        </button>

      </div>

    </main>
  )
}
