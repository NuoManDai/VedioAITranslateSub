/**
 * Video Player Component
 */
import { Button, Typography, Tooltip } from 'antd'
import { DeleteOutlined, ClockCircleOutlined, FileOutlined, YoutubeOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { Video } from '../types'
import { getVideoStreamUrl } from '../services/api'

const { Text } = Typography

interface VideoPlayerProps {
  video: Video
  onDelete?: () => void
}

export default function VideoPlayer({ video, onDelete }: VideoPlayerProps) {
  const { t } = useTranslation()

  const videoUrl = getVideoStreamUrl(video.filename)

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return '-'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }

  const formatDuration = (seconds?: number): string => {
    if (!seconds) return '-'
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="space-y-4">
      {/* Video Player */}
      <div className="video-container">
        <video
          src={videoUrl}
          controls
          className="w-full h-full"
        >
          Your browser does not support the video tag.
        </video>
      </div>

      {/* Video Info Bar */}
      <div className="video-info flex items-center justify-between flex-wrap gap-4">
        <div className="flex-1 min-w-0">
          <Tooltip title={video.filename}>
            <Text className="video-title block">{video.filename}</Text>
          </Tooltip>
          <div className="flex items-center gap-4 mt-2 text-gray-400 text-sm">
            {video.sourceType === 'youtube' && (
              <span className="flex items-center gap-1">
                <YoutubeOutlined style={{ color: '#ff4d4f' }} />
                <span>YouTube</span>
              </span>
            )}
            <span className="flex items-center gap-1">
              <FileOutlined />
              <span>{formatFileSize(video.fileSize)}</span>
            </span>
            <span className="flex items-center gap-1">
              <ClockCircleOutlined />
              <span>{formatDuration(video.duration)}</span>
            </span>
          </div>
        </div>

        {onDelete && (
          <Button
            className="btn-danger"
            icon={<DeleteOutlined />}
            onClick={onDelete}
          >
            {t('deleteVideo')}
          </Button>
        )}
      </div>
    </div>
  )
}
