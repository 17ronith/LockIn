const DEFAULT_BASE_URL = 'https://lockin-dev.vercel.app'
const BUTTON_ID = 'lockin-floating-button'

const createButton = () => {
  if (document.getElementById(BUTTON_ID)) return
  const button = document.createElement('button')
  button.id = BUTTON_ID
  button.textContent = "Let's LockIn"
  button.style.position = 'fixed'
  button.style.right = '18px'
  button.style.bottom = '18px'
  button.style.zIndex = '9999'
  button.style.padding = '10px 16px'
  button.style.borderRadius = '999px'
  button.style.border = '1px solid rgba(148, 163, 184, 0.4)'
  button.style.background = 'rgba(15, 23, 42, 0.92)'
  button.style.color = '#e5e7eb'
  button.style.fontSize = '13px'
  button.style.fontWeight = '600'
  button.style.cursor = 'pointer'
  button.style.backdropFilter = 'blur(8px)'
  button.style.transition = 'transform 0.15s ease, background 0.2s ease'

  button.addEventListener('mouseenter', () => {
    button.style.transform = 'translateY(-1px)'
    button.style.background = 'rgba(30, 41, 59, 0.95)'
  })
  button.addEventListener('mouseleave', () => {
    button.style.transform = 'translateY(0)'
    button.style.background = 'rgba(15, 23, 42, 0.92)'
  })

  button.addEventListener('click', async () => {
    const { lockinBaseUrl } = await chrome.storage.sync.get(['lockinBaseUrl'])
    const baseUrl = (lockinBaseUrl || DEFAULT_BASE_URL).trim()
    const target = `${baseUrl.replace(/\/$/, '')}/?video=${encodeURIComponent(window.location.href)}`
    window.open(target, '_blank', 'noopener')
  })

  document.body.appendChild(button)
}

const isWatchPage = () => {
  return window.location.pathname === '/watch'
}

const maybeInject = () => {
  if (isWatchPage()) {
    createButton()
  } else {
    const existing = document.getElementById(BUTTON_ID)
    if (existing) existing.remove()
  }
}

const observer = new MutationObserver(maybeInject)
observer.observe(document.documentElement, { childList: true, subtree: true })

maybeInject()
