const BASE_URL = 'https://lockin-dev.vercel.app'

// DOM refs
const $ = (id) => document.getElementById(id)
const userChip     = $('userChip')
const userAvatar   = $('userAvatar')
const userName     = $('userName')
const userCredits  = $('userCredits')
const guestBadge   = $('guestBadge')
const videoCard    = $('videoCard')
const videoThumb   = $('videoThumb')
const videoTitle   = $('videoTitle')
const noVideoCard  = $('noVideoCard')
const creditInfo   = $('creditInfo')
const lockInBtn    = $('lockInBtn')
const ctaLabel     = $('ctaLabel')
const ctaSpinner   = $('ctaSpinner')
const signInBtn    = $('signInBtn')
const statusMsg    = $('statusMsg')

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
  // Strip " - YouTube" suffix
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

  // 4. Render video card
  if (isWatchUrl(url)) {
    const vid = extractVideoId(url)
    if (vid) {
      videoThumb.src = `https://img.youtube.com/vi/${vid}/mqdefault.jpg`
      videoTitle.textContent = cleanTitle || "YouTube Video"
      show(videoCard)
      hide(noVideoCard)
    } else {
      hide(videoCard)
      show(noVideoCard)
    }
  } else {
    hide(videoCard)
    show(noVideoCard)
  }

  // 5. Credits info
  if (isLoggedIn) show(creditInfo)
  else hide(creditInfo)

  // 6. CTA state
  const canLaunch = isWatchUrl(url)
  if (isLoggedIn) {
    hide(signInBtn)
    if (canLaunch) {
      show(lockInBtn)
      lockInBtn.disabled = false
      ctaLabel.textContent = "Start Session →"
    } else {
      show(lockInBtn)
      lockInBtn.disabled = true
      ctaLabel.textContent = "Open a video first"
    }
  } else {
    hide(lockInBtn)
    show(signInBtn)
  }
}

// ---- Actions -----------------------------------------------------------

const launch = async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  const url = tab?.url || ''
  if (!isWatchUrl(url)) { setStatus('Open a YouTube video first.', true); return }

  // Button loading state
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
  // If on a video page, go to /?video=URL — the app stores pending_url and redirects to /signup
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
