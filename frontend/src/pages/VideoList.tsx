/**
 * VideoList Page - Card grid layout showing all videos
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { Card, Tag, Button, Modal, Empty, Row, Col, Typography, Spin, Tooltip, message, Input, Select } from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  CloudUploadOutlined,
  YoutubeOutlined,
  VideoCameraOutlined,
  ClockCircleOutlined,
  EditOutlined,
  SearchOutlined,
  CheckOutlined,
  CloseOutlined,
  LoadingOutlined,
  FilterOutlined,
  SortAscendingOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import type { Video, VideoStatus, VideoSourceType } from '@/types'
import { getVideos, deleteVideo, renameVideo, getVideoThumbnailUrl } from '@/services/api'
import VideoUpload from '@/components/VideoUpload'

const { Title, Text } = Typography
const PAGE_SIZE = 20

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
  const [failedThumbnails, setFailedThumbnails] = useState<Set<string>>(new Set())
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [total, setTotal] = useState(0)
  const sentinelRef = useRef<HTMLDivElement>(null)
  const [searchKeyword, setSearchKeyword] = useState('')
  const searchTimerRef = useRef<ReturnType<typeof setTimeout>>()
  const videosRef = useRef<Video[]>([])
  videosRef.current = videos
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterSource, setFilterSource] = useState<string>('all')
  const [sortBy, setSortBy] = useState<string>('created_at')
  const [sortOrder, setSortOrder] = useState<string>('desc')

  const handleUploadSuccess = (video: Video) => {
    setUploadModalOpen(false)
    navigate(`/video/${video.id}`)
  }

  const fetchVideos = useCallback(async (reset = false) => {
    try {
      if (reset) {
        setLoading(true)
      } else {
        setLoadingMore(true)
      }
      const offset = reset ? 0 : videosRef.current.length
      const data = await getVideos({
        offset,
        limit: PAGE_SIZE,
        keyword: searchKeyword || undefined,
        status: filterStatus !== 'all' ? filterStatus : undefined,
        sourceType: filterSource !== 'all' ? filterSource : undefined,
        sortBy,
        sortOrder,
      })
      if (reset) {
        setVideos(data.items)
      } else {
        setVideos((prev) => [...prev, ...data.items])
      }
      setTotal(data.total)
      setHasMore(data.hasMore)
    } catch {
      if (reset) {
        setVideos([])
        setTotal(0)
      }
      setHasMore(false)
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [searchKeyword, filterStatus, filterSource, sortBy, sortOrder])

  useEffect(() => {
    fetchVideos(true)
  }, [fetchVideos])

  // Infinite scroll via IntersectionObserver
  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore && !loading) {
          fetchVideos(false)
        }
      },
      { rootMargin: '200px' }
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [hasMore, loadingMore, loading, fetchVideos])

  const handleSearchChange = (value: string) => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => {
      setSearchKeyword(value)
    }, 300)
  }

  const handleSortChange = (value: string) => {
    const [field, order] = value.split('_')
    setSortBy(field === 'filename' ? 'filename' : field === 'duration' ? 'duration' : 'created_at')
    setSortOrder(order === 'asc' ? 'asc' : 'desc')
  }

  const sortValue = `${sortBy}_${sortOrder}`

  const STATUS_FILTERS = [
    { key: 'all', label: t('videoList.filterAll') },
    { key: 'ready', label: t('videoList.filterReady'), color: STATUS_COLOR_MAP.ready },
    { key: 'processing', label: t('videoList.filterProcessing'), color: STATUS_COLOR_MAP.processing },
    { key: 'completed', label: t('videoList.filterCompleted'), color: STATUS_COLOR_MAP.completed },
    { key: 'error', label: t('videoList.filterError'), color: STATUS_COLOR_MAP.error },
  ]

  const SOURCE_FILTERS = [
    { key: 'all', label: t('videoList.filterAll') },
    { key: 'upload', label: t('videoList.filterUpload') },
    { key: 'youtube', label: t('videoList.filterYoutube') },
  ]

  const handleRename = async (videoId: string) => {
    const trimmed = editingName.trim()
    if (!trimmed) {
      setEditingId(null)
      return
    }
    try {
      const updated = await renameVideo(videoId, trimmed)
      setVideos((prev) => prev.map((v) => (v.id === videoId ? { ...v, filename: updated.filename } : v)))
      message.success(t('videoList.renameSuccess'))
    } catch {
      message.error(t('videoList.renameFailed'))
    }
    setEditingId(null)
  }

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
          setTotal((prev) => prev - 1)
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
            {total > 0 ? t('videoList.videoCount', { count: total }) : t('videoList.noVideosYet')}
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

      {/* Search & Filter Toolbar */}
      <div
        className="rounded-xl p-4 space-y-3"
        style={{
          background: 'linear-gradient(135deg, rgba(102,126,234,0.04) 0%, rgba(118,75,162,0.04) 100%)',
          border: '1px solid rgba(102,126,234,0.1)',
        }}
      >
        {/* Search Row */}
        <Input
          placeholder={t('videoList.search')}
          prefix={<SearchOutlined style={{ color: '#667eea' }} />}
          allowClear
          size="large"
          onChange={(e) => handleSearchChange(e.target.value)}
          style={{ borderRadius: 10 }}
        />

        {/* Filters Row */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          {/* Status Filter */}
          <div className="flex items-center gap-2 flex-wrap flex-1">
            <Text className="text-gray-400 text-xs flex items-center gap-1 shrink-0">
              <FilterOutlined />
              {t('videoList.filterStatus')}
            </Text>
            {STATUS_FILTERS.map((f) => (
              <Tag.CheckableTag
                key={f.key}
                checked={filterStatus === f.key}
                onChange={() => setFilterStatus(f.key)}
                style={{
                  borderRadius: 6,
                  padding: '2px 10px',
                  border: filterStatus === f.key ? 'none' : '1px solid #d9d9d9',
                  ...(filterStatus === f.key && f.color ? {} : {}),
                }}
              >
                {f.label}
              </Tag.CheckableTag>
            ))}
          </div>

          {/* Source Filter */}
          <div className="flex items-center gap-2 flex-wrap flex-1">
            <Text className="text-gray-400 text-xs flex items-center gap-1 shrink-0">
              <FilterOutlined />
              {t('videoList.filterSource')}
            </Text>
            {SOURCE_FILTERS.map((f) => (
              <Tag.CheckableTag
                key={f.key}
                checked={filterSource === f.key}
                onChange={() => setFilterSource(f.key)}
                style={{
                  borderRadius: 6,
                  padding: '2px 10px',
                  border: filterSource === f.key ? 'none' : '1px solid #d9d9d9',
                }}
              >
                {f.key === 'youtube' && <YoutubeOutlined style={{ marginRight: 4 }} />}
                {f.key === 'upload' && <CloudUploadOutlined style={{ marginRight: 4 }} />}
                {f.label}
              </Tag.CheckableTag>
            ))}
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2 shrink-0">
            <Text className="text-gray-400 text-xs flex items-center gap-1">
              <SortAscendingOutlined />
              {t('videoList.sortBy')}
            </Text>
            <Select
              value={sortValue}
              onChange={handleSortChange}
              size="small"
              style={{ width: 140, borderRadius: 8 }}
              options={[
                { value: 'created_at_desc', label: t('videoList.sortNewest') },
                { value: 'created_at_asc', label: t('videoList.sortOldest') },
                { value: 'filename_asc', label: t('videoList.sortNameAZ') },
                { value: 'filename_desc', label: t('videoList.sortNameZA') },
                { value: 'duration_desc', label: t('videoList.sortDuration') },
              ]}
            />
          </div>
        </div>
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
        <>
        <Row gutter={[20, 20]}>
          {videos.map((video) => (
            <Col key={video.id} xs={24} sm={12} lg={8}>
              <Card
                className="modern-card h-full cursor-pointer transition-all duration-300"
                hoverable
                bodyStyle={{ padding: 0 }}
                onClick={() => handleCardClick(video.id)}
                style={{ borderRadius: 12, overflow: 'hidden' }}
              >
                {/* Thumbnail */}
                <div
                  className="flex items-center justify-center relative overflow-hidden"
                  style={{
                    height: 180,
                    background: 'linear-gradient(135deg, #f0f2f5 0%, #e8eaed 100%)',
                  }}
                >
                  {failedThumbnails.has(video.id) ? (
                    <VideoCameraOutlined style={{ fontSize: 40, color: '#bfbfbf' }} />
                  ) : (
                    <img
                      src={getVideoThumbnailUrl(video.id)}
                      alt={video.filename}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      onError={() => setFailedThumbnails((prev) => new Set(prev).add(video.id))}
                    />
                  )}
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
                  {editingId === video.id ? (
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <Input
                        size="small"
                        value={editingName}
                        onChange={(e) => setEditingName(e.target.value)}
                        onPressEnter={() => handleRename(video.id)}
                        onKeyDown={(e) => { if (e.key === 'Escape') setEditingId(null) }}
                        autoFocus
                        style={{ flex: 1 }}
                      />
                      <Button
                        type="text"
                        size="small"
                        icon={<CheckOutlined />}
                        style={{ color: '#52c41a' }}
                        onClick={() => handleRename(video.id)}
                      />
                      <Button
                        type="text"
                        size="small"
                        icon={<CloseOutlined />}
                        onClick={() => setEditingId(null)}
                      />
                    </div>
                  ) : (
                    <div className="flex items-center gap-1">
                      <Tooltip title={video.filename}>
                        <Text strong className="block text-base leading-snug flex-1" style={{ lineHeight: 1.4 }}>
                          {truncateFilename(video.filename)}
                        </Text>
                      </Tooltip>
                      <Tooltip title={t('videoList.rename')}>
                        <Button
                          type="text"
                          size="small"
                          icon={<EditOutlined />}
                          onClick={(e) => {
                            e.stopPropagation()
                            setEditingId(video.id)
                            setEditingName(video.filename)
                          }}
                        />
                      </Tooltip>
                    </div>
                  )}

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

        {/* Infinite scroll sentinel */}
        <div ref={sentinelRef} style={{ height: 1 }} />

        {loadingMore && (
          <div className="flex justify-center py-4">
            <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
          </div>
        )}

        {!hasMore && videos.length > 0 && (
          <div className="text-center py-4">
            <Text className="text-gray-400">{t('videoList.noMoreVideos')}</Text>
          </div>
        )}
        </>
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
