/**
 * Batch processing TypeScript types
 */

export type BatchFileStatus = 'pending' | 'uploading' | 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled'
export type BatchJobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'

export interface BatchFile {
  id: string
  jobId: string
  filename: string
  filepath?: string
  status: BatchFileStatus
  sourceLang: string
  targetLang: string
  dubbing: boolean
  outputPath?: string
  errorMessage?: string
  createdAt: string
  updatedAt: string
}

export interface BatchJob {
  id: string
  status: BatchJobStatus
  totalFiles: number
  completedFiles: number
  failedFiles: number
  files: BatchFile[]
  createdAt: string
  updatedAt: string
}

export interface BatchFileSettingsUpdate {
  sourceLang?: string
  targetLang?: string
  dubbing?: boolean
}
