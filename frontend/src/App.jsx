import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import axios from 'axios'
import './App.css'
import lockInLogo from './assets/Color Scheme for Focus Jan 26 2026 (1).png'
import reactIcon from './assets/React Icon.png'
import viteIcon from './assets/Vite.js Icon.png'
import openaiIcon from './assets/OpenAI Logo Icon 50.png'
import llamaIcon from './assets/LLaMA Model Icon.png'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const EXIT_PHRASE = "I don't want to achieve my goals"
const DEFAULT_FOCUS_MINUTES = 25
const DEFAULT_BREAK_MINUTES = 5
const LOADING_DURATION_SECONDS = 30
const spring = { type: 'spring', stiffness: 80, damping: 18 }
const pageVariants = {
  initial: { opacity: 0, scale: 0.98, filter: 'blur(10px)' },
  animate: { opacity: 1, scale: 1, filter: 'blur(0px)', transition: spring },
  exit: { opacity: 0, scale: 1.02, filter: 'blur(10px)', transition: spring }
}
const stagger = {
  initial: { opacity: 1 },
  animate: { opacity: 1, transition: { staggerChildren: 0.1 } },
  exit: { opacity: 1 }
}
const item = {
  initial: { opacity: 0, scale: 0.98, filter: 'blur(10px)' },
  animate: { opacity: 1, scale: 1, filter: 'blur(0px)', transition: spring },
  exit: { opacity: 0, scale: 1.02, filter: 'blur(10px)', transition: spring }
}

const AnimationWrapper = ({ children }) => (
  <motion.div
    className="page-wrapper"
    variants={pageVariants}
    initial="initial"
    animate="animate"
    exit="exit"
  >
    {children}
  </motion.div>
)

function App() {
  const [playlistUrl, setPlaylistUrl] = useState('')
  const [userIntent, setUserIntent] = useState('')
  const [goalStatement, setGoalStatement] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedVideo, setSelectedVideo] = useState(null)
  const [goalError, setGoalError] = useState('')
  const [showExitGuard, setShowExitGuard] = useState(false)
  const [exitInput, setExitInput] = useState('')
  const [exitError, setExitError] = useState('')
  const [pendingExitUrl, setPendingExitUrl] = useState(null)
  const [sessionActive, setSessionActive] = useState(false)
  const [breakActive, setBreakActive] = useState(false)
  const [focusMinutes, setFocusMinutes] = useState(DEFAULT_FOCUS_MINUTES)
  const [breakMinutes, setBreakMinutes] = useState(DEFAULT_BREAK_MINUTES)
  const [focusSecondsLeft, setFocusSecondsLeft] = useState(DEFAULT_FOCUS_MINUTES * 60)
  const [breakSecondsLeft, setBreakSecondsLeft] = useState(DEFAULT_BREAK_MINUTES * 60)
  const [sessionsCompleted, setSessionsCompleted] = useState(0)
  const [streakCount, setStreakCount] = useState(0)
  const [showPenalty, setShowPenalty] = useState(false)
  const [penaltyPaused, setPenaltyPaused] = useState(false)
  const [playerStartSeconds, setPlayerStartSeconds] = useState(0)
  const [playerKey, setPlayerKey] = useState(0)
  const [showSessionSetup, setShowSessionSetup] = useState(false)
  const [pendingVideo, setPendingVideo] = useState(null)
  const [sessionError, setSessionError] = useState('')
  const [fullscreenRequired, setFullscreenRequired] = useState(false)
  const [fullscreenError, setFullscreenError] = useState('')
  const [readyToStart, setReadyToStart] = useState(false)
  const [loadingSecondsLeft, setLoadingSecondsLeft] = useState(LOADING_DURATION_SECONDS)
  const [loadingTipIndex, setLoadingTipIndex] = useState(0)
  const [loadingZeroAt, setLoadingZeroAt] = useState(null)
  const [loadingStartedAt, setLoadingStartedAt] = useState(null)
  const [focusPaused, setFocusPaused] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [authUser, setAuthUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('lockin_user') || 'null')
    } catch {
      return null
    }
  })
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('lockin_token') || '')
  const [authError, setAuthError] = useState('')

  const loadingTips = [
    'Breathe in — breathe out.',
    'Meditation reduces stress and improves focus.',
    'Slow breaths calm the nervous system.',
    'Let your shoulders drop and relax.',
    'Notice the breath, return to it gently.'
  ]
  const playerStartRef = useRef(0)
  const playerTimestampRef = useRef(Date.now())
  const userMenuRef = useRef(null)
  const externalLaunchHandledRef = useRef(false)
  const location = useLocation()
  const navigate = useNavigate()
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
  const googleLoadedRef = useRef(false)

  const TailwindIcon = () => (
    <svg viewBox="0 0 24 24" width="32" height="32" aria-hidden="true">
      <path
        fill="#2A8F8B"
        d="M12 6c-2.2 0-3.6 1.1-4.2 3.2.8-1.1 1.7-1.6 2.8-1.6 1.5 0 2.6.8 3.6 2 .9 1.1 1.9 2.4 3.8 2.4 2.2 0 3.6-1.1 4.2-3.2-.8 1.1-1.7 1.6-2.8 1.6-1.5 0-2.6-.8-3.6-2-.9-1.1-1.9-2.4-3.8-2.4zM7.8 12.4c-2.2 0-3.6 1.1-4.2 3.2.8-1.1 1.7-1.6 2.8-1.6 1.5 0 2.6.8 3.6 2 .9 1.1 1.9 2.4 3.8 2.4 2.2 0 3.6-1.1 4.2-3.2-.8 1.1-1.7 1.6-2.8 1.6-1.5 0-2.6-.8-3.6-2-.9-1.1-1.9-2.4-3.8-2.4z"
      />
    </svg>
  )

  const normalizeUrl = (value) => {
    const trimmed = value.trim()
    if (!trimmed) return ''
    if (/^https?:\/\//i.test(trimmed)) return trimmed
    return `https://${trimmed}`
  }

  const decodeGoogleCredential = (credential) => {
    try {
      const payload = credential.split('.')[1]
      if (!payload) return null
      const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
      const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=')
      const json = atob(padded)
      const data = JSON.parse(json)
      if (!data?.sub) return null
      return {
        id: data.sub,
        email: data.email || '',
        name: data.name || '',
        given_name: data.given_name,
        family_name: data.family_name,
        picture: data.picture
      }
    } catch {
      return null
    }
  }

  const isPlaylistUrl = (value) => {
    if (!value) return false
    try {
      const url = new URL(normalizeUrl(value))
      return url.searchParams.has('list')
    } catch {
      return value.includes('list=')
    }
  }

  const extractVideoId = (value) => {
    const trimmed = value.trim()
    if (!trimmed) return null
    if (/^[\w-]{11}$/.test(trimmed)) return trimmed

    try {
      const url = new URL(normalizeUrl(trimmed))
      if (url.hostname.includes('youtu.be')) {
        const id = url.pathname.split('/').filter(Boolean)[0]
        return id || null
      }
      if (url.searchParams.get('v')) {
        return url.searchParams.get('v')
      }
      if (url.pathname.startsWith('/shorts/')) {
        return url.pathname.split('/shorts/')[1]?.split('/')[0] || null
      }
      if (url.pathname.startsWith('/embed/')) {
        return url.pathname.split('/embed/')[1]?.split('/')[0] || null
      }
    } catch {
      return null
    }
    return null
  }

  const isVideoUrl = (value) => Boolean(extractVideoId(value))
  const showIntentField = isPlaylistUrl(playlistUrl)
  const isAuthRoute = location.pathname === '/login' || location.pathname === '/signup'
  const isResultsRoute = location.pathname === '/results'

  const clearPendingSubmission = () => {
    localStorage.removeItem('lockin_pending_url')
    localStorage.removeItem('lockin_pending_intent')
  }

  const submitUrl = useCallback(async (urlValue, intentValue) => {
    const trimmedUrl = urlValue.trim()
    const trimmedIntent = intentValue.trim()

    setError('')
    setLoading(true)

    try {
      if (isPlaylistUrl(trimmedUrl)) {
        if (!trimmedIntent) {
          setError('Please enter a learning goal for playlist ranking.')
          return
        }
        const response = await axios.post(`${API_URL}/rank`, {
          playlist_url: trimmedUrl,
          user_intent: trimmedIntent,
          limit: 9,
          min_score: 0.0,
        })
        setResults(response.data)
      } else if (isVideoUrl(trimmedUrl)) {
        const response = await axios.post(`${API_URL}/video`, {
          video_url: trimmedUrl,
        })
        const video = response.data
        setResults({
          status: 'success',
          timestamp: new Date().toISOString(),
          playlist_url: trimmedUrl,
          user_intent: trimmedIntent || 'Single video',
          total_videos: 1,
          returned_results: 1,
          videos: [video]
        })
        setPendingVideo(video)
        setShowSessionSetup(true)
      } else {
        setError('Please enter a valid YouTube playlist or video URL.')
      }
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Failed to rank playlist. Check the URL and try again.'
      )
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }, [isPlaylistUrl, isVideoUrl])

  const handleGoogleCredential = useCallback(async (credential) => {
    if (!credential) return
    setAuthError('')
    try {
      const response = await axios.post(`${API_URL}/auth/google`, {
        credential,
      })
      const user = response.data.user
      const token = response.data.token || credential
      setAuthUser(user)
      setAuthToken(token)
      localStorage.setItem('lockin_user', JSON.stringify(user))
      localStorage.setItem('lockin_token', token)

      const pendingUrl = localStorage.getItem('lockin_pending_url') || ''
      const pendingIntent = localStorage.getItem('lockin_pending_intent') || ''
      clearPendingSubmission()
      navigate('/')

      if (pendingUrl) {
        setPlaylistUrl(pendingUrl)
        setUserIntent(pendingIntent)
        await submitUrl(pendingUrl, pendingIntent)
      }
    } catch (err) {
      if (err.response) {
        setAuthError(
          err.response?.data?.detail ||
          err.message ||
          'Unable to sign in with Google. Please try again.'
        )
        return
      }

      const fallbackUser = decodeGoogleCredential(credential)
      if (fallbackUser) {
        const pendingUrl = localStorage.getItem('lockin_pending_url') || ''
        const pendingIntent = localStorage.getItem('lockin_pending_intent') || ''
        setAuthUser(fallbackUser)
        setAuthToken(credential)
        localStorage.setItem('lockin_user', JSON.stringify(fallbackUser))
        localStorage.setItem('lockin_token', credential)
        clearPendingSubmission()
        navigate('/')
        if (pendingUrl) {
          setPlaylistUrl(pendingUrl)
          setUserIntent(pendingIntent)
          await submitUrl(pendingUrl, pendingIntent)
        }
        return
      }
      setAuthError(
        err.response?.data?.detail ||
        err.message ||
        'Unable to sign in with Google. Please try again.'
      )
    }
  }, [navigate, submitUrl])

  const handleLogout = () => {
    setAuthUser(null)
    setAuthToken('')
    localStorage.removeItem('lockin_user')
    localStorage.removeItem('lockin_token')
    navigate('/')
  }

  const handleHome = () => {
    if (location.pathname === '/results' && selectedVideo) {
      requestExit('__reset__')
      return
    }
    if (location.pathname === '/results') {
      setResults(null)
      setSelectedVideo(null)
      setPendingVideo(null)
      setShowSessionSetup(false)
    }
    navigate('/')
  }

  useEffect(() => {
    if (!googleClientId || googleLoadedRef.current) return

    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = () => {
      if (!window.google?.accounts?.id) return
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: (response) => handleGoogleCredential(response.credential),
        auto_select: true,
        itp_support: true
      })
      googleLoadedRef.current = true
    }
    document.body.appendChild(script)

    return () => {
      script.onload = null
    }
  }, [googleClientId, handleGoogleCredential])

  useEffect(() => {
    if (authUser && isAuthRoute) {
      navigate('/')
      return
    }
    if (authUser || !isAuthRoute) return
    if (window.google?.accounts?.id) {
      const targetId = location.pathname === '/signup' ? 'google-signup' : 'google-login'
      const container = document.getElementById(targetId)
      if (container && !container.dataset.rendered) {
        window.google.accounts.id.renderButton(container, {
          theme: 'outline',
          size: 'large',
          width: 320,
          shape: 'pill'
        })
        container.dataset.rendered = 'true'
      }
      window.google.accounts.id.prompt()
    }
  }, [authUser, isAuthRoute, location.pathname, navigate])

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const token = params.get('token')
    const error = params.get('error')
    if (!token && !error) return

    if (error) {
      setAuthError('Unable to sign in with Google. Please try again.')
      navigate(location.pathname, { replace: true })
      return
    }

    const user = decodeGoogleCredential(token)
    if (user) {
      setAuthUser(user)
      setAuthToken(token)
      localStorage.setItem('lockin_user', JSON.stringify(user))
      localStorage.setItem('lockin_token', token)
      navigate('/', { replace: true })
    } else {
      setAuthError('Unable to sign in with Google. Please try again.')
      navigate(location.pathname, { replace: true })
    }
  }, [location.pathname, location.search, navigate])

  useEffect(() => {
    if (externalLaunchHandledRef.current) return
    const params = new URLSearchParams(location.search)
    const incomingUrl = params.get('video') || params.get('url')
    if (!incomingUrl) return

    externalLaunchHandledRef.current = true
    const decodedUrl = decodeURIComponent(incomingUrl)
    setPlaylistUrl(decodedUrl)
    setUserIntent('')

    if (!authUser) {
      localStorage.setItem('lockin_pending_url', decodedUrl)
      localStorage.setItem('lockin_pending_intent', '')
      navigate('/signup', { replace: true })
      return
    }

    submitUrl(decodedUrl, '')
  }, [authUser, location.search, navigate, submitUrl])

  useEffect(() => {
    if (!showUserMenu) return
    const handleClickOutside = (event) => {
      if (!userMenuRef.current) return
      if (!userMenuRef.current.contains(event.target)) {
        setShowUserMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showUserMenu])

  useEffect(() => {
    setShowUserMenu(false)
  }, [location.pathname])

  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (showExitGuard) return
      e.preventDefault()
      e.returnValue = 'Do you want to achieve your goals?'
      return e.returnValue
    }

    const handleLinkClick = (e) => {
      const anchor = e.target.closest('a')
      if (!anchor) return

      const href = anchor.getAttribute('href')
      if (!href || href.startsWith('#')) return

      try {
        const url = new URL(href, window.location.href)
        if (url.origin !== window.location.origin) {
          e.preventDefault()
          requestExit(url.href)
        }
      } catch {
        return
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    document.addEventListener('click', handleLinkClick)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
      document.removeEventListener('click', handleLinkClick)
    }
  }, [showExitGuard])

  useEffect(() => {
    if (!loading) return

    const durationSeconds = LOADING_DURATION_SECONDS
    const startTime = Date.now()
    setLoadingStartedAt(startTime)
    setLoadingSecondsLeft(durationSeconds)
    setLoadingTipIndex(0)
    setLoadingZeroAt(null)

    const countdown = setInterval(() => {
      const elapsed = (Date.now() - startTime) / 1000
      const remaining = Math.max(0, durationSeconds - elapsed)
      setLoadingSecondsLeft(remaining)
    }, 100)

    const tips = setInterval(() => {
      setLoadingTipIndex((prev) => (prev + 1) % loadingTips.length)
    }, 3000)

    return () => {
      clearInterval(countdown)
      clearInterval(tips)
    }
  }, [loading])

  useEffect(() => {
    if (loadingSecondsLeft === 0 && loadingZeroAt === null) {
      setLoadingZeroAt(Date.now())
    }
  }, [loadingSecondsLeft, loadingZeroAt])

  useEffect(() => {
    const handleFullscreenChange = () => {
      if (document.fullscreenElement) {
        setFullscreenRequired(false)
        setFullscreenError('')
        if (readyToStart) {
          startPlayback()
        }
      }
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [readyToStart])

  useEffect(() => {
    const savedSessions = Number(localStorage.getItem('lockin_sessions_completed') || 0)
    const savedStreak = Number(localStorage.getItem('lockin_streak_count') || 0)
    setSessionsCompleted(savedSessions)
    setStreakCount(savedStreak)
  }, [])

  useEffect(() => {
    localStorage.setItem('lockin_sessions_completed', String(sessionsCompleted))
    localStorage.setItem('lockin_streak_count', String(streakCount))
  }, [sessionsCompleted, streakCount])

  useEffect(() => {
    const tick = () => {
      if (sessionActive && !focusPaused) {
        setFocusSecondsLeft((prev) => {
          if (prev <= 1) {
            setSessionActive(false)
            setBreakActive(true)
            setBreakSecondsLeft(breakMinutes * 60)
            setSessionsCompleted((count) => count + 1)
            setStreakCount((count) => count + 1)
            return 0
          }
          return prev - 1
        })
      } else if (breakActive) {
        setBreakSecondsLeft((prev) => {
          if (prev <= 1) {
            setBreakActive(false)
            setFocusSecondsLeft(focusMinutes * 60)
            return breakMinutes * 60
          }
          return prev - 1
        })
      }
    }

    const interval = setInterval(tick, 1000)
    return () => clearInterval(interval)
  }, [sessionActive, breakActive, focusPaused, breakMinutes, focusMinutes])

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!selectedVideo) return
      if (document.hidden) {
        setFocusPaused(true)
      }
      if (!document.hidden || penaltyPaused) return

      const now = Date.now()
      const elapsed = (now - playerTimestampRef.current) / 1000
      const currentTime = playerStartRef.current + elapsed
      const newStart = Math.max(0, currentTime - 10)

      playerStartRef.current = newStart
      setPlayerStartSeconds(newStart)
      setPenaltyPaused(true)
      setShowPenalty(true)
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [selectedVideo, penaltyPaused])

  useEffect(() => {
    if (breakActive && selectedVideo) {
      setSelectedVideo(null)
    }
  }, [breakActive, selectedVideo])

  const handleRankPlaylist = async (e) => {
    e.preventDefault()
    if (!authUser) {
      localStorage.setItem('lockin_pending_url', playlistUrl)
      localStorage.setItem('lockin_pending_intent', userIntent)
      navigate('/signup')
      return
    }

    await submitUrl(playlistUrl, userIntent)
  }

  const handleWatchInApp = (video) => {
    if (breakActive) {
      setError('Break time is active. Come back when the break ends.')
      return
    }
    setGoalError('')
    setSessionError('')
    setPendingVideo(video)
    setShowSessionSetup(true)
  }

  const requestExit = (url) => {
    setPendingExitUrl(url || 'about:blank')
    setExitInput('')
    setExitError('')
    setShowExitGuard(true)
  }

  const confirmExit = () => {
    if (exitInput.trim() !== EXIT_PHRASE) {
      setExitError('Please type the exact phrase to leave.')
      return
    }
    setShowExitGuard(false)
    setExitError('')
    if (pendingExitUrl === '__reset__') {
      setSelectedVideo(null)
      setResults(null)
      setPlaylistUrl('')
      setUserIntent('')
      setError('')
      setShowExitGuard(false)
      setPendingExitUrl(null)
      navigate('/')
      return
    }
    if (pendingExitUrl) {
      window.location.href = pendingExitUrl
    }
  }

  const startSession = () => {
    if (breakActive) return
    setSessionActive(true)
    setFocusSecondsLeft(focusMinutes * 60)
  }

  const stopSession = () => {
    setSessionActive(false)
    setBreakActive(false)
    setFocusSecondsLeft(focusMinutes * 60)
    setBreakSecondsLeft(breakMinutes * 60)
  }

  const resumeAfterPenalty = () => {
    setShowPenalty(false)
    setPenaltyPaused(false)
    playerTimestampRef.current = Date.now()
    setPlayerKey(Date.now())
    setFocusPaused(false)
  }

  const confirmSessionSetup = () => {
    if (!pendingVideo) return
    if (!goalStatement.trim()) {
      setGoalError('Please enter your goal statement before watching.')
      return
    }
    if (focusMinutes <= 0 || breakMinutes < 0) {
      setSessionError('Please enter valid session and break lengths.')
      return
    }

    setShowSessionSetup(false)

    if (!document.fullscreenElement) {
      setFullscreenRequired(true)
      setReadyToStart(true)
      return
    }

    startPlayback()
  }

  const requestFullscreen = async () => {
    try {
      await document.documentElement.requestFullscreen()
      setFullscreenRequired(false)
      setFullscreenError('')
      if (readyToStart) {
        startPlayback()
      }
    } catch {
      setFullscreenRequired(true)
      setFullscreenError('Unable to enter fullscreen. Please use your browser controls.')
    }
  }

  const startPlayback = () => {
    if (!pendingVideo) return
    setSelectedVideo(pendingVideo)
    setPendingVideo(null)
    setReadyToStart(false)
    const now = Date.now()
    playerStartRef.current = 0
    playerTimestampRef.current = now
    setPlayerStartSeconds(0)
    setPenaltyPaused(false)
    setShowPenalty(false)
    setPlayerKey(now)
    setFocusPaused(false)
    startSession()
  }

  const formatTime = (seconds) => {
    const m = String(Math.floor(seconds / 60)).padStart(2, '0')
    const s = String(seconds % 60).padStart(2, '0')
    return `${m}:${s}`
  }

  useEffect(() => {
    if (results && location.pathname !== '/results') {
      navigate('/results')
    }
    if (!results && location.pathname === '/results') {
      navigate('/')
    }
  }, [results, location.pathname, navigate])

  return (
    <div className="app">
      <div className="animated-bg">
        <span className="orb orb-blue"></span>
        <span className="orb orb-teal"></span>
      </div>
      {loading && (
        <div className="loading-overlay">
          <div className="loading-card">
            <div className="loading-title">Fetching results...</div>
            {loadingSecondsLeft === 0 && loadingZeroAt && (Date.now() - loadingZeroAt > 1000) ? (
              <div className="loading-one-moment">
                One moment
                <span className="loading-dots"></span>
              </div>
            ) : (
              <div
                className="loading-ring"
                style={{
                  '--progress': Math.max(0, Math.min(100, (1 - (loadingSecondsLeft / LOADING_DURATION_SECONDS)) * 100))
                }}
              >
                <div className="loading-ring-inner">{`${Math.ceil(loadingSecondsLeft)}s`}</div>
              </div>
            )}
            <div className="loading-subtitle">Take a breath while we prepare your focus session.</div>
            <div className="loading-tip">{loadingTips[loadingTipIndex]}</div>
            <div className="loading-breath">
              <span className="breath-dot"></span>
              <span className="breath-dot"></span>
              <span className="breath-dot"></span>
            </div>
          </div>
        </div>
      )}
      {showSessionSetup && (
        <div className="session-overlay">
          <div className="session-modal">
            <h3>Set your focus session</h3>
            <div className="session-grid">
              <div>
                <label htmlFor="focus-min">Focus length (minutes)</label>
                <input
                  id="focus-min"
                  type="number"
                  min="1"
                  value={focusMinutes}
                  onChange={(e) => setFocusMinutes(Number(e.target.value))}
                />
              </div>
              <div>
                <label htmlFor="break-min">Break length (minutes)</label>
                <input
                  id="break-min"
                  type="number"
                  min="0"
                  value={breakMinutes}
                  onChange={(e) => setBreakMinutes(Number(e.target.value))}
                />
              </div>
            </div>
            <div className="session-goal">
              <label htmlFor="goal">Goal statement</label>
              <input
                id="goal"
                type="text"
                placeholder="e.g., Finish 3 videos with full attention"
                value={goalStatement}
                onChange={(e) => setGoalStatement(e.target.value)}
              />
              {goalError && <div className="error-message" style={{ marginTop: '0.75rem' }}>{goalError}</div>}
              {sessionError && <div className="error-message" style={{ marginTop: '0.75rem' }}>{sessionError}</div>}
            </div>
            <div className="session-actions">
              <button className="btn btn-secondary" onClick={() => setShowSessionSetup(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={confirmSessionSetup}>
                Start Session
              </button>
            </div>
          </div>
        </div>
      )}

      {fullscreenRequired && (
        <div className="fullscreen-overlay">
          <div className="fullscreen-modal">
            <h3>Enter Fullscreen to start</h3>
            <p>You need fullscreen focus mode before watching.</p>
            {fullscreenError && <div className="error-message">{fullscreenError}</div>}
            <div className="fullscreen-actions">
              <button className="btn btn-secondary" onClick={() => { setFullscreenRequired(false); setReadyToStart(false) }}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={requestFullscreen}>
                Enter Fullscreen
              </button>
            </div>
          </div>
        </div>
      )}

      {showExitGuard && (
        <div className="exit-overlay">
          <div className="exit-modal">
            <h3>Do you want to achieve your goals?</h3>
            <p>Type the phrase exactly to leave.</p>
            <input
              type="text"
              value={exitInput}
              onChange={(e) => setExitInput(e.target.value)}
              placeholder="I don't want to achieve my goals"
            />
            {exitError && <div className="error-message">{exitError}</div>}
            <div className="exit-actions">
              <button className="btn btn-secondary" onClick={() => setShowExitGuard(false)}>
                Stay
              </button>
              <button className="btn btn-primary" onClick={confirmExit}>
                Leave
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="navbar">
        <div className="navbar-content">
          <button className="navbar-brand" onClick={handleHome}>LockIn</button>
          {authUser ? (
            <div className="navbar-user" ref={userMenuRef}>
              <button
                className="user-trigger"
                onClick={() => setShowUserMenu((prev) => !prev)}
                aria-haspopup="menu"
                aria-expanded={showUserMenu}
              >
                {authUser.picture ? (
                  <img
                    src={authUser.picture}
                    alt=""
                    className="user-avatar"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <span className="user-avatar-fallback">
                    {(authUser.given_name || authUser.name || 'U').charAt(0)}
                  </span>
                )}
                {authUser.given_name || authUser.name || 'Account'}
                <span className="user-caret">⌄</span>
              </button>
              {showUserMenu && (
                <div className="user-menu" role="menu">
                  <button className="user-menu-item" type="button" disabled>
                    Settings
                  </button>
                  <button className="user-menu-item" type="button" onClick={handleLogout}>
                    Log out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="navbar-auth">
              <button
                className="nav-auth-link"
                type="button"
                onClick={() => navigate('/login')}
              >
                Sign in
              </button>
              <button
                className="nav-auth-btn"
                type="button"
                onClick={() => navigate('/signup')}
              >
                Get started
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* Main Content */}
      <div className="container">
        <AnimatePresence mode="wait">
          <Routes location={location}>
            <Route
              path="/"
              element={
                <AnimationWrapper key={location.pathname}>
                  <motion.section
                    className="landing"
                    variants={stagger}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                  >
                    <motion.h1 className="landing-title" variants={item}>
                      Focus Your Learning
                    </motion.h1>
                    <motion.p className="landing-subtitle" variants={item}>
                      Transform YouTube playlists into a calm, distraction-free learning flow using multimodal analysis.
                    </motion.p>

                    <motion.div className="search-card glass-card" layoutId="card-container" variants={item}>
                      <form className="search-form" onSubmit={handleRankPlaylist}>
                        <div className="form-group">
                          <label htmlFor="url">Enter a valid YouTube URL</label>
                          <input
                            id="url"
                            type="url"
                            placeholder="https://www.youtube.com/playlist?list=PLxxxx"
                            value={playlistUrl}
                            onChange={(e) => setPlaylistUrl(e.target.value)}
                            required
                          />
                        </div>

                        <AnimatePresence mode="wait" initial={false}>
                          {showIntentField && (
                            <motion.div
                              key="intent-field"
                              className="form-group"
                              initial={{ opacity: 0, y: 10, filter: 'blur(6px)' }}
                              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                              exit={{ opacity: 0, y: -8, filter: 'blur(6px)' }}
                              transition={spring}
                            >
                              <label htmlFor="intent">What we looking for?</label>
                              <textarea
                                id="intent"
                                placeholder="Some Valid Funny Placeholder"
                                value={userIntent}
                                onChange={(e) => setUserIntent(e.target.value)}
                                rows="2"
                              />
                            </motion.div>
                          )}
                        </AnimatePresence>

                        {error && <div className="error-message">{error}</div>}

                        <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%' }}>
                          {loading ? (
                            <>
                              <span className="spinner"></span>
                              Ranking Videos...
                            </>
                          ) : (
                            "Let's Lock In"
                          )}
                        </button>
                      </form>
                    </motion.div>

                    <motion.div className="feature-grid" variants={item}>
                      <div className="feature-card">
                        <h3>Smart Ranking</h3>
                        <p>Find the most relevant videos using multimodal understanding.</p>
                      </div>
                      <div className="feature-card">
                        <h3>Distraction Free</h3>
                        <p>Stay in a calm workspace that keeps you focused.</p>
                      </div>
                      <div className="feature-card">
                        <h3>Deep Analysis</h3>
                        <p>Text and visual signals combine for better learning flow.</p>
                      </div>
                    </motion.div>

                  </motion.section>
                </AnimationWrapper>
              }
            />
            <Route
              path="/signup"
              element={
                <AnimationWrapper key={location.pathname}>
                  <motion.section
                    className="auth-page"
                    variants={stagger}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                  >
                    <motion.div className="auth-card" variants={item}>
                      <div className="auth-brand">
                        <div className="auth-brand-icon">L</div>
                        <span className="auth-brand-name">LockIn</span>
                      </div>
                      <div className="auth-badge">Free forever</div>
                      <div className="auth-header">
                        <h2 className="auth-title">Create your account</h2>
                        <p className="auth-subtitle">Stay focused with distraction-free video sessions, streaks, and progress tracking.</p>
                      </div>
                      <div className="auth-divider">
                        <span className="auth-divider-text">continue with</span>
                      </div>
                      {!googleClientId && (
                        <div className="error-message">Google login is not configured.</div>
                      )}
                      <div className="auth-google" id="google-signup"></div>
                      {authError && <div className="error-message">{authError}</div>}
                      <div className="auth-perks">
                        <span className="auth-perk"><span className="auth-perk-icon">🔒</span> No password needed</span>
                        <span className="auth-perk"><span className="auth-perk-icon">⚡</span> Instant setup</span>
                      </div>
                      <div className="auth-footer">
                        <span>Already have an account?</span>
                        <button className="auth-link" type="button" onClick={() => navigate('/login')}>Sign in</button>
                      </div>
                    </motion.div>
                  </motion.section>
                </AnimationWrapper>
              }
            />
            <Route
              path="/login"
              element={
                <AnimationWrapper key={location.pathname}>
                  <motion.section
                    className="auth-page"
                    variants={stagger}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                  >
                    <motion.div className="auth-card" variants={item}>
                      <div className="auth-brand">
                        <div className="auth-brand-icon">L</div>
                        <span className="auth-brand-name">LockIn</span>
                      </div>
                      <div className="auth-header">
                        <h2 className="auth-title">Welcome back</h2>
                        <p className="auth-subtitle">Pick up where you left off — your streaks and sessions are waiting.</p>
                      </div>
                      <div className="auth-divider">
                        <span className="auth-divider-text">continue with</span>
                      </div>
                      {!googleClientId && (
                        <div className="error-message">Google login is not configured.</div>
                      )}
                      <div className="auth-google" id="google-login"></div>
                      {authError && <div className="error-message">{authError}</div>}
                      <div className="auth-footer">
                        <span>Need an account?</span>
                        <button className="auth-link" type="button" onClick={() => navigate('/signup')}>Sign up</button>
                      </div>
                    </motion.div>
                  </motion.section>
                </AnimationWrapper>
              }
            />
            <Route
              path="/results"
              element={
                <AnimationWrapper key={location.pathname}>
                  <motion.div
                    className="results-page"
                    variants={stagger}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                  >
                    {selectedVideo && (
                      <motion.div className="focus-panel" variants={item}>
                        <div className="focus-status">
                          <div className="focus-label">Focus Session</div>
                          <div className="focus-time">
                            {breakActive ? `Break ${formatTime(breakSecondsLeft)}` : formatTime(focusSecondsLeft)}
                          </div>
                          <div className="focus-progress">
                            <div
                              className="focus-progress-bar"
                              style={{ width: `${Math.min(100, ((focusMinutes * 60 - focusSecondsLeft) / (focusMinutes * 60 || 1)) * 100)}%` }}
                            />
                          </div>
                        </div>
                        <div className="focus-actions">
                          {!sessionActive && !breakActive && (
                            <button className="btn btn-primary" onClick={startSession}>Start Focus</button>
                          )}
                          {sessionActive && (
                            <button className="btn btn-secondary" onClick={stopSession}>Stop Session</button>
                          )}
                          {breakActive && (
                            <button className="btn btn-secondary" disabled>Break Lock</button>
                          )}
                        </div>
                        <div className="focus-metrics">
                          <div><strong>Sessions:</strong> {sessionsCompleted}</div>
                          <div><strong>Streak:</strong> {streakCount}</div>
                        </div>
                      </motion.div>
                    )}

                    {results && selectedVideo && (
                      <motion.div className="player-section" variants={item}>
                        <div className="player-header">
                          <h3>{selectedVideo.title}</h3>
                          <button className="player-close" onClick={() => setSelectedVideo(null)}>✕</button>
                        </div>
                        <div className="player-frame">
                          {!penaltyPaused && (
                            <iframe
                              key={playerKey}
                              src={`https://www.youtube.com/embed/${selectedVideo.video_id}?autoplay=1&rel=0&start=${Math.floor(playerStartSeconds)}`}
                              title={selectedVideo.title}
                              allow="autoplay; encrypted-media; picture-in-picture"
                              allowFullScreen
                            />
                          )}
                          {penaltyPaused && (
                            <div className="penalty-overlay">
                              <div className="penalty-modal">
                                <h3>Stay focused</h3>
                                <p>You switched tabs. We rewound 10 seconds.</p>
                                <button className="btn btn-primary" onClick={resumeAfterPenalty}>Resume</button>
                              </div>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}

                    {results && !selectedVideo && (
                      <motion.div variants={item}>
                        {results.videos.length === 0 ? (
                          <div className="empty-state">
                            <div className="empty-state-icon">🎬</div>
                            <h3>No videos found</h3>
                            <p>Try adjusting your search intent.</p>
                          </div>
                        ) : (
                          <div className="videos-grid">
                            {results.videos.slice(0, 9).map((video) => (
                              <div key={video.video_id} className="video-card">
                                <img
                                  src={video.thumbnail_url_hq}
                                  alt={video.title}
                                  className="video-thumbnail"
                                  onError={(e) => { e.target.src = 'https://via.placeholder.com/320x180?text=Video' }}
                                />
                                <div className="video-content">
                                  <div className="video-rank">#{video.rank}</div>
                                  <h3 className="video-title">{video.title}</h3>
                                  
                                  <div className="video-scores">
                                    <div className="score">
                                      <span className="score-label">Relevance</span>
                                      <span className="score-value">{(video.final_score * 100).toFixed(0)}%</span>
                                    </div>
                                    <div className="score">
                                      <span className="score-label">Text</span>
                                      <span className="score-value">{(video.text_score * 100).toFixed(0)}%</span>
                                    </div>
                                    <div className="score">
                                      <span className="score-label">Visual</span>
                                      <span className="score-value">{(video.visual_score * 100).toFixed(0)}%</span>
                                    </div>
                                  </div>

                                  <div className="video-actions">
                                    <button
                                      className="video-btn video-btn-primary"
                                      onClick={() => handleWatchInApp(video)}
                                      disabled={breakActive}
                                    >
                                      Watch Video
                                    </button>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                        <div style={{ textAlign: 'center', marginTop: '3rem' }}>
                          <button
                            className="btn btn-primary"
                            onClick={() => requestExit('__reset__')}
                          >
                            ↻ Search Again
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </motion.div>
                </AnimationWrapper>
              }
            />
          </Routes>
        </AnimatePresence>
      </div>
    </div>
  )
}

export default App
