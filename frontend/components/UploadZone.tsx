'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { FiUpload, FiFile } from 'react-icons/fi'
import { motion } from 'framer-motion'
import axios from 'axios'
import { useJobStore } from '@/lib/store'

export default function UploadZone() {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setError(null)
    setUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await axios.post('http://localhost:8000/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      const { job_id, filename, total_pages } = response.data

      // Update store
      useJobStore.setState({
        currentJob: job_id,
        jobStatus: 'uploaded',
        jobMetadata: { filename, total_pages }
      })

    } catch (error: any) {
      setError(error.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: uploading
  })

  return (
    <div className="max-w-3xl mx-auto">
      <motion.div
        {...getRootProps()}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        className={`
          neu-card p-16 cursor-pointer transition-all
          ${isDragActive ? 'ring-4 ring-primary-300' : ''}
          ${uploading ? 'opacity-60 cursor-wait' : ''}
        `}
        // Explicitly handle these events to resolve framer-motion type conflicts
        onAnimationStart={() => {}}
        onDragStart={() => {}}
        onDragEnd={() => {}}
        onDrag={() => {}}
      >
        <input {...getInputProps()} />

        <div className="text-center space-y-6">
          <motion.div
            animate={isDragActive ? { scale: 1.2 } : { scale: 1 }}
            transition={{ type: 'spring', stiffness: 300 }}
            className="neu-surface w-24 h-24 mx-auto flex items-center justify-center"
          >
            {uploading ? (
              <div className="animate-spin w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full" />
            ) : (
              <FiUpload className="w-12 h-12 text-primary-500" />
            )}
          </motion.div>

          {uploading ? (
            <div className="space-y-2">
              <h3 className="text-2xl font-semibold text-gray-800">Uploading...</h3>
              <p className="text-gray-600">Please wait while we process your file</p>
            </div>
          ) : (
            <div className="space-y-2">
              <h3 className="text-2xl font-semibold text-gray-800">
                {isDragActive ? 'Drop your PDF here' : 'Upload PDF to Convert'}
              </h3>
              <p className="text-gray-600">
                Drag and drop a PDF file here, or click to browse
              </p>
              <p className="text-sm text-gray-500">
                Supports NotebookLLM slide exports and other presentation PDFs
              </p>
            </div>
          )}

          {error && (
            <div className="neu-pressed p-4 rounded-lg">
              <p className="text-error text-sm">{error}</p>
            </div>
          )}
        </div>
      </motion.div>

      {/* Features */}
      <div className="mt-12 grid grid-cols-3 gap-6">
        {[
          { icon: '🎯', title: 'SOTA Accuracy', desc: 'Datalab + Claude AI' },
          { icon: '⚡', title: 'Fast Processing', desc: 'Real-time progress' },
          { icon: '✨', title: 'Fully Editable', desc: 'Text, not images' },
        ].map((feature) => (
          <div key={feature.title} className="neu-surface-sm p-6 text-center space-y-2">
            <div className="text-3xl">{feature.icon}</div>
            <h4 className="font-semibold text-gray-800">{feature.title}</h4>
            <p className="text-sm text-gray-600">{feature.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
