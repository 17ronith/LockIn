const BASE_URL = 'https://lockin-dev.vercel.app'
const BUTTON_ID = 'lockin-floating-btn'

const CSS = `
  #${BUTTON_ID} {
    position: fixed;
    right: 20px;
    bottom: 80px;
    z-index: 9999;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    border-radius: 999px;
    border: 1px solid rgba(43, 108, 176, 0.4);
    background: rgba(10, 13, 20, 0.88);
    color: #E2E8F0;
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.2px;
    cursor: pointer;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 20px rgba(43, 108, 176, 0.25), 0 0 0 1px rgba(43, 108, 176, 0.15) inset;
    transition: transform 0.15s ease, box-shadow 0.2s ease, background 0.18s ease;
    text-decoration: none;
    animation: lockinPop 0.35s cubic-bezier(0.34,1.56,0.64,1) both;
  }
  #${BUTTON_ID}:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(43, 108, 176, 0.4);
    background: rgba(15, 25, 45, 0.94);
  }
  #${BUTTON_ID}:active {
    transform: translateY(0);
  }
  #${BUTTON_ID} .lockin-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3B82F6, #2A8F8B);
    box-shadow: 0 0 6px rgba(59, 130, 246, 0.8);
    flex-shrink: 0;
  }
  @keyframes lockinPop {
    from { opacity: 0; transform: translateY(12px) scale(0.9); }
    to   { opacity: 1; transform: translateY(0)   scale(1); }
  }
`

const injectStyles = () => {
  if (document.getElementById('lockin-styles')) return
  const style = document.createElement('style')
  style.id = 'lockin-styles'
  style.textContent = CSS
  document.head.appendChild(style)
}

const createButton = () => {
  if (document.getElementById(BUTTON_ID)) return

  injectStyles()

  const btn = document.createElement('button')
  btn.id = BUTTON_ID
  btn.innerHTML = '<span class="lockin-dot"></span> LockIn'
  btn.title = 'Start a LockIn focus session for this video'

  btn.addEventListener('click', () => {
    const target = `${BASE_URL}/?video=${encodeURIComponent(window.location.href)}`
    window.open(target, '_blank', 'noopener')
  })

  document.body.appendChild(btn)
}

const removeButton = () => {
  const existing = document.getElementById(BUTTON_ID)
  if (existing) existing.remove()
}

const isWatchPage = () => window.location.pathname === '/watch'

const maybeInject = () => {
  if (isWatchPage()) createButton()
  else removeButton()
}

// Re-check on YouTube's SPA navigation
const navObserver = new MutationObserver(maybeInject)
navObserver.observe(document.documentElement, { childList: true, subtree: true })

maybeInject()
