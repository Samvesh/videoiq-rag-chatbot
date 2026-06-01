import React, { useState, useEffect, useRef } from 'react'

const API_URL = import.meta.env.VITE_API_URL || ''

export default function ChatPanel() {
  const [sessionId] = useState(() => {
    if (typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID()
    }
    return 'session-' + Math.random().toString(36).substring(2, 11)
  })

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  const suggestedQuestions = [
    "Why did Video A get more engagement?",
    "Compare the hooks in the first 5 seconds",
    "Suggest improvements for Video B",
    "What is the engagement rate of each video?"
  ]

  const handleSend = async (textToSend) => {
    if (!textToSend.trim() || loading) return

    const userMsg = { role: 'user', content: textToSend }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // Add empty assistant bubble for token accumulation
    const assistantMsg = { role: 'assistant', content: '', sources: [] }
    setMessages((prev) => [...prev, assistantMsg])

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: textToSend,
          session_id: sessionId,
        }),
      })

      if (!response.ok) {
        throw new Error('RAG backend failed to generate response.')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulated = ''
      let accumulatedSources = []

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        
        // Save incomplete line back to buffer
        buffer = lines.pop() || ''

        for (const line of lines) {
          const cleanLine = line.trim()
          if (cleanLine.startsWith('data: ')) {
            try {
              const data = JSON.parse(cleanLine.substring(6))
              if (data.token) {
                accumulated += data.token
              }
              if (data.sources && accumulatedSources.length === 0) {
                accumulatedSources = data.sources
              }
            } catch (err) {
              // Ignore temporary chunk JSON parse boundaries
            }
          }
        }

        // Update state with a fresh object (never mutate in-place — React StrictMode safe)
        const currentText = accumulated
        const currentSources = accumulatedSources
        setMessages((prev) => {
          const updated = [...prev]
          const lastIdx = updated.length - 1
          if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
            updated[lastIdx] = {
              ...updated[lastIdx],
              content: currentText,
              sources: currentSources,
            }
          }
          return updated
        })
      }
    } catch (err) {
      console.error(err)
      setMessages((prev) => {
        const updated = [...prev]
        const lastMsg = updated[updated.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.content = `Error: ${err.message || 'Failed to stream response.'}`
        }
        return updated
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    handleSend(input)
  }

  return (
    <div className="flex-1 bg-[#1a1a1a] border border-[#222] rounded-2xl flex flex-col justify-between overflow-hidden shadow-xl glow-indigo">
      
      {/* Panel Header */}
      <div className="border-b border-[#222] px-4 py-3 bg-[#121212] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-xs font-bold text-gray-200 tracking-wide uppercase">AI VideoIQ Expert</span>
        </div>
        <span className="text-[9px] font-bold text-gray-500 uppercase tracking-widest bg-[#222] px-2 py-0.5 rounded">
          RAG Active
        </span>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col justify-center items-center py-6">
            <span className="text-3xl animate-bounce">🤖</span>
            <h4 className="text-sm font-bold text-white mt-3">Chat with VideoIQ Analyst</h4>
            <p className="text-xs text-gray-500 mt-1 max-w-xs text-center leading-relaxed">
              Ask deep questions comparing hooks, metrics, durations, and content structure.
            </p>
            
            {/* Suggested Prompt Grids */}
            <div className="mt-6 grid grid-cols-1 gap-2 w-full max-w-sm">
              {suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(q)}
                  className="text-left text-xs bg-[#121212] hover:bg-[#222] border border-[#222] hover:border-indigo-500/30 px-3.5 py-2.5 rounded-xl text-gray-400 hover:text-white transition duration-150"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => {
            const isUser = msg.role === 'user'
            return (
              <div
                key={idx}
                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl p-3.5 text-xs leading-relaxed shadow-md ${
                    isUser
                      ? 'bg-indigo-600 text-white rounded-tr-none'
                      : 'bg-[#121212] border border-[#222] text-gray-200 rounded-tl-none'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  
                  {/* Sources Badges display */}
                  {!isUser && msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-[#222] flex flex-wrap gap-1.5 items-center">
                      <span className="text-[9px] font-bold text-gray-500 uppercase mr-1">Cited Segments:</span>
                      {msg.sources.map((src, sidx) => (
                        <span
                          key={sidx}
                          className={`text-[9px] font-bold px-2 py-0.5 rounded border ${
                            src.video_id === 'A'
                              ? 'bg-indigo-950/20 text-indigo-400 border-indigo-500/20'
                              : 'bg-purple-950/20 text-purple-400 border-purple-500/20'
                          }`}
                          title={src.text_preview}
                        >
                          Video {src.video_id} · Chunk {src.chunk_index}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )
          })
        )}

        {/* Typing loading dots */}
        {loading && messages.length > 0 && messages[messages.length - 1].content === '' && (
          <div className="flex items-center space-x-1.5 bg-[#121212] border border-[#222] rounded-xl px-3 py-2 w-max">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-bounce [animation-delay:-0.3s]"></span>
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-bounce [animation-delay:-0.15s]"></span>
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-bounce"></span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Inputs */}
      <form onSubmit={handleSubmit} className="border-t border-[#222] p-3 bg-[#121212] flex items-center space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about the videos..."
          className="flex-1 bg-[#1a1a1a] border border-[#222] focus:border-indigo-500 rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-600 outline-none transition duration-150"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-[#222] text-white disabled:text-gray-600 h-9 w-9 rounded-xl flex items-center justify-center shadow-lg transition duration-150"
        >
          <span>🚀</span>
        </button>
      </form>
    </div>
  )
}
