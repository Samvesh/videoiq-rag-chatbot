import React, { useState } from 'react'
import URLInput from './components/URLInput'
import MetadataBar from './components/MetadataBar'
import VideoCard from './components/VideoCard'
import ChatPanel from './components/ChatPanel'

const API_URL = import.meta.env.VITE_API_URL || ''

export default function App() {
  const [view, setView] = useState('input') // 'input' | 'dashboard'
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
    setVideoData(null)
    setError('')
  }

  return (
    <div className="min-h-screen flex flex-col font-sans">
      <header className="border-b border-[#222] bg-[#121212]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={handleReset}>
            <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center font-bold text-white shadow-md">
              VIQ
            </div>
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

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 flex flex-col">
        {loading && (
          <div className="flex-1 flex flex-col items-center justify-center py-20">
            <div className="relative">
              <div className="h-16 w-16 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin"></div>
              <div className="absolute inset-0 h-16 w-16 rounded-full border border-purple-500/10 animate-ping"></div>
            </div>
            <h3 className="mt-6 text-lg font-medium text-gray-200">Analyzing videos...</h3>
            <p className="mt-2 text-sm text-gray-500 max-w-xs text-center">
              Fetching transcripts, transcribing Instagram Reels audio with Whisper, and indexing contents...
            </p>
          </div>
        )}

        {!loading && view === 'input' && (
          <div className="flex-1 flex items-center justify-center py-10">
            <URLInput onSubmit={handleIngest} error={error} />
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
