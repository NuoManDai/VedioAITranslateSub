/**
 * Home Page - Video Detail interface (parameterized by URL :id)
 */
import { useState, useEffect, useRef } from 'react'
import { Card, message, Modal, Result, Button } from 'antd'
import { PlayCircleOutlined, RocketOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate, Link } from 'react-router-dom'
import VideoPlayer from '../components/VideoPlayer'
import ProcessingPanel from '../components/ProcessingPanel'
import ConsolePanel from '../components/ConsolePanel'
import type { Video, ProcessingStatus } from '../types'
import { getVideo, deleteVideo, getProcessingStatus, cleanupAllFiles, ApiRequestError } from '../services/api'

export default function Home() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [video, setVideo] = useState<Video | null>(null)
  const [status, setStatus] = useState<ProcessingStatus | null>(null)
  const [_loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const recoveryPromptShownRef = useRef(false)

  useEffect(() => {
    loadInitialState()
  }, [id])

  const loadInitialState = async () => {
    if (!id) {
      setError(t('videoDetail.noVideoId'))
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)
      const [currentVideo, processingStatus] = await Promise.all([
        getVideo(id),
        getProcessingStatus(id),
      ])
      setVideo(currentVideo)
      setStatus(processingStatus)

      // Check for unfinished task
      if (processingStatus?.hasUnfinishedTask && !recoveryPromptShownRef.current) {
        recoveryPromptShownRef.current = true
        showRecoveryPrompt()
      }
    } catch (err) {
      if (err instanceof ApiRequestError && err.statusCode === 404) {
        setError(t('videoDetail.videoNotFound'))
      } else {
        console.error('Failed to load initial state:', err)
        setError(t('videoDetail.loadFailed'))
      }
    } finally {
      setLoading(false)
    }
  }

  const showRecoveryPrompt = () => {
    Modal.confirm({
      title: t('recoveryPrompt'),
      okText: t('continueTask'),
      cancelText: t('startOver'),
      onCancel: async () => {
        try {
          await cleanupAllFiles(id!)
          const newStatus = await getProcessingStatus(id!)
          setStatus(newStatus)
          message.success(t('cleanupAllSuccess') || '已清理所有缓存，可以重新开始处理')
        } catch {
          message.error(t('error'))
        }
      },
    })
  }

  const handleDelete = async () => {
    Modal.confirm({
      title: t('confirmDelete'),
      okText: t('yes'),
      cancelText: t('no'),
      onOk: async () => {
        try {
          await deleteVideo(id!)
          navigate('/')
          message.success(t('success'))
        } catch {
          message.error(t('error'))
        }
      },
    })
  }

  const handleStatusUpdate = (newStatus: ProcessingStatus) => {
    setStatus(newStatus)
    if (newStatus.video) {
      setVideo(newStatus.video as Video)
    }
  }

  // Error state - video not found
  if (error) {
    return (
      <div className="space-y-8 animate-fade-in-up">
        <Result
          status="404"
          title={t('videoDetail.videoNotFound')}
          subTitle={error}
          extra={
            <Link to="/">
              <Button type="primary" icon={<ArrowLeftOutlined />}>
                {t('videoList.backToVideos')}
              </Button>
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* Back to list link */}
      <Link to="/" className="inline-flex items-center gap-1 text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeftOutlined /> {t('videoList.backToVideos')}
      </Link>

      {/* Video Player Section */}
      {video && (
        <Card 
          className="modern-card"
          title={
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                   style={{ background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)' }}>
                <PlayCircleOutlined className="text-white" />
              </div>
              <span>{t('videoPreview') || 'Video Preview'}</span>
            </div>
          }
        >
          <VideoPlayer 
            video={video} 
            onDelete={handleDelete} 
            subtitleCompleted={status?.subtitleJob?.status === 'completed'}
          />
        </Card>
      )}

      {/* Processing Panel Section */}
      {video && (
        <Card 
          className="modern-card"
          title={
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                   style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
                <RocketOutlined className="text-white" />
              </div>
              <span>{t('processControl')}</span>
            </div>
          }
        >
          <ProcessingPanel
            video={video}
            initialStatus={status}
            onStatusUpdate={handleStatusUpdate}
          />
        </Card>
      )}

      {/* Console Panel - Always visible when video is loaded */}
      {video && (
        <ConsolePanel 
          isProcessing={
            status?.subtitleJob?.status === 'running' || 
            status?.dubbingJob?.status === 'running'
          }
          videoId={video.id}
          className="mt-6"
        />
      )}
    </div>
  )
}

