'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { FiCheck, FiLoader } from 'react-icons/fi'
import { useJobStore } from '@/lib/store'
import { useWebSocket } from '@/lib/useWebSocket'

interface Props {
  jobId: string
}

const PHASES = [
  { id: 'upload', label: 'Uploading', completed: true },
  { id: 'extract', label: 'Extracting Content', completed: false },
  { id: 'ai', label: 'AI Processing', completed: false },
  { id: 'render', label: 'Generating PPTX', completed: false },
  { id: 'complete', label: 'Complete', completed: false },
]

export default function ProgressView({ jobId }: Props) {
  const [progress, setProgress] = useState(0)
  const [currentPhase, setCurrentPhase] = useState('Initializing')
  const [phases, setPhases] = useState(PHASES)

  const { lastMessage } = useWebSocket(jobId)

  useEffect(() => {
    if (lastMessage) {
      // Ignore non-JSON messages like 'pong' heartbeat
      if (lastMessage === 'pong') return

      try {
        const data = JSON.parse(lastMessage)

        if (data.progress !== undefined) {
          setProgress(data.progress)
        }

        if (data.phase) {
          setCurrentPhase(data.phase)

          // Update phases
          const newPhases = [...PHASES]
          if (data.progress >= 20) newPhases[1].completed = true
          if (data.progress >= 50) newPhases[2].completed = true
          if (data.progress >= 75) newPhases[3].completed = true
          if (data.progress >= 100) newPhases[4].completed = true
          setPhases(newPhases)
        }

        if (data.status === 'completed') {
          useJobStore.setState({ jobStatus: 'completed' })
        }

        if (data.status === 'failed') {
          useJobStore.setState({ jobStatus: 'failed' })
        }
      } catch (e) {
        // Ignore non-JSON messages
        console.debug('Ignoring non-JSON WebSocket message:', lastMessage)
      }
    }
  }, [lastMessage])

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Progress Card */}
      <div className="neu-card p-8 space-y-6">
        {/* Status */}
        <div className="text-center space-y-2">
          <div className="neu-surface w-16 h-16 mx-auto flex items-center justify-center">
            <FiLoader className="w-8 h-8 text-primary-500 animate-spin" />
          </div>
          <h2 className="text-2xl font-semibold text-gray-800">{currentPhase}</h2>
          <p className="text-gray-600">Converting your PDF to PowerPoint</p>
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="neu-pressed h-4 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
              className="h-full bg-gradient-to-r from-primary-400 to-primary-600"
            />
          </div>
          <div className="flex justify-between text-sm text-gray-600">
            <span>{currentPhase}</span>
            <span>{Math.round(progress)}%</span>
          </div>
        </div>

        {/* Phase Stepper */}
        <div className="relative pt-6">
          <div className="absolute top-10 left-0 right-0 h-0.5 bg-neu-dark/30" />

          <div className="relative flex justify-between">
            {phases.map((phase, index) => (
              <div key={phase.id} className="flex flex-col items-center gap-2">
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{
                    scale: phase.completed ? 1 : 0.9,
                    opacity: phase.completed ? 1 : 0.5
                  }}
                  className={`
                    w-8 h-8 rounded-full flex items-center justify-center
                    ${phase.completed
                      ? 'bg-primary-500 text-white'
                      : 'neu-surface text-gray-400'
                    }
                  `}
                >
                  {phase.completed ? (
                    <FiCheck className="w-4 h-4" />
                  ) : (
                    <span className="text-sm">{index + 1}</span>
                  )}
                </motion.div>
                <span className={`
                  text-xs font-medium text-center max-w-[80px]
                  ${phase.completed ? 'text-gray-700' : 'text-gray-400'}
                `}>
                  {phase.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tips */}
      <div className="neu-surface-sm p-6 space-y-2">
        <h3 className="font-semibold text-gray-700">💡 Did you know?</h3>
        <p className="text-sm text-gray-600">
          SlideRefactor uses Gemini AI to intelligently reconstruct layout, infer bullet structures,
          and preserve reading order—even in complex multi-column slides.
        </p>
      </div>
    </div>
  )
}
