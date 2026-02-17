/**
 * VideoList Page - Card grid layout showing all videos
 */
import { useState, useEffect, useCallback } from 'react'
import { Card, Tag, Button, Modal, Empty, Row, Col, Typography, Spin, Tooltip, message } from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  CloudUploadOutlined,
  YoutubeOutlined,
  VideoCameraOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import type { Video, VideoStatus, VideoSourceType } from '@/types'
import { getVideos, deleteVideo } from '@/services/api'
import VideoUpload from '@/components/VideoUpload'

const { Title, Text } = Typography

// ------------
// Helpers
// ------------

function getRelativeTime(dateString: string, t: (key: string, opts?: Record<string, unknown>) => string): string {
  const now = Date.now()
  const date = new Date(dateString).getTime()
  const diffMs = now - date

  if (diffMs < 0) return t('videoList.justNow')

  const seconds = Math.floor(diffMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) return t('videoList.justNow')
  if (minutes < 60) return t('videoList.minutesAgo', { count: minutes })
  if (hours < 24) return t('videoList.hoursAgo', { count: hours })
  if (days === 1) return t('videoList.yesterday')
  if (days < 7) return t('videoList.daysAgo', { count: days })

  const d = new Date(dateString)
  return d.toLocaleDateString()
}

function formatDuration(seconds?: number): string {
  if (seconds === undefined || seconds === null) return '--:--'
  const totalSeconds = Math.floor(seconds)
  const h = Math.floor(totalSeconds / 3600)
  const m = Math.floor((totalSeconds % 3600) / 60)
  const s = totalSeconds % 60
  const pad = (n: number) => n.toString().padStart(2, '0')
  if (h > 0) return `${pad(h)}:${pad(m)}:${pad(s)}`
  return `${pad(m)}:${pad(s)}`
}

const STATUS_COLOR_MAP: Record<VideoStatus, string> = {
  ready: 'blue',
  uploading: 'cyan',
  downloading: 'cyan',
  processing: 'orange',
  completed: 'green',
  error: 'red',
}

function getSourceIcon(sourceType: VideoSourceType) {
  if (sourceType === 'youtube') return <YoutubeOutlined />
  return <CloudUploadOutlined />
}

function truncateFilename(filename: string, maxLen: number = 28): string {
  if (filename.length <= maxLen) return filename
  const ext = filename.lastIndexOf('.')
  if (ext > 0 && filename.length - ext <= 6) {
    const nameMaxLen = maxLen - (filename.length - ext) - 3
    return `${filename.slice(0, nameMaxLen)}...${filename.slice(ext)}`
  }
  return `${filename.slice(0, maxLen - 3)}...`
}

// ------------
// Component
// ------------

export default function VideoList() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [videos, setVideos] = useState<Video[]>([])
  const [loading, setLoading] = useState(true)
  const [uploadModalOpen, setUploadModalOpen] = useState(false)

  const handleUploadSuccess = (video: Video) => {
    setUploadModalOpen(false)
    navigate(`/video/${video.id}`)
  }

  const fetchVideos = useCallback(async () => {
    try {
      setLoading(true)
      const data = await getVideos()
      setVideos(data)
    } catch {
      // API unavailable — gracefully show empty state
      setVideos([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchVideos()
  }, [fetchVideos])

  const handleDelete = (videoId: string, filename: string) => {
    Modal.confirm({
      title: t('deleteVideo'),
      content: t('videoList.confirmDeleteDesc', { filename }),
      okText: t('yes'),
      cancelText: t('no'),
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteVideo(videoId)
          setVideos((prev) => prev.filter((v) => v.id !== videoId))
          message.success(t('videoList.videoDeleted'))
        } catch {
          message.error(t('deleteFailed'))
        }
      },
    })
  }

  const handleCardClick = (videoId: string) => {
    navigate(`/video/${videoId}`)
  }

  // ------------
  // Render
  // ------------

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Spin size="large" />
          <p className="mt-4 text-gray-500">{t('videoList.loading')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Title level={3} className="!mb-1" style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            {t('videoList.title')}
          </Title>
          <Text className="text-gray-500">
            {videos.length > 0 ? t('videoList.videoCount', { count: videos.length }) : t('videoList.noVideosYet')}
          </Text>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          size="large"
          onClick={() => setUploadModalOpen(true)}
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            border: 'none',
            borderRadius: 10,
            height: 44,
            paddingInline: 24,
          }}
        >
          {t('videoList.newVideo')}
        </Button>
      </div>

      {/* Empty State */}
      {videos.length === 0 && (
        <Card className="modern-card">
          <Empty
            image={
              <div className="flex items-center justify-center">
                <div
                  className="w-28 h-28 rounded-2xl flex items-center justify-center"
                  style={{
                    background: 'linear-gradient(135deg, rgba(102,126,234,0.12) 0%, rgba(118,75,162,0.12) 100%)',
                  }}
                >
                  <VideoCameraOutlined style={{ fontSize: 48, color: '#667eea' }} />
                </div>
              </div>
            }
            description={
              <div className="space-y-2">
                <Text className="text-gray-500 text-base block">
                  {t('videoList.emptyDesc')}
                </Text>
              </div>
            }
          >
            <Button
              type="primary"
              icon={<PlusOutlined />}
              size="large"
              onClick={() => setUploadModalOpen(true)}
              style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                borderRadius: 10,
                height: 44,
                paddingInline: 28,
              }}
            >
              {t('videoList.uploadFirst')}
            </Button>
          </Empty>
        </Card>
      )}

      {/* Video Grid */}
      {videos.length > 0 && (
        <Row gutter={[20, 20]}>
          {videos.map((video) => (
            <Col key={video.id} xs={24} sm={12} lg={8}>
              <Card
                className="modern-card h-full cursor-pointer transition-all duration-200 hover:shadow-lg"
                hoverable
                bodyStyle={{ padding: 0 }}
                onClick={() => handleCardClick(video.id)}
              >
                {/* Thumbnail Placeholder */}
                <div
                  className="flex items-center justify-center relative"
                  style={{
                    height: 160,
                    background: 'linear-gradient(135deg, #f0f2f5 0%, #e8eaed 100%)',
                    borderRadius: '8px 8px 0 0',
                  }}
                >
                  <VideoCameraOutlined style={{ fontSize: 40, color: '#bfbfbf' }} />
                  {/* Duration Badge */}
                  <div
                    className="absolute bottom-2 right-2 px-2 py-0.5 rounded text-xs font-medium"
                    style={{
                      background: 'rgba(0,0,0,0.65)',
                      color: '#fff',
                    }}
                  >
                    {formatDuration(video.duration)}
                  </div>
                </div>

                {/* Card Body */}
                <div className="p-4 space-y-3">
                  {/* Filename */}
                  <Tooltip title={video.filename}>
                    <Text strong className="block text-base leading-snug" style={{ lineHeight: 1.4 }}>
                      {truncateFilename(video.filename)}
                    </Text>
                  </Tooltip>

                  {/* Tags Row */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <Tag color={STATUS_COLOR_MAP[video.status]}>
                      {t(video.status)}
                    </Tag>
                    <Tag icon={getSourceIcon(video.sourceType)} bordered={false}>
                      {video.sourceType === 'youtube' ? 'YouTube' : t('videoUpload')}
                    </Tag>
                  </div>

                  {/* Footer Row */}
                  <div className="flex items-center justify-between pt-1">
                    <Tooltip title={new Date(video.createdAt).toLocaleString()}>
                      <Text className="text-gray-400 text-xs flex items-center gap-1">
                        <ClockCircleOutlined />
                        {getRelativeTime(video.createdAt, t)}
                      </Text>
                    </Tooltip>

                    <Tooltip title={t('deleteVideo')}>
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDelete(video.id, video.filename)
                        }}
                      />
                    </Tooltip>
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}
      {/* Upload Modal */}
      <Modal
        title={t('videoUpload')}
        open={uploadModalOpen}
        onCancel={() => setUploadModalOpen(false)}
        footer={null}
        destroyOnClose
        width={520}
      >
        <VideoUpload onSuccess={handleUploadSuccess} />
      </Modal>
    </div>
  )
}
