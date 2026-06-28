import fs from 'fs'
import path from 'path'

// Absolute path to the Obsidian vault directory on this server
const OBSIDIAN_DIR = path.join(process.cwd(), '..', '..', 'obsidian', 'AI-Dev-Agent')

export default function handler(req, res) {
  // CORS — allow the dashboard origin so it can call this endpoint directly
  res.setHeader('Access-Control-Allow-Origin', 'https://dashboard.percubaan.com')
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')

  if (req.method === 'OPTIONS') return res.status(200).end()
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' })

  const { file, content } = req.body || {}
  if (!file || !content) {
    return res.status(400).json({ error: 'Need "file" and "content" fields' })
  }

  // Strip any path traversal — only allow filenames, not relative paths
  const safeName = path.basename(file)
  const filePath = path.join(OBSIDIAN_DIR, safeName)

  try {
    fs.appendFileSync(filePath, content, 'utf-8')
    return res.json({ ok: true, file: safeName })
  } catch (err) {
    return res.status(500).json({ error: err.message })
  }
}
