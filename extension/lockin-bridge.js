/**
 * LockIn Bridge — runs on lockin-dev.vercel.app
 * Listens for auth state messages posted by App.jsx and syncs them
 * into chrome.storage.local so the popup can show user info & credits.
 */
window.addEventListener('message', (event) => {
  if (event.source !== window) return
  const { type, payload } = event.data || {}

  if (type === 'LOCKIN_AUTH_STATE') {
    chrome.storage.local.set({ lockinUser: payload || null })
  }

  if (type === 'LOCKIN_AUTH_CLEARED') {
    chrome.storage.local.set({ lockinUser: null })
  }
})
