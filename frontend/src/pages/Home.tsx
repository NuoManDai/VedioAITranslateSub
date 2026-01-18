/**
 * Home Page - Main application interface
 */
import { useState, useEffect } from 'react'
import { Card, Row, Col, message, Modal, Typography } from 'antd'
import { CloudUploadOutlined, YoutubeOutlined, PlayCircleOutlined, RocketOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import VideoUpload from '../components/VideoUpload'
import YouTubeDownload from '../components/YouTubeDownload'
import VideoPlayer from '../components/VideoPlayer'
import ProcessingPanel from '../components/ProcessingPanel'
import ConsolePanel from '../components/ConsolePanel'
import type { Video, ProcessingStatus } from '../types'
import { getCurrentVideo, deleteCurrentVideo, getProcessingStatus } from '../services/api'

const { Title, Text } = Typography

export default function Home() {
  const { t } = useTranslation()
  const [video, setVideo] = useState<Video | null>(null)
  const [status, setStatus] = useState<ProcessingStatus | null>(null)
  const [_loading, setLoading] = useState(true)

  useEffect(() => {
    loadInitialState()
  }, [])

  const loadInitialState = async () => {
    try {
      setLoading(true)
      const [currentVideo, processingStatus] = await Promise.all([
        getCurrentVideo(),
        getProcessingStatus(),
      ])
      setVideo(currentVideo)
      setStatus(processingStatus)
      
      // Check for unfinished task
      if (processingStatus?.hasUnfinishedTask) {
        showRecoveryPrompt()
      }
    } catch (error) {
      console.error('Failed to load initial state:', error)
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
          await deleteCurrentVideo()
          setVideo(null)
          setStatus(null)
        } catch (error) {
          message.error(t('error'))
        }
      },
    })
  }

  const handleVideoLoaded = (newVideo: Video) => {
    setVideo(newVideo)
  }

  const handleDelete = async () => {
    Modal.confirm({
      title: t('confirmDelete'),
      okText: t('yes'),
      cancelText: t('no'),
      onOk: async () => {
        try {
          await deleteCurrentVideo()
          setVideo(null)
          setStatus(null)
          message.success(t('success'))
        } catch (error) {
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

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* Hero Section - Video Input */}
      {!video && (
        <>
          <div className="text-center mb-8">
            <Title level={2} className="!mb-2" style={{ 
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              {t('home.title') || 'AI Video Translation'}
            </Title>
            <Text className="text-gray-500 text-lg">
              {t('home.subtitle') || 'Upload a video or paste a YouTube link to get started'}
            </Text>
          </div>
          
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <Card 
                className="modern-card h-full"
                title={
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                         style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
                      <CloudUploadOutlined className="text-white" />
                    </div>
                    <span>{t('videoUpload')}</span>
                  </div>
                }
              >
                <VideoUpload onSuccess={handleVideoLoaded} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card 
                className="modern-card h-full"
                title={
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                         style={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
                      <YoutubeOutlined className="text-white" />
                    </div>
                    <span>{t('youtubeDownload')}</span>
                  </div>
                }
              >
                <YouTubeDownload onSuccess={handleVideoLoaded} />
              </Card>
            </Col>
          </Row>
        </>
      )}

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
          className="mt-6"
        />
      )}
    </div>
  )
}
