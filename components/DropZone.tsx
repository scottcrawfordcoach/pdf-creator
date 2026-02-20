'use client'

import { useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { UploadCloud, X, Star } from 'lucide-react'
import type { BrandFile } from '@/lib/types'

interface DropZoneProps {
  files:          BrandFile[]
  onFilesChange:  (files: BrandFile[]) => void
  disabled?:      boolean
}

const MAX_FILES  = 5
const ACCEPT_IMG = { 'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'] }

export default function DropZone({ files, onFilesChange, disabled }: DropZoneProps) {

  // Build BrandFile objects from newly dropped File objects
  const onDrop = useCallback(
    (accepted: File[]) => {
      const remaining = MAX_FILES - files.length
      const toAdd = accepted.slice(0, remaining).map((file, i) => ({
        file,
        preview: URL.createObjectURL(file),
        isLogo:  files.length === 0 && i === 0,
      }))
      onFilesChange([...files, ...toAdd])
    },
    [files, onFilesChange]
  )

  // Revoke object URLs when files are removed to prevent memory leaks
  useEffect(() => {
    return () => files.forEach(bf => URL.revokeObjectURL(bf.preview))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept:   ACCEPT_IMG,
    disabled: disabled || files.length >= MAX_FILES,
    maxFiles: MAX_FILES,
  })

  const removeFile = (index: number) => {
    const updated = files.filter((_, i) => i !== index)
    // Re-flag the first remaining file as the logo
    const remapped = updated.map((bf, i) => ({ ...bf, isLogo: i === 0 }))
    onFilesChange(remapped)
  }

  return (
    <div className="space-y-3">

      {/* Drop target */}
      <div
        {...getRootProps()}
        className={[
          'relative rounded-xl border-2 border-dashed p-8 text-center',
          'transition-all duration-200 select-none',
          disabled || files.length >= MAX_FILES
            ? 'opacity-50 cursor-not-allowed border-white/8'
            : isDragActive
              ? 'border-violet-400 bg-violet-500/10 cursor-copy'
              : 'border-white/10 hover:border-violet-500/40 hover:bg-white/[0.02] cursor-pointer',
        ].join(' ')}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center gap-3 pointer-events-none">
          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center
                           transition-colors duration-200
                           ${isDragActive ? 'bg-violet-500/25' : 'bg-white/5'}`}>
            <UploadCloud className={`w-6 h-6 ${isDragActive ? 'text-violet-300' : 'text-[#8085a4]'}`} />
          </div>

          {isDragActive ? (
            <p className="text-violet-300 font-medium text-sm">Drop to add</p>
          ) : (
            <>
              <p className="text-white font-medium text-sm">
                {files.length === 0 ? 'Drop your logo here' : 'Add more images'}
              </p>
              <p className="text-[#4a4f6a] text-xs">
                PNG, JPG, WebP, GIF · up to {MAX_FILES} files
              </p>
            </>
          )}
        </div>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <ul className="space-y-2">
          {files.map((bf, index) => (
            <li
              key={bf.preview}
              className="flex items-center gap-3 bg-white/[0.04] border border-white/8
                         rounded-xl px-3 py-2.5 group"
            >
              {/* Thumbnail */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={bf.preview}
                alt={bf.file.name}
                className="w-9 h-9 object-cover rounded-lg shrink-0 bg-white/5"
              />

              {/* Name + logo badge */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white truncate">{bf.file.name}</p>
                <p className="text-xs text-[#4a4f6a]">
                  {(bf.file.size / 1024).toFixed(0)} KB
                </p>
              </div>

              {bf.isLogo && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                                 bg-violet-500/15 border border-violet-500/25
                                 text-violet-300 text-[10px] font-semibold shrink-0">
                  <Star className="w-2.5 h-2.5 fill-current" />
                  Logo
                </span>
              )}

              {/* Remove button */}
              <button
                onClick={() => removeFile(index)}
                disabled={disabled}
                className="w-6 h-6 rounded-lg flex items-center justify-center
                           text-[#4a4f6a] hover:text-red-400 hover:bg-red-500/10
                           opacity-0 group-hover:opacity-100
                           disabled:pointer-events-none transition-all duration-150 shrink-0"
                aria-label={`Remove ${bf.file.name}`}
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Counter */}
      {files.length > 0 && (
        <p className="text-xs text-[#4a4f6a] text-right">
          {files.length} / {MAX_FILES} images
        </p>
      )}
    </div>
  )
}
