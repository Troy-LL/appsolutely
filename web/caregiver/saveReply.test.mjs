// Checks saveReply (src/data/hub.ts): the yellow-card reply asks the hub to play it now.
// No hub, no browser: fetch is faked and Vite loads the .ts file.
//   cd web/caregiver && node saveReply.test.mjs
import { createServer } from 'vite'
import { fileURLToPath } from 'node:url'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

let failed = 0
function check(name, ok, detail = '') {
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  (${detail})` : ''}`)
  if (!ok) failed++
}

// Record every fetch instead of calling a hub.
const calls = []
globalThis.fetch = async (url, init) => {
  calls.push({ url, init })
  return new Response(JSON.stringify({ id: 'kumain-na-ba-ako' }), { status: 200 })
}

const root = fileURLToPath(new URL('.', import.meta.url))
const vite = await createServer({
  root, logLevel: 'silent', appType: 'custom', cacheDir: join(tmpdir(), 'sino-caregiver-test-vite'),
  server: { middlewareMode: true, hmr: false, watch: null },
})
const audio = new Blob(['x'], { type: 'audio/mp4' })
const opts = { transcript: 'Kumain na ba ako?', speaker: 'Donita', audio }

try {
  // Real hub mode: USING_HUB reads ?feed=hub when hub.ts loads.
  globalThis.location = { search: '?feed=hub', protocol: 'http:', host: 'localhost' }
  let hub = await vite.ssrLoadModule('/src/data/hub.ts')
  await hub.saveReply(opts)
  const form = calls[0]?.init?.body
  check('one POST /questions', calls.length === 1 && calls[0].url === '/questions' && calls[0].init.method === 'POST')
  check('play_now is "1"', form instanceof FormData && form.get('play_now') === '1', String(form?.get?.('play_now')))
  check('reply_audio still sent', form?.get('reply_audio') instanceof Blob)

  // Fake feed: returns 'fake' and posts nothing.
  calls.length = 0
  globalThis.location = { search: '', protocol: 'http:', host: 'localhost' }
  vite.moduleGraph.invalidateAll()
  hub = await vite.ssrLoadModule('/src/data/hub.ts')
  const res = await hub.saveReply(opts)
  check('fake feed returns "fake" and posts nothing', res === 'fake' && calls.length === 0)
} finally {
  await vite.close()
}

console.log(failed ? `${failed} failed` : 'all passed')
process.exit(failed ? 1 : 0)
