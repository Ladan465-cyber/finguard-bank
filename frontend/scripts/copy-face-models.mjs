import { cpSync, existsSync, mkdirSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const src = join(__dirname, '..', 'node_modules', '@vladmandic', 'face-api', 'model')
const dest = join(__dirname, '..', 'public', 'models')

if (existsSync(src)) {
  mkdirSync(dest, { recursive: true })
  cpSync(src, dest, { recursive: true })
  console.log('[face-api] Model weights copied to public/models — face verification will work offline.')
} else {
  console.warn(
    '[face-api] Could not find model weights in node_modules/@vladmandic/face-api/model.\n' +
    '           Face verification pages will fail to load their models until this is fixed.\n' +
    '           Try: npm install @vladmandic/face-api, then re-run: node scripts/copy-face-models.mjs'
  )
}