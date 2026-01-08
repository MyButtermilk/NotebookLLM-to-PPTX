import { useEffect, useState, useRef } from 'react'

export function useWebSocket(jobId: string) {
  const [lastMessage, setLastMessage] = useState<string | null>(null)
  const [readyState, setReadyState] = useState<number>(WebSocket.CONNECTING)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!jobId) return

    const ws = new WebSocket(`ws://localhost:8000/ws/${jobId}`)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
      setReadyState(WebSocket.OPEN)
    }

    ws.onmessage = (event) => {
      console.log('WebSocket message:', event.data)
      setLastMessage(event.data)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setReadyState(WebSocket.CLOSED)
    }

    // Heartbeat to keep connection alive
    const heartbeat = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)

    return () => {
      clearInterval(heartbeat)
      ws.close()
    }
  }, [jobId])

  return {
    lastMessage,
    readyState,
    sendMessage: (message: string) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(message)
      }
    },
  }
}
