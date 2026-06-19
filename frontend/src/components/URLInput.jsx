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
    <div className="w-full max-w-lg bg-[#141414]/85 border border-white/10 p-6 rounded-xl shadow-2xl relative overflow-hidden glow-indigo backdrop-blur-xl">
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-indigo-500 to-purple-500"></div>
      
      <div className="mb-5">
        <h2 className="text-xl font-bold tracking-tight text-white">Add Video Links</h2>
        <p className="text-gray-400 text-sm mt-1">
          Paste one YouTube URL and one Instagram Reel URL to begin the comparison.
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
          className="w-full bg-white text-black hover:bg-indigo-100 font-semibold text-sm rounded-xl py-3 shadow-lg shadow-white/10 hover:shadow-indigo-400/20 active:transform active:scale-[0.99] transition duration-150 flex items-center justify-center space-x-2"
        >
          <span>Start Analyzing</span>
        </button>
      </form>
    </div>
  )
}
