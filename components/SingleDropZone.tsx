'use client'

import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { UploadCloud, X, FileImage } from 'lucide-react'

interface SingleDropZoneProps {
  file:          File | null
  onFileChange:  (file: File | null) => void
  disabled?:     boolean
}

const ACCEPT_TEMPLATES = {
  'image/png':      ['.png'],
  'application/pdf': ['.pdf'],
}

export default function SingleDropZone({ file, onFileChange, disabled }: SingleDropZoneProps) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted[0]) onFileChange(accepted[0])
    },
    [onFileChange]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept:    ACCEPT_TEMPLATES,
    disabled:  disabled || !!file,
    maxFiles:  1,
    multiple:  false,
  })

  if (file) {
    return (
      <div className="relative rounded-xl border border-white/10 bg-white/[0.03] p-4
                      flex items-center gap-4 group">
        {/* Preview thumbnail — only possible for images, not PDFs */}
        <div className="w-14 h-14 rounded-lg overflow-hidden bg-white/5 shrink-0 flex items-center justify-center">
          {file.type === 'application/pdf' ? (
            <FileImage className="w-7 h-7 text-emerald-400/70" />
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={URL.createObjectURL(file)}
              alt="Template preview"
              className="w-full h-full object-contain"
            />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm text-white font-medium truncate">{file.name}</p>
          <p className="text-xs text-[#4a4f6a] mt-0.5">
            {(file.size / 1024).toFixed(0)} KB · {file.type === 'application/pdf' ? 'PDF' : 'PNG'}
          </p>
        </div>

        {!disabled && (
          <button
            type="button"
            onClick={() => onFileChange(null)}
            className="w-7 h-7 rounded-full bg-white/5 flex items-center justify-center
                       text-[#8085a4] hover:bg-red-500/15 hover:text-red-400
                       transition-colors duration-150 shrink-0"
            aria-label="Remove file"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    )
  }

  return (
    <div
      {...getRootProps()}
      className={[
        'relative rounded-xl border-2 border-dashed p-10 text-center',
        'transition-all duration-200 select-none',
        disabled
          ? 'opacity-50 cursor-not-allowed border-white/8'
          : isDragActive
            ? 'border-emerald-400 bg-emerald-500/10 cursor-copy'
            : 'border-white/10 hover:border-emerald-500/40 hover:bg-white/[0.02] cursor-pointer',
      ].join(' ')}
    >
      <input {...getInputProps()} />

      <div className="flex flex-col items-center gap-3 pointer-events-none">
        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center
                         transition-colors duration-200
                         ${isDragActive ? 'bg-emerald-500/25' : 'bg-white/5'}`}>
          {isDragActive
            ? <UploadCloud className="w-7 h-7 text-emerald-300" />
            : <FileImage   className="w-7 h-7 text-[#8085a4]"  />
          }
        </div>

        {isDragActive ? (
          <p className="text-emerald-300 font-medium text-sm">Drop your PNG here</p>
        ) : (
          <>
            <p className="text-white font-medium text-sm">
              Drop your template here
            </p>
            <p className="text-[#4a4f6a] text-xs">
              PNG or PDF · single page recommended
            </p>
          </>
        )}
      </div>
    </div>
  )
}
