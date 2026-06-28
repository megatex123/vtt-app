/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  allowedDevOrigins: ['voicetotext.percubaan.com'],
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://voicetotext.percubaan.com',
  },
  async rewrites() {
    const backend = process.env.VTT_BACKEND_URL || 'http://localhost:5000'
    return [
      { source: '/transcribe', destination: `${backend}/api/transcribe` },
      { source: '/history', destination: `${backend}/api/history` },
      { source: '/history/:id', destination: `${backend}/api/history/:id` },
    ]
  },
}

module.exports = nextConfig
