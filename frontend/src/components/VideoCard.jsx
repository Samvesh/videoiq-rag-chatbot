import React from 'react'

const formatNumber = (num) => {
  if (num === undefined || num === null) return '0'
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K'
  }
  return num.toString()
}

const formatDuration = (seconds) => {
  if (!seconds) return '0:00'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  const formattedSeconds = s < 10 ? `0${s}` : s
  if (h > 0) {
    const formattedMinutes = m < 10 ? `0${m}` : m
    return `${h}:${formattedMinutes}:${formattedSeconds}`
  }
  return `${m}:${formattedSeconds}`
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'Unknown Date'
  if (dateStr.includes('-') || dateStr.includes(':')) {
    try {
      const d = new Date(dateStr)
      return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
    } catch {
      return dateStr
    }
  }
  if (dateStr.length === 8) {
    const y = dateStr.slice(0, 4)
    const m = dateStr.slice(4, 6)
    const d = dateStr.slice(6, 8)
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    const monthIdx = parseInt(m) - 1
    if (monthIdx >= 0 && monthIdx < 12) {
      return `${months[monthIdx]} ${parseInt(d)}, ${y}`
    }
  }
  return dateStr
}

export default function VideoCard({ video, label }) {
  const isYoutube = label === 'A'
  
  const getEngagementBadge = (rate) => {
    if (rate >= 5.0) {
      return (
        <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs px-2.5 py-1 rounded-full font-medium">
          🔥 High ({rate}%)
        </span>
      )
    }
    if (rate >= 2.0) {
      return (
        <span className="bg-amber-500/10 text-amber-400 border border-amber-500/30 text-xs px-2.5 py-1 rounded-full font-medium">
          📈 Medium ({rate}%)
        </span>
      )
    }
    return (
      <span className="bg-rose-500/10 text-rose-400 border border-rose-500/30 text-xs px-2.5 py-1 rounded-full font-medium">
        📉 Low ({rate}%)
      </span>
    )
  }

  return (
    <div className={`flex-1 bg-[#1a1a1a] border border-[#222] rounded-2xl p-5 flex flex-col justify-between relative overflow-hidden shadow-xl ${isYoutube ? 'glow-indigo hover:border-indigo-500/30' : 'glow-purple hover:border-purple-500/30'}`}>
      
      {/* Label Badge */}
      <div className="flex items-center justify-between mb-4">
        <span className={`text-[10px] uppercase font-bold tracking-widest px-2.5 py-1 rounded-md text-white shadow-sm ${isYoutube ? 'bg-indigo-600' : 'bg-purple-600'}`}>
          Video {label} • {isYoutube ? 'YouTube' : 'Instagram'}
        </span>
        {getEngagementBadge(video.engagement_rate)}
      </div>

      {/* Embed/Placeholder Area */}
      <div className="mb-4">
        {isYoutube && video.video_id ? (
          <div className="aspect-video w-full rounded-xl overflow-hidden border border-[#2c2c2c] bg-black">
            <iframe
              src={`https://www.youtube.com/embed/${video.video_id}`}
              title={video.title}
              className="w-full h-full border-none"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            ></iframe>
          </div>
        ) : (
          <div className="aspect-video w-full rounded-xl bg-[#121212] border border-[#2c2c2c] flex flex-col items-center justify-center relative group overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-tr from-purple-500/5 to-pink-500/5 opacity-50 group-hover:opacity-80 transition duration-300"></div>
            <span className="text-3xl mb-2 animate-bounce">🎬</span>
            <span className="text-sm font-semibold text-gray-300">Instagram Reel Playback</span>
            <a
              href={video.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 text-xs bg-[#222] hover:bg-purple-600 border border-[#333] hover:border-purple-500 px-4 py-2 rounded-xl text-gray-300 hover:text-white transition duration-200"
            >
              Open Link ↗
            </a>
          </div>
        )}
      </div>

      {/* Metadata Metrics */}
      <div className="flex-1 flex flex-col justify-start">
        <h3 className="text-base font-bold text-white leading-snug line-clamp-2 hover:line-clamp-none cursor-pointer mb-1" title={video.title}>
          {video.title}
        </h3>
        
        <div className="flex items-center space-x-2 mb-4">
          <div className="h-6 w-6 rounded-full bg-gradient-to-tr from-[#333] to-[#444] flex items-center justify-center text-xs font-semibold text-gray-300">
            {video.channel ? video.channel.charAt(0).toUpperCase() : '?'}
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-300 leading-none">{video.channel || 'Unknown Creator'}</p>
            <p className="text-[10px] text-gray-500 leading-none mt-0.5">{formatNumber(video.channel_follower_count)} followers</p>
          </div>
        </div>

        {/* 3 Metric Grid */}
        <div className="grid grid-cols-3 gap-2 py-3 px-4 bg-[#121212] border border-[#222] rounded-xl mb-4">
          <div className="text-center">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Views</p>
            <p className="text-sm font-bold text-white mt-0.5">{formatNumber(video.view_count)}</p>
          </div>
          <div className="text-center border-x border-[#222]">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Likes</p>
            <p className="text-sm font-bold text-white mt-0.5">{formatNumber(video.like_count)}</p>
          </div>
          <div className="text-center">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Comments</p>
            <p className="text-sm font-bold text-white mt-0.5">{formatNumber(video.comment_count)}</p>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="border-t border-[#222] pt-3 flex items-center justify-between text-[10px] font-semibold text-gray-500 tracking-wide uppercase">
        <span>Duration: {formatDuration(video.duration)}</span>
        <span>Uploaded: {formatDate(video.upload_date)}</span>
      </div>
    </div>
  )
}
