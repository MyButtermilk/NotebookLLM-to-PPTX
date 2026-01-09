'use client'

import { useState, useEffect } from 'react'
import { FiPlay, FiSettings as FiSettingsIcon } from 'react-icons/fi'
import { motion } from 'framer-motion'
import axios from 'axios'
import { useJobStore } from '@/lib/store'

interface Props {
  jobId: string
}

export default function ConversionSettings({ jobId }: Props) {
  const { jobMetadata } = useJobStore()
  const [settings, setSettings] = useState({
    extractor: 'datalab',
    use_preprocessing: false,
    generate_audit: true,
    save_intermediate: true,
    slide_size: '16:9',
    render_background: true,
    skip_llm: true,
  })

  const [starting, setStarting] = useState(false)

  const handleStart = async () => {
    setStarting(true)

    try {
      await axios.post(`http://localhost:8000/api/jobs/${jobId}/convert`, settings)

      useJobStore.setState({ jobStatus: 'queued' })

    } catch (error) {
      console.error('Failed to start conversion:', error)
      alert('Failed to start conversion')
      setStarting(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* File Info */}
      <div className="neu-card p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="font-semibold text-gray-800 text-lg">{jobMetadata?.filename}</h3>
            <p className="text-sm text-gray-600">{jobMetadata?.total_pages} pages</p>
          </div>
          <button
            onClick={() => useJobStore.setState({ currentJob: null, jobStatus: 'idle' })}
            className="text-sm text-gray-500 hover:text-error"
          >
            Cancel
          </button>
        </div>
      </div>

      {/* Settings Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Extractor */}
        <div className="neu-card p-6 space-y-4">
          <div className="flex items-center gap-2 text-gray-700">
            <FiSettingsIcon />
            <h3 className="font-semibold">Extraction Engine</h3>
          </div>

          <div className="space-y-3">
            <label className="flex items-start gap-3 cursor-pointer p-3 rounded-lg hover:bg-neu-dark/20 transition-colors">
              <input
                type="radio"
                name="extractor"
                value="datalab"
                checked={settings.extractor === 'datalab'}
                onChange={(e) => setSettings({ ...settings, extractor: e.target.value })}
                className="mt-1 w-4 h-4 text-primary-600"
              />
              <div className="flex-1">
                <div className="font-medium text-gray-800">Datalab (Recommended)</div>
                <div className="text-sm text-gray-600">SOTA accuracy with precise bounding boxes</div>
              </div>
            </label>

            <label className="flex items-start gap-3 cursor-pointer p-3 rounded-lg hover:bg-neu-dark/20 transition-colors">
              <input
                type="radio"
                name="extractor"
                value="paddleocr"
                checked={settings.extractor === 'paddleocr'}
                onChange={(e) => setSettings({ ...settings, extractor: e.target.value })}
                className="mt-1 w-4 h-4 text-primary-600"
              />
              <div className="flex-1">
                <div className="font-medium text-gray-800">PaddleOCR</div>
                <div className="text-sm text-gray-600">Open-source OCR fallback</div>
              </div>
            </label>
          </div>
        </div>

        {/* Options */}
        <div className="neu-card p-6 space-y-4">
          <div className="flex items-center gap-2 text-gray-700">
            <FiSettingsIcon />
            <h3 className="font-semibold">Conversion Options</h3>
          </div>

          <div className="space-y-3">
            <label className="flex items-start gap-3 cursor-pointer p-3 rounded-lg hover:bg-neu-dark/20 transition-colors">
              <input
                type="checkbox"
                checked={settings.use_preprocessing}
                onChange={(e) => setSettings({ ...settings, use_preprocessing: e.target.checked })}
                className="mt-1 w-5 h-5 text-primary-600 rounded"
              />
              <div className="flex-1">
                <div className="font-medium text-gray-800">Preprocessing</div>
                <div className="text-sm text-gray-600">Apply OpenCV enhancements</div>
              </div>
            </label>

            <label className="flex items-start gap-3 cursor-pointer p-3 rounded-lg hover:bg-neu-dark/20 transition-colors">
              <input
                type="checkbox"
                checked={settings.generate_audit}
                onChange={(e) => setSettings({ ...settings, generate_audit: e.target.checked })}
                className="mt-1 w-5 h-5 text-primary-600 rounded"
              />
              <div className="flex-1">
                <div className="font-medium text-gray-800">Generate Audit Report</div>
                <div className="text-sm text-gray-600">Interactive HTML QA report</div>
              </div>
            </label>

            <label className="flex items-start gap-3 cursor-pointer p-3 rounded-lg hover:bg-neu-dark/20 transition-colors">
              <input
                type="checkbox"
                checked={settings.save_intermediate}
                onChange={(e) => setSettings({ ...settings, save_intermediate: e.target.checked })}
                className="mt-1 w-5 h-5 text-primary-600 rounded"
              />
              <div className="flex-1">
                <div className="font-medium text-gray-800">Save SlideGraph JSON</div>
                <div className="text-sm text-gray-600">Intermediate format for re-processing</div>
              </div>
            </label>

            <label className="flex items-start gap-3 cursor-pointer p-3 rounded-lg hover:bg-neu-dark/20 transition-colors">
              <input
                type="checkbox"
                checked={settings.render_background}
                onChange={(e) => setSettings({ ...settings, render_background: e.target.checked })}
                className="mt-1 w-5 h-5 text-primary-600 rounded"
              />
              <div className="flex-1">
                <div className="font-medium text-gray-800">Render Background Image</div>
                <div className="text-sm text-gray-600">Disable to avoid "double text" if layout isn't perfect</div>
              </div>
            </label>

            <label className="flex items-start gap-3 cursor-pointer p-3 rounded-lg hover:bg-neu-dark/20 transition-colors">
              <input
                type="checkbox"
                checked={settings.skip_llm}
                onChange={(e) => setSettings({ ...settings, skip_llm: e.target.checked })}
                className="mt-1 w-5 h-5 text-primary-600 rounded"
              />
              <div className="flex-1">
                <div className="font-medium text-gray-800">Direct Conversion (Recommended)</div>
                <div className="text-sm text-gray-600">Skip LLM, use OCR coordinates directly - faster and more reliable</div>
              </div>
            </label>
          </div>
        </div>
      </div>

      {/* Start Button */}
      <motion.button
        onClick={handleStart}
        disabled={starting}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className="w-full neu-button p-6 font-semibold text-primary-600 hover:text-primary-700 disabled:opacity-50 disabled:cursor-wait flex items-center justify-center gap-3 text-lg"
      >
        {starting ? (
          <>
            <div className="animate-spin w-5 h-5 border-3 border-primary-200 border-t-primary-600 rounded-full" />
            Starting Conversion...
          </>
        ) : (
          <>
            <FiPlay className="w-5 h-5" />
            Start Conversion
          </>
        )}
      </motion.button>
    </div>
  )
}
