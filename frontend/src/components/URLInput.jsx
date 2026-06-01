import React, { useState } from 'react'

export default function URLInput({ onSubmit, error }) {
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [instagramUrl, setInstagramUrl] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (youtubeUrl.trim() && instagramUrl.trim()) {
      onSubmit(youtubeUrl.trim(), instagramUrl.trim())
    }
  }

  return (
    <div className="w-full max-w-xl bg-[#1a1a1a] border border-[#222] p-8 rounded-2xl shadow-xl relative overflow-hidden glow-indigo">
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-indigo-500 to-purple-500"></div>
      
      <div className="mb-6">
        <h2 className="text-2xl font-bold tracking-tight text-white">Compare Video Performance</h2>
        <p className="text-gray-400 text-sm mt-1">
          Input YouTube and Instagram Reel URLs to cross-analyze transcripts, engagement metrics, and hook structures.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="youtube-url" className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            YouTube Video / Short URL
          </label>
          <input
            id="youtube-url"
            type="url"
            required
            placeholder="https://www.youtube.com/watch?v=..."
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
            className="w-full bg-[#121212] border border-[#333] focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 outline-none transition duration-200"
          />
        </div>

        <div>
          <label htmlFor="instagram-url" className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Instagram Reel URL
          </label>
          <input
            id="instagram-url"
            type="url"
            required
            placeholder="https://www.instagram.com/reel/..."
            value={instagramUrl}
            onChange={(e) => setInstagramUrl(e.target.value)}
            className="w-full bg-[#121212] border border-[#333] focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 outline-none transition duration-200"
          />
        </div>

        {error && (
          <div className="p-3 bg-red-950/40 border border-red-500/30 rounded-xl text-red-400 text-xs flex items-start space-x-2">
            <span className="mt-0.5 text-base leading-none">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <button
          type="submit"
          className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm rounded-xl py-3 shadow-lg shadow-indigo-600/10 hover:shadow-indigo-500/20 active:transform active:scale-[0.99] transition duration-150 flex items-center justify-center space-x-2"
        >
          <span>Analyze Videos</span>
          <span>⚡</span>
        </button>
      </form>
    </div>
  )
}
