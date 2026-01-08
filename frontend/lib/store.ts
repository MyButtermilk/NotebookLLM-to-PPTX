import { create } from 'zustand'

interface JobMetadata {
  filename: string
  total_pages: number
}

interface JobStore {
  currentJob: string | null
  jobStatus: 'idle' | 'uploaded' | 'queued' | 'processing' | 'completed' | 'failed'
  jobMetadata: JobMetadata | null
}

export const useJobStore = create<JobStore>((set) => ({
  currentJob: null,
  jobStatus: 'idle',
  jobMetadata: null,
}))
