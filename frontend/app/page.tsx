'use client'

import { useState } from 'react'
import UploadZone from '@/components/UploadZone'
import ConversionSettings from '@/components/ConversionSettings'
import ProgressView from '@/components/ProgressView'
import ResultsView from '@/components/ResultsView'
import { useJobStore } from '@/lib/store'

export default function ConvertPage() {
  const { currentJob, jobStatus } = useJobStore()

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center space-y-3">
        <h1 className="font-display text-5xl font-bold text-gray-800 tracking-tight">
          SlideRefactor
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Transform NotebookLLM slide PDFs into fully editable PowerPoint presentations
        </p>
      </div>

      {/* Main Content */}
      {!currentJob && <UploadZone />}

      {currentJob && jobStatus === 'uploaded' && (
        <ConversionSettings jobId={currentJob} />
      )}

      {currentJob && ['queued', 'processing'].includes(jobStatus) && (
        <ProgressView jobId={currentJob} />
      )}

      {currentJob && jobStatus === 'completed' && (
        <ResultsView jobId={currentJob} />
      )}

      {currentJob && jobStatus === 'failed' && (
        <div className="neu-card p-8 text-center space-y-4">
          <div className="text-6xl">⚠️</div>
          <h3 className="text-2xl font-semibold text-gray-800">Conversion Failed</h3>
          <p className="text-gray-600">Something went wrong during the conversion process.</p>
          <button
            onClick={() => useJobStore.setState({ currentJob: null, jobStatus: 'idle' })}
            className="neu-button px-8 py-3 font-medium text-gray-700 hover:text-primary-600"
          >
            Start Over
          </button>
        </div>
      )}
    </div>
  )
}
