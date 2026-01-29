const DEFAULT_BASE_URL = 'https://lockin-dev.vercel.app'
const statusEl = document.getElementById('status')
const lockInButton = document.getElementById('lockIn')

const setStatus = (message) => {
  statusEl.textContent = message
}

const getCurrentTabUrl = async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  return tab?.url
}

const openLockIn = async () => {
  setStatus('Checking current tab...')
  const url = await getCurrentTabUrl()
  if (!url || (!url.includes('youtube.com') && !url.includes('youtu.be'))) {
    setStatus('Open a YouTube video to start.')
    return
  }

  const baseUrl = DEFAULT_BASE_URL
  const target = `${baseUrl.replace(/\/$/, '')}/?video=${encodeURIComponent(url)}`

  await chrome.tabs.create({ url: target })
  setStatus('Launching LockIn...')
}

lockInButton.addEventListener('click', () => {
  openLockIn().catch(() => setStatus('Unable to open LockIn.'))
})
