const BASE_URL = 'https://lockin-dev.vercel.app'

// DOM refs
const $ = (id) => document.getElementById(id)
const userChip      = $('userChip')
const userAvatar    = $('userAvatar')
const userName      = $('userName')
const userCredits   = $('userCredits')
const guestBadge    = $('guestBadge')
const videoCard     = $('videoCard')
const videoThumb    = $('videoThumb')
const videoTitle    = $('videoTitle')
const urlSection    = $('urlSection')
const urlInputWrap  = $('urlInputWrap')
const urlInput      = $('urlInput')
const urlGoBtn      = $('urlGoBtn')
const urlPreview    = $('urlPreview')
const urlThumb      = $('urlThumb')
const urlPreviewTitle = $('urlPreviewTitle')
const creditInfo    = $('creditInfo')
const lockInBtn     = $('lockInBtn')
const ctaLabel      = $('ctaLabel')
const ctaSpinner    = $('ctaSpinner')
const signInBtn     = $('signInBtn')
const statusMsg     = $('statusMsg')

// ---- Helpers -----------------------------------------------------------

const show = (el)  => el.classList.remove('hidden')
const hide = (el)  => el.classList.add('hidden')
const setStatus = (msg, isErr = false) => {
  statusMsg.textContent = msg
  statusMsg.classList.toggle('err', isErr)
}

const extractVideoId = (url) => {
  try {
    const u = new URL(url)
    if (u.hostname === 'youtu.be') return u.pathname.slice(1).split('?')[0]
    return u.searchParams.get('v') || null
  } catch { return null }
}

const isWatchUrl = (url) => {
  if (!url) return false
  return (url.includes('youtube.com/watch') || url.includes('youtu.be/'))
}

// ---- Render ------------------------------------------------------------

const render = async () => {
  // 1. Get current tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  const url = tab?.url || ''
  const rawTitle = tab?.title || ''
  const cleanTitle = rawTitle.replace(/ - YouTube$/, '').trim()

  // 2. Get stored user from bridge
  const { lockinUser } = await chrome.storage.local.get('lockinUser')
  const isLoggedIn = !!(lockinUser?.email)

  // 3. Render auth chip
  if (isLoggedIn) {
    if (lockinUser.picture) {
      userAvatar.src = lockinUser.picture
      show(userAvatar)
    } else {
      hide(userAvatar)
    }
    userName.textContent = lockinUser.name || lockinUser.email.split('@')[0]
    if (lockinUser.credits != null) {
      userCredits.textContent = `${lockinUser.credits} cr`
      show(userCredits)
    } else {
      hide(userCredits)
    }
    show(userChip)
    hide(guestBadge)
  } else {
    hide(userChip)
    show(guestBadge)
  }

  // 4. Render detected video card (only if on YouTube)
  if (isWatchUrl(url)) {
    const vid = extractVideoId(url)
    if (vid) {
      videoThumb.src = `https://img.youtube.com/vi/${vid}/mqdefault.jpg`
      videoTitle.textContent = cleanTitle || 'YouTube Video'
      show(videoCard)
    } else {
      hide(videoCard)
    }
  } else {
    hide(videoCard)
  }

  // 5. URL paste section + credits
  if (isLoggedIn) {
    show(urlSection)
    show(creditInfo)
  } else {
    hide(urlSection)
    hide(creditInfo)
  }

  // 6. CTA state
  const canLaunch = isWatchUrl(url)
  if (isLoggedIn) {
    hide(signInBtn)
    show(lockInBtn)
    if (canLaunch) {
      lockInBtn.disabled = false
      ctaLabel.textContent = 'Start Session →'
    } else {
      lockInBtn.disabled = true
      ctaLabel.textContent = 'Open a video first'
    }
  } else {
    hide(lockInBtn)
    show(signInBtn)
  }
}

// ---- URL input logic ---------------------------------------------------

let _lastValidUrl = ''

const handleUrlInput = () => {
  const raw = urlInput.value.trim()

  // Normalize bare domains like "youtube.com/watch?v=abc"
  const toTry = raw.startsWith('http') ? raw : `https://${raw}`

  if (isWatchUrl(toTry)) {
    const vid = extractVideoId(toTry)
    if (vid) {
      _lastValidUrl = toTry
      // Show preview thumbnail immediately
      urlThumb.src = `https://img.youtube.com/vi/${vid}/mqdefault.jpg`
      urlPreviewTitle.textContent = 'YouTube Video'
      // Reanimate preview
      urlPreview.classList.add('hidden')
      requestAnimationFrame(() => {
        requestAnimationFrame(() => { // double rAF forces reflow
          show(urlPreview)
        })
      })
      urlInputWrap.classList.remove('focused')
      urlInputWrap.classList.add('valid')
      urlGoBtn.disabled = false
      setStatus('')
      return
    }
  }

  // Invalid
  _lastValidUrl = ''
  hide(urlPreview)
  urlGoBtn.disabled = true
  if (raw.length > 8) {
    urlInputWrap.classList.remove('valid')
  }
}

urlInput.addEventListener('focus', () => {
  if (!urlInputWrap.classList.contains('valid')) {
    urlInputWrap.classList.add('focused')
  }
})
urlInput.addEventListener('blur', () => {
  urlInputWrap.classList.remove('focused')
})
urlInput.addEventListener('input', handleUrlInput)
urlInput.addEventListener('paste', () => {
  // handle paste — short timeout lets the value populate first
  setTimeout(handleUrlInput, 0)
})
urlInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !urlGoBtn.disabled) launchFromInput()
})

const launchFromInput = async () => {
  if (!_lastValidUrl) return
  urlGoBtn.disabled = true
  urlGoBtn.textContent = '…'
  const target = `${BASE_URL}/?video=${encodeURIComponent(_lastValidUrl)}`
  await chrome.tabs.create({ url: target })
  setStatus('Session started!')
  setTimeout(() => window.close(), 700)
}

urlGoBtn.addEventListener('click', () => launchFromInput().catch(e => setStatus(e.message, true)))

// ---- Actions -----------------------------------------------------------

const launch = async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  const url = tab?.url || ''
  if (!isWatchUrl(url)) { setStatus('Open a YouTube video first.', true); return }

  ctaLabel.classList.add('hidden')
  ctaSpinner.classList.remove('hidden')
  lockInBtn.disabled = true

  const target = `${BASE_URL}/?video=${encodeURIComponent(url)}`
  await chrome.tabs.create({ url: target })
  setStatus('Session started!')
  setTimeout(() => window.close(), 800)
}

const goSignIn = async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  const url = tab?.url || ''
  const target = isWatchUrl(url)
    ? `${BASE_URL}/?video=${encodeURIComponent(url)}`
    : `${BASE_URL}/signup`
  await chrome.tabs.create({ url: target })
  window.close()
}

lockInBtn.addEventListener('click',  () => launch().catch(e => setStatus(e.message, true)))
signInBtn.addEventListener('click',  () => goSignIn())

// Run
render().catch(e => setStatus(e.message, true))
