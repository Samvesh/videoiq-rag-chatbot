import React from 'react'

export default function MetadataBar({ videoA, videoB }) {
  const engagementA = videoA?.engagement_rate || 0
  const engagementB = videoB?.engagement_rate || 0

  const winA = engagementA > engagementB
  const winB = engagementB > engagementA
  const draw = engagementA === engagementB

  return (
    <div className="w-full bg-[#1a1a1a] border border-[#222] rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between shadow-lg relative overflow-hidden">
      <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-indigo-500 to-purple-500"></div>
      
      <div className="flex items-center space-x-3 mb-3 md:mb-0 pl-2">
        <span className="text-xl">📊</span>
        <div>
          <h2 className="text-sm font-bold text-white leading-none">Performance Comparison</h2>
          <p className="text-[10px] text-gray-500 mt-1 uppercase tracking-wider font-semibold">Comparing engagement rates directly</p>
        </div>
      </div>

      <div className="flex items-center space-x-8">
        {/* Video A Metric */}
        <div className="flex items-center space-x-2.5">
          <div className="text-right">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none">Video A (YouTube)</p>
            <p className="text-lg font-extrabold text-indigo-400 mt-0.5">{engagementA}%</p>
          </div>
          {winA && <span className="text-lg animate-bounce" title="Engagement Winner">🏆</span>}
        </div>

        {/* VS Divider */}
        <div className="text-xs font-black text-[#333] px-2.5 py-1 bg-[#121212] rounded-md border border-[#222]">
          VS
        </div>

        {/* Video B Metric */}
        <div className="flex items-center space-x-2.5">
          {winB && <span className="text-lg animate-bounce" title="Engagement Winner">🏆</span>}
          <div className="text-left">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none">Video B (Instagram)</p>
            <p className="text-lg font-extrabold text-purple-400 mt-0.5">{engagementB}%</p>
          </div>
        </div>
      </div>
      
      {/* Short Summary Text */}
      <div className="hidden lg:block text-xs text-gray-400 font-medium">
        {winA && <span>🏆 <strong>{videoA.channel || 'Video A'}</strong> leads by <strong>{(engagementA - engagementB).toFixed(2)}%</strong> in engagement.</span>}
        {winB && <span>🏆 <strong>{videoB.channel || 'Video B'}</strong> leads by <strong>{(engagementB - engagementA).toFixed(2)}%</strong> in engagement.</span>}
        {draw && <span>🤝 Both videos are <strong>tied</strong> in engagement rate!</span>}
      </div>
    </div>
  )
}
