import { useState, useEffect, useRef, FormEvent } from 'react'
import { 
  PhoneOff, 
  Mic, 
  MicOff, 
  Send, 
  Radio, 
  Sparkles, 
  Clock, 
  Stethoscope, 
  Cpu 
} from 'lucide-react'
import { VoiceTranscriptItem, VoiceToolEvent } from '../types'

interface CallModalProps {
  isOpen: boolean
  onClose: () => void
  onAppointmentUpdated?: () => void
}

export const CallModal = ({ isOpen, onClose, onAppointmentUpdated }: CallModalProps) => {
  const [callStatus, setCallStatus] = useState<'connecting' | 'connected' | 'ended'>('connecting')
  const [callDuration, setCallDuration] = useState<number>(0)
  const [isMuted, setIsMuted] = useState<boolean>(false)
  const [transcripts, setTranscripts] = useState<VoiceTranscriptItem[]>([])
  const [activeTool, setActiveTool] = useState<VoiceToolEvent | null>(null)
  const [textInput, setTextInput] = useState<string>('')
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false)
  const [isListening, setIsListening] = useState<boolean>(true)

  const wsRef = useRef<WebSocket | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const transcriptEndRef = useRef<HTMLDivElement | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)

  // Auto-scroll transcript to bottom
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcripts, activeTool])

  // Call duration counter
  useEffect(() => {
    if (callStatus === 'connected') {
      timerRef.current = setInterval(() => {
        setCallDuration((prev) => prev + 1)
      }, 1000)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [callStatus])

  // Initialize WebSocket connection on modal open
  useEffect(() => {
    if (!isOpen) return

    setCallStatus('connecting')
    setCallDuration(0)
    setIsMuted(false)
    setTranscripts([])
    setActiveTool(null)

    const sessionId = `web_call_${Date.now()}`
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/voice/ws?session_id=${sessionId}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('CareFlow Voice WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        if (typeof event.data === 'string') {
          const payload = JSON.parse(event.data)
          handleWebSocketEvent(payload)
        } else if (event.data instanceof Blob) {
          // Binary audio chunk received from ElevenLabs TTS
          playAudioChunk(event.data)
        }
      } catch (err) {
        console.error('Failed to parse voice event:', err)
      }
    }

    ws.onerror = (err) => {
      console.warn('Voice WebSocket error, switching to simulation mode:', err)
      // If WebSocket fails, simulate active connection for graceful demo
      setCallStatus('connected')
    }

    ws.onclose = () => {
      console.log('Voice WebSocket closed')
      setCallStatus('ended')
    }

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.send(JSON.stringify({ type: 'call.end' }))
        ws.close()
      }
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => {})
      }
    }
  }, [isOpen])

  const handleWebSocketEvent = (payload: any) => {
    const { type, data } = payload
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })

    switch (type) {
      case 'call.started':
        setCallStatus('connecting')
        break

      case 'call.connected':
        setCallStatus('connected')
        setIsListening(true)
        break

      case 'transcript.user':
        setIsSpeaking(false)
        setIsListening(false)
        setTranscripts((prev) => [
          ...prev,
          { id: `user_${Date.now()}`, role: 'user', text: data.text, timestamp: now },
        ])
        break

      case 'transcript.agent':
        setIsSpeaking(true)
        setIsListening(true)
        setTranscripts((prev) => [
          ...prev,
          { id: `agent_${Date.now()}`, role: 'agent', text: data.text, timestamp: now },
        ])
        setTimeout(() => setIsSpeaking(false), 3000)
        break

      case 'tool.started':
        setActiveTool({
          tool: data.tool,
          status: 'started',
          params: data.params,
          timestamp: now,
        })
        break

      case 'tool.completed':
        setActiveTool({
          tool: data.tool,
          status: 'completed',
          result: data.result,
          timestamp: now,
        })
        // Clear tool pill after 4 seconds
        setTimeout(() => setActiveTool(null), 4000)
        break

      case 'appointment.created':
      case 'appointment.cancelled':
        if (onAppointmentUpdated) {
          onAppointmentUpdated()
        }
        break

      case 'call.ended':
        setCallStatus('ended')
        break

      default:
        break
    }
  }

  const playAudioChunk = async (blob: Blob) => {
    try {
      if (!audioContextRef.current) {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
        audioContextRef.current = new AudioContextClass()
      }
      const arrayBuffer = await blob.arrayBuffer()
      const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer)
      const source = audioContextRef.current.createBufferSource()
      source.buffer = audioBuffer
      source.connect(audioContextRef.current.destination)
      source.start()
      setIsSpeaking(true)
      source.onended = () => setIsSpeaking(false)
    } catch {
      // Audio playback fallback
    }
  }

  const toggleMute = () => {
    const nextMuted = !isMuted
    setIsMuted(nextMuted)
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'client.mute',
          muted: nextMuted,
        })
      )
    }
  }

  const handleEndCall = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'call.end' }))
    }
    setCallStatus('ended')
    setTimeout(() => {
      onClose()
    }, 800)
  }

  const handleSendTextMessage = (e?: FormEvent) => {
    if (e) e.preventDefault()
    if (!textInput.trim() || callStatus !== 'connected') return

    const msg = textInput.trim()
    setTextInput('')

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'text.input',
          text: msg,
        })
      )
    } else {
      // Fallback transcript reflection
      const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      setTranscripts((prev) => [
        ...prev,
        { id: `user_${Date.now()}`, role: 'user', text: msg, timestamp: now },
      ])
    }
  }

  const sendQuickChip = (text: string) => {
    setTextInput(text)
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'text.input',
          text: text,
        })
      )
      setTextInput('')
    }
  }

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-ink/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
      <div className="bg-surface border border-border rounded-2xl max-w-lg w-full h-[620px] flex flex-col shadow-2xl overflow-hidden">
        {/* Call Header */}
        <div className="p-4 bg-gradient-to-r from-blue-900 to-indigo-950 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-full bg-blue-600/30 border border-blue-400/40 flex items-center justify-center">
                <Stethoscope className="w-5 h-5 text-blue-200" />
              </div>
              {callStatus === 'connected' && (
                <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-400 border-2 border-indigo-950 rounded-full animate-pulse"></span>
              )}
            </div>

            <div>
              <h3 className="text-sm font-bold tracking-tight">CareFlow Voice Assistant</h3>
              <div className="flex items-center gap-2 text-xs text-blue-200">
                {callStatus === 'connecting' && <span>Connecting voice pipeline...</span>}
                {callStatus === 'connected' && (
                  <span className="flex items-center gap-1 font-mono">
                    <Clock className="w-3 h-3" /> {formatTimer(callDuration)}
                  </span>
                )}
                {callStatus === 'ended' && <span>Call Ended</span>}
                {isMuted && <span className="text-amber-300 font-semibold">• Muted</span>}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-500/20 text-blue-200 border border-blue-400/20 flex items-center gap-1">
              <Radio className="w-3 h-3" /> Live
            </span>
          </div>
        </div>

        {/* Dynamic Voice State & Tool Indicator Bar */}
        <div className="bg-background/80 border-b border-border px-4 py-2 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <span
                className={`w-2 h-2 rounded-full transition-colors ${
                  isSpeaking ? 'bg-primary animate-ping' : isListening ? 'bg-positive' : 'bg-muted-text'
                }`}
              ></span>
              <span className="font-medium text-ink">
                {isSpeaking ? 'Speaking...' : isListening ? 'Listening...' : 'Thinking...'}
              </span>
            </div>
          </div>

          {activeTool && (
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-primary/10 text-primary border border-primary/20 animate-in fade-in duration-150">
              <Cpu className="w-3 h-3 animate-spin" />
              <span>
                {activeTool.status === 'started'
                  ? `Executing: ${activeTool.tool.replace(/_/g, ' ')}...`
                  : `Completed: ${activeTool.tool.replace(/_/g, ' ')}`}
              </span>
            </div>
          )}
        </div>

        {/* Live Conversation Transcript Feed */}
        <div className="flex-1 p-4 overflow-y-auto space-y-3.5 bg-background/30">
          {transcripts.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-muted-text space-y-3">
              <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                <Sparkles className="w-6 h-6" />
              </div>
              <div>
                <p className="text-sm font-bold text-ink">CareFlow Voice Pipeline Ready</p>
                <p className="text-xs text-muted-text max-w-xs mt-1">
                  Start speaking or use the quick chips below to book with Dr. Rao or manage your appointments.
                </p>
              </div>
            </div>
          ) : (
            transcripts.map((item) => (
              <div
                key={item.id}
                className={`flex flex-col ${item.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div className="flex items-center gap-1 text-[10px] text-muted-text mb-1 px-1">
                  <span>{item.role === 'user' ? 'You' : 'CareFlow AI'}</span>
                  <span>•</span>
                  <span>{item.timestamp}</span>
                </div>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed shadow-xs ${
                    item.role === 'user'
                      ? 'bg-primary text-white rounded-br-xs font-medium'
                      : 'bg-surface border border-border text-ink rounded-bl-xs'
                  }`}
                >
                  {item.text}
                </div>
              </div>
            ))
          )}
          <div ref={transcriptEndRef} />
        </div>

        {/* Quick Test Intent Chips */}
        <div className="px-4 py-2 bg-surface border-t border-border flex items-center gap-1.5 overflow-x-auto text-[11px]">
          <span className="text-muted-text font-semibold shrink-0">Quick prompts:</span>
          <button
            onClick={() => sendQuickChip('Is there a cardiologist available tomorrow?')}
            className="px-2.5 py-1 rounded-full bg-background hover:bg-border/60 text-ink whitespace-nowrap border border-border/80"
          >
            Check Cardiology
          </button>
          <button
            onClick={() => sendQuickChip('My phone number is 9876543210')}
            className="px-2.5 py-1 rounded-full bg-background hover:bg-border/60 text-ink whitespace-nowrap border border-border/80 font-mono"
          >
            Provide Phone
          </button>
          <button
            onClick={() => sendQuickChip('Yes, that is correct, please confirm.')}
            className="px-2.5 py-1 rounded-full bg-positive/10 hover:bg-positive/20 text-positive whitespace-nowrap border border-positive/30 font-semibold"
          >
            Confirm
          </button>
          <button
            onClick={() => sendQuickChip('I would like to cancel my appointment.')}
            className="px-2.5 py-1 rounded-full bg-error/10 hover:bg-error/20 text-error whitespace-nowrap border border-error/30"
          >
            Cancel Appointment
          </button>
        </div>

        {/* Text Fallback Input Bar */}
        <form
          onSubmit={handleSendTextMessage}
          className="p-3 bg-surface border-t border-border flex items-center gap-2"
        >
          <input
            type="text"
            placeholder="Type a voice utterance or reply..."
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            disabled={callStatus !== 'connected'}
            className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-xs text-ink placeholder:text-muted-text focus:outline-none focus:border-primary disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!textInput.trim() || callStatus !== 'connected'}
            className="bg-primary hover:bg-blue-700 disabled:opacity-50 text-white p-2 rounded-lg transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>

        {/* Call Controls Footer */}
        <div className="p-4 bg-background border-t border-border flex items-center justify-around shrink-0">
          {/* Mute Toggle */}
          <button
            onClick={toggleMute}
            className={`p-3 rounded-full border transition-all duration-150 ${
              isMuted
                ? 'bg-amber-100 text-amber-800 border-amber-300'
                : 'bg-surface hover:bg-border/60 text-ink border-border shadow-xs'
            }`}
            title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
          >
            {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>

          {/* End Call Button */}
          <button
            onClick={handleEndCall}
            className="flex items-center gap-2 bg-error hover:bg-red-700 text-white font-bold text-xs py-3 px-6 rounded-full shadow-md transition-all duration-150 active:scale-95"
          >
            <PhoneOff className="w-4 h-4" />
            <span>End Call</span>
          </button>
        </div>
      </div>
    </div>
  )
}
