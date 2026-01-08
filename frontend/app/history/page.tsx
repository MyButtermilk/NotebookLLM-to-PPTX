'use client'

import { useEffect, useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { FiDownload, FiTrash2, FiFileText, FiCheckCircle, FiXCircle, FiClock } from 'react-icons/fi'
import axios from 'axios'

interface Job {
  job_id: string
  filename: string
  status: string
  total_pages: number
  created_at: string
  progress: number
}

export default function HistoryPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadJobs()
  }, [])

  const loadJobs = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/jobs')
      setJobs(response.data)
    } catch (error) {
      console.error('Failed to load jobs:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async (jobId: string) => {
    window.open(`http://localhost:8000/api/jobs/${jobId}/download`, '_blank')
  }

  const handleDelete = async (jobId: string) => {
    if (!confirm('Are you sure you want to delete this job?')) return

    try {
      await axios.delete(`http://localhost:8000/api/jobs/${jobId}`)
      setJobs(jobs.filter(j => j.job_id !== jobId))
    } catch (error) {
      console.error('Failed to delete job:', error)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <FiCheckCircle className="text-success" />
      case 'failed':
        return <FiXCircle className="text-error" />
      case 'processing':
      case 'queued':
        return <FiClock className="text-warning" />
      default:
        return <FiFileText className="text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-success'
      case 'failed':
        return 'text-error'
      case 'processing':
      case 'queued':
        return 'text-warning'
      default:
        return 'text-gray-500'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center space-y-4">
          <div className="animate-spin w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full mx-auto" />
          <p className="text-gray-600">Loading history...</p>
        </div>
      </div>
    )
  }

  if (jobs.length === 0) {
    return (
      <div className="text-center py-16 space-y-4">
        <div className="text-6xl opacity-50">📁</div>
        <h2 className="text-2xl font-semibold text-gray-700">No conversion history yet</h2>
        <p className="text-gray-600">Your completed conversions will appear here</p>
        <a
          href="/"
          className="inline-block neu-button px-6 py-3 font-medium text-primary-600 hover:text-primary-700"
        >
          Convert Your First PDF
        </a>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-3xl font-bold text-gray-800">Conversion History</h1>
        <div className="text-sm text-gray-600">{jobs.length} total conversions</div>
      </div>

      <div className="space-y-4">
        {jobs.map((job) => (
          <div key={job.job_id} className="neu-card p-6 hover:shadow-neu-hover transition-shadow">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-4 flex-1 min-w-0">
                <div className="mt-1 text-2xl">
                  {getStatusIcon(job.status)}
                </div>

                <div className="flex-1 min-w-0 space-y-2">
                  <div className="flex items-center gap-3">
                    <h3 className="text-lg font-semibold text-gray-800 truncate">
                      {job.filename}
                    </h3>
                    <span className={`text-sm font-medium ${getStatusColor(job.status)} capitalize`}>
                      {job.status}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span>{job.total_pages} pages</span>
                    <span>•</span>
                    <span>{formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}</span>
                  </div>

                  {job.status === 'processing' && (
                    <div className="space-y-1">
                      <div className="neu-pressed h-2 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-primary-400 to-primary-600 transition-all duration-300"
                          style={{ width: `${job.progress}%` }}
                        />
                      </div>
                      <div className="text-xs text-gray-500">{Math.round(job.progress)}% complete</div>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {job.status === 'completed' && (
                  <button
                    onClick={() => handleDownload(job.job_id)}
                    className="neu-button p-3 text-primary-600 hover:text-primary-700"
                    title="Download PPTX"
                  >
                    <FiDownload className="w-5 h-5" />
                  </button>
                )}

                <button
                  onClick={() => handleDelete(job.job_id)}
                  className="neu-button p-3 text-gray-500 hover:text-error"
                  title="Delete"
                >
                  <FiTrash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
