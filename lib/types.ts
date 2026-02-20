/** Payload sent to POST /api/generate */
export interface GenerateRequest {
  company_name:   string
  document_title: string
  copy_text:      string
  page_size:      'a4' | 'letter'
  footer_text:    string
  file_urls:      string[]
  use_ai:         boolean
}

/** UI generation status */
export type GenStatus =
  | 'idle'
  | 'uploading'
  | 'analyzing'
  | 'generating'
  | 'done'
  | 'error'

/** A brand material file tracked in the UI */
export interface BrandFile {
  file:     File
  preview:  string   // Object URL for thumbnail
  isLogo:   boolean  // True only for the first file
}
