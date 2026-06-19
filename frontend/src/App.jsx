import React, { useState } from 'react'
import URLInput from './components/URLInput'
import MetadataBar from './components/MetadataBar'
import VideoCard from './components/VideoCard'
import ChatPanel from './components/ChatPanel'

const API_URL = import.meta.env.VITE_API_URL || ''

function AmbientScene({ mode = 'landing' }) {
  const dashboard = mode === 'dashboard'

  return (
    <div className={`ambient-scene ${dashboard ? 'ambient-dashboard' : 'ambient-landing'}`} aria-hidden="true">
      {!dashboard && (
        <>
          <div className="logo-orb youtube-orb">
            <span className="yt-mark"><span /></span>
          </div>
          <div className="logo-orb instagram-orb">
            <img className="ig-logo-img" src="/assets/instagram-logo.png" alt="" />
          </div>
        </>
      )}
      <span className="ambient-shape shape-circle shape-a" />
      <span className="ambient-shape shape-triangle shape-b" />
      <span className="ambient-shape shape-circle shape-c" />
      <span className="ambient-shape shape-triangle shape-d" />
      <span className="ambient-shape shape-pentagon shape-e" />
      <span className="ambient-shape shape-circle shape-f" />
      <span className="ambient-line line-a" />
      <span className="ambient-line line-b" />
    </div>
  )
}

function LandingIntro({ onStart }) {
  return (
    <section className="landing-panel">
      <p className="landing-kicker">Creator intelligence workspace</p>
      <h1>Video Analyzer RAG Chatbot</h1>
      <div className="intro-block">
        <p>
          Compare a YouTube video and Instagram Reel through one polished analysis layer. VideoIQ reads performance
          signals, builds a searchable RAG context, and turns raw video data into clear creator decisions.
        </p>
        <div className="intro-points">
          <span>Engagement comparison across views, likes, comments, and rate.</span>
          <span>Transcript-backed chat for hooks, pacing, topics, and content gaps.</span>
          <span>Side-by-side video summaries that make stronger creative choices easier.</span>
        </div>
      </div>
      <button type="button" onClick={onStart} className="start-button">
        START
      </button>
    </section>
  )
}

function RagLoader() {
  return (
    <div className="rag-loader-wrap">
      <div className="rag-loader">
        <div className="rag-word">RAG</div>
        <div className="rag-loading" aria-label="Loading">LOADING<span /></div>
      </div>
    </div>
  )
}

export default function App() {
  const [view, setView] = useState('input') // 'input' | 'dashboard'
  const [showForm, setShowForm] = useState(false)
  const [videoData, setVideoData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleIngest = async (youtubeUrl, instagramUrl) => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API_URL}/api/ingest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          youtube_url: youtubeUrl,
          instagram_url: instagramUrl,
        }),
      })

      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || 'Failed to analyze videos. Please check your URLs and try again.')
      }

      const data = await response.json()
      setVideoData(data)
      setView('dashboard')
    } catch (err) {
      console.error(err)
      setError(err.message || 'An error occurred during video analysis.')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setView('input')
    setShowForm(false)
    setVideoData(null)
    setError('')
  }

  return (
    <div className="min-h-screen flex flex-col font-sans app-shell">
      {!loading && view === 'input' && <AmbientScene mode="landing" />}
      {!loading && view === 'dashboard' && <AmbientScene mode="dashboard" />}
      <header className="border-b border-[#222] bg-[#121212]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={handleReset}>
            <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              VideoIQ
            </span>
          </div>
          {view === 'dashboard' && (
            <button
              onClick={handleReset}
              className="text-xs px-3 py-1.5 rounded-md border border-[#333] hover:border-indigo-500/50 hover:bg-indigo-500/10 text-gray-400 hover:text-white transition duration-200"
            >
              Analyze New Videos
            </button>
          )}
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 flex flex-col relative z-10">
        {loading && <RagLoader />}

        {!loading && view === 'input' && (
          <div className="flex-1 flex flex-col items-center justify-center py-10 gap-6">
            <LandingIntro onStart={() => setShowForm(true)} />
            {showForm && <URLInput onSubmit={handleIngest} error={error} />}
          </div>
        )}

        {!loading && view === 'dashboard' && videoData && (
          <div className="flex-1 flex flex-col space-y-4">
            {/* Metadata Bar comparison summary */}
            <MetadataBar videoA={videoData.videoA} videoB={videoData.videoB} />

            {/* Content splits */}
            <div className="flex-1 flex flex-col lg:flex-row gap-4 items-stretch">
              {/* Video metrics/cards (left 60%) */}
              <div className="lg:w-3/5 flex flex-col md:flex-row gap-4 items-stretch">
                <VideoCard video={videoData.videoA} label="A" />
                <VideoCard video={videoData.videoB} label="B" />
              </div>

              {/* Chat Panel (right 40%) */}
              <div className="lg:w-2/5 min-h-[500px] flex">
                <ChatPanel />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
