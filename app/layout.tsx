import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PDF Creator – AI-Powered Branded Forms',
  description:
    'Drop your logo and inspiration images, describe your form, and get a custom-branded fillable PDF in seconds.',
  openGraph: {
    title: 'PDF Creator',
    description: 'AI-powered branded PDF form generator',
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
