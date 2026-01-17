/**
 * Video Upload Component
 */
import { useState } from 'react'
import { Progress, message } from 'antd'
import { CloudUploadOutlined, VideoCameraOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { Video } from '../types'
import { uploadVideo } from '../services/api'

interface VideoUploadProps {
  onSuccess: (video: Video) => void
}

export default function VideoUpload({ onSuccess }: VideoUploadProps) {
  const { t } = useTranslation()
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [dragActive, setDragActive] = useState(false)

  const handleUpload = async (file: File) => {
    try {
      setUploading(true)
      setProgress(0)
      
      const video = await uploadVideo(file, (p) => {
        setProgress(p)
      })
      
      message.success(t('success'))
      onSuccess(video)
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('error'))
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('video/')) {
      handleUpload(file)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(true)
  }

  const handleDragLeave = () => {
    setDragActive(false)
  }

  const handleClick = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'video/*,.mp4,.avi,.mkv,.mov,.webm'
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (file) handleUpload(file)
    }
    input.click()
  }

  return (
    <div className="space-y-4">
      <div
        className={`upload-area ${dragActive ? 'upload-area-active' : ''} ${uploading ? 'pointer-events-none opacity-50' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={!uploading ? handleClick : undefined}
      >
        <div className="upload-icon">
          <CloudUploadOutlined style={{ fontSize: 48 }} />
        </div>
        <p className="upload-text">{t('dragOrClick')}</p>
        <p className="upload-hint">
          <VideoCameraOutlined className="mr-2" />
          {t('supportedFormats')}
        </p>
      </div>

      {uploading && (
        <div className="upload-progress">
          <Progress 
            percent={progress} 
            status="active" 
            strokeColor={{
              '0%': '#667eea',
              '100%': '#764ba2',
            }}
            trailColor="rgba(255,255,255,0.1)"
          />
          <p className="text-center text-gray-400 mt-3 flex items-center justify-center gap-2">
            <span className="inline-block w-2 h-2 bg-purple-500 rounded-full animate-pulse"></span>
            {t('uploading')}
          </p>
        </div>
      )}
    </div>
  )
}
