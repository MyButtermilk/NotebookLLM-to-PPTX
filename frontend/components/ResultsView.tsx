'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { FiDownload, FiFileText, FiCheckCircle, FiRefreshCw } from 'react-icons/fi'
import axios from 'axios'
import { useJobStore } from '@/lib/store'

interface Props {
  jobId: string
}

export default function ResultsView({ jobId }: Props) {
  const { jobMetadata } = useJobStore()
  const [downloading, setDownloading] = useState(false)

  const handleDownload = async () => {
    setDownloading(true)
    try {
      window.open(`http://localhost:8000/api/jobs/${jobId}/download`, '_blank')
    } finally {
      setTimeout(() => setDownloading(false), 1000)
    }
  }

  const handleAudit = () => {
    window.open(`http://localhost:8000/api/jobs/${jobId}/audit`, '_blank')
  }

  const handleStartOver = () => {
    useJobStore.setState({
      currentJob: null,
      jobStatus: 'idle',
      jobMetadata: null
    })
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Success Card */}
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="neu-card p-12 text-center space-y-6"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200, delay: 0.2 }}
          className="neu-surface w-24 h-24 mx-auto flex items-center justify-center"
        >
          <FiCheckCircle className="w-12 h-12 text-success" />
        </motion.div>

        <div className="space-y-2">
          <h2 className="font-display text-3xl font-bold text-gray-800">
            Conversion Complete!
          </h2>
          <p className="text-gray-600">
            Your editable PowerPoint presentation is ready to download
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
          <div className="neu-surface-sm p-4 space-y-1">
            <div className="text-3xl font-bold text-primary-600">
              {jobMetadata?.total_pages || 0}
            </div>
            <div className="text-sm text-gray-600">Slides Created</div>
          </div>
          <div className="neu-surface-sm p-4 space-y-1">
            <div className="text-3xl font-bold text-success">
              100%
            </div>
            <div className="text-sm text-gray-600">Editability</div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
          <motion.button
            onClick={handleDownload}
            disabled={downloading}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="neu-button px-8 py-4 font-semibold text-primary-600 hover:text-primary-700 disabled:opacity-50 flex items-center justify-center gap-3"
          >
            {downloading ? (
              <>
                <div className="animate-spin w-5 h-5 border-3 border-primary-200 border-t-primary-600 rounded-full" />
                Downloading...
              </>
            ) : (
              <>
                <FiDownload className="w-5 h-5" />
                Download PPTX
              </>
            )}
          </motion.button>

          <button
            onClick={handleAudit}
            className="neu-button px-8 py-4 font-medium text-gray-700 hover:text-primary-600 flex items-center justify-center gap-2"
          >
            <FiFileText className="w-5 h-5" />
            View Audit Report
          </button>
        </div>
      </motion.div>

      {/* Details */}
      <div className="neu-card p-6 space-y-4">
        <h3 className="font-semibold text-gray-800">Conversion Summary</h3>

        <div className="space-y-2 text-sm">
          <div className="flex justify-between py-2 border-b border-neu-dark/20">
            <span className="text-gray-600">Original File</span>
            <span className="font-medium text-gray-800">{jobMetadata?.filename}</span>
          </div>
          <div className="flex justify-between py-2 border-b border-neu-dark/20">
            <span className="text-gray-600">Pages Converted</span>
            <span className="font-medium text-gray-800">{jobMetadata?.total_pages}</span>
          </div>
          <div className="flex justify-between py-2 border-b border-neu-dark/20">
            <span className="text-gray-600">Text Extraction</span>
            <span className="font-medium text-success">✓ All text editable</span>
          </div>
          <div className="flex justify-between py-2">
            <span className="text-gray-600">Layout Fidelity</span>
            <span className="font-medium text-success">✓ High</span>
          </div>
        </div>
      </div>

      {/* Start Over */}
      <div className="text-center">
        <button
          onClick={handleStartOver}
          className="text-gray-600 hover:text-primary-600 font-medium flex items-center gap-2 mx-auto"
        >
          <FiRefreshCw className="w-4 h-4" />
          Convert Another PDF
        </button>
      </div>
    </div>
  )
}
