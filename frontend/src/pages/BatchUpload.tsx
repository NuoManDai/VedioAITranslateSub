/**
 * Batch Upload Page - Batch video upload and processing
 */
import { useState, useRef, useCallback, useEffect } from 'react'
import { Typography, Card, Space, Button, message, Modal } from 'antd'
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { BatchUploader, BatchFileList, BatchStatusDashboard } from '@/components/batch'
import {
  createBatch,
  getBatchStatus,
  startBatchProcessing,
  cancelBatch,
  registerFile,
  uploadBatchFile,
  updateFileSettings,
  removeFile,
} from '@/services/batchApi'
import type { BatchFile, BatchJob, BatchFileSettingsUpdate } from '@/types/batch'

const { Title } = Typography

const POLL_INTERVAL = 2000

export default function BatchUpload() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  // ------------
  // State
  // ------------
  const [jobId, setJobId] = useState<string | null>(null)
  const [files, setFiles] = useState<BatchFile[]>([])
  const [job, setJob] = useState<BatchJob | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({})
  const [starting, setStarting] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ------------
  // Polling
  // ------------
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }, [])

  const startPolling = useCallback(
    (id: string) => {
      stopPolling()
      pollingRef.current = setInterval(async () => {
        try {
          const status = await getBatchStatus(id)
          setJob(status)
          setFiles(status.files)

          // Stop polling when job is finished
          if (['completed', 'failed', 'cancelled'].includes(status.status)) {
            stopPolling()
          }
        } catch {
          // Silently retry on polling errors
        }
      }, POLL_INTERVAL)
    },
    [stopPolling]
  )

  // Cleanup polling on unmount
  useEffect(() => {
    return () => stopPolling()
  }, [stopPolling])

  // ------------
  // Upload Flow
  // ------------
  const handleFilesSelected = useCallback(
    async (selectedFiles: File[]) => {
      setUploading(true)
      setUploadProgress({})

      try {
        // Create batch job if none exists
        let currentJobId = jobId
        if (!currentJobId) {
          const result = await createBatch()
          currentJobId = result.jobId
          setJobId(currentJobId)
        }

        // Register and upload each file sequentially
        for (const file of selectedFiles) {
          try {
            // Register file
            const batchFile = await registerFile(currentJobId, file.name)

            // Update local state immediately
            setFiles((prev) => [...prev, batchFile])

            // Upload file content with progress tracking
            const uploaded = await uploadBatchFile(
              currentJobId,
              batchFile.id,
              file,
              (progress) => {
                setUploadProgress((prev) => ({
                  ...prev,
                  [file.name]: progress,
                }))
              }
            )

            // Update file state with upload result
            setFiles((prev) =>
              prev.map((f) => (f.id === uploaded.id ? uploaded : f))
            )
          } catch (error) {
            const msg =
              error instanceof Error ? error.message : t('uploadFailed', '上传失败')
            message.error(`${file.name}: ${msg}`)
          }
        }
      } catch (error) {
        const msg =
          error instanceof Error ? error.message : t('createBatchFailed', '创建批次失败')
        message.error(msg)
      } finally {
        setUploading(false)
        setUploadProgress({})
      }
    },
    [jobId, t]
  )

  // ------------
  // Settings Change
  // ------------
  const handleSettingsChange = useCallback(
    async (fileId: string, settings: BatchFileSettingsUpdate) => {
      if (!jobId) return
      try {
        const updated = await updateFileSettings(jobId, fileId, settings)
        setFiles((prev) => prev.map((f) => (f.id === updated.id ? updated : f)))
      } catch (error) {
        const msg =
          error instanceof Error ? error.message : t('updateFailed', '更新失败')
        message.error(msg)
      }
    },
    [jobId, t]
  )

  // ------------
  // Delete File
  // ------------
  const handleDeleteFile = useCallback(
    async (fileId: string) => {
      if (!jobId) return
      try {
        await removeFile(jobId, fileId)
        setFiles((prev) => prev.filter((f) => f.id !== fileId))
      } catch (error) {
        const msg =
          error instanceof Error ? error.message : t('deleteFailed', '删除失败')
        message.error(msg)
      }
    },
    [jobId, t]
  )

  // ------------
  // Start Processing
  // ------------
  const handleStartProcessing = useCallback(async () => {
    if (!jobId) return

    Modal.confirm({
      title: t('confirmStartBatch', '确认开始批量处理？'),
      content: t(
        'confirmStartBatchDesc',
        `将处理 ${files.length} 个文件，处理期间无法使用单文件翻译功能。`
      ),
      okText: t('startProcessing', '开始处理'),
      cancelText: t('cancel', '取消'),
      onOk: async () => {
        setStarting(true)
        try {
          const result = await startBatchProcessing(jobId)
          setJob(result)
          setFiles(result.files)
          startPolling(jobId)
        } catch (error) {
          const msg =
            error instanceof Error ? error.message : t('startFailed', '启动失败')
          message.error(msg)
        } finally {
          setStarting(false)
        }
      },
    })
  }, [jobId, files.length, startPolling, t])

  // ------------
  // Cancel Processing
  // ------------
  const handleCancel = useCallback(async () => {
    if (!jobId) return
    setCancelling(true)
    try {
      const result = await cancelBatch(jobId)
      setJob(result)
      setFiles(result.files)
      stopPolling()
    } catch (error) {
      const msg =
        error instanceof Error ? error.message : t('cancelFailed', '取消失败')
      message.error(msg)
    } finally {
      setCancelling(false)
    }
  }, [jobId, stopPolling, t])

  // ------------
  // Reset (new batch)
  // ------------
  const handleReset = useCallback(() => {
    stopPolling()
    setJobId(null)
    setFiles([])
    setJob(null)
    setUploading(false)
    setUploadProgress({})
    setStarting(false)
    setCancelling(false)
  }, [stopPolling])

  // ------------
  // Derived State
  // ------------
  const isProcessing = job?.status === 'processing'
  const isFinished = job
    ? ['completed', 'failed', 'cancelled'].includes(job.status)
    : false
  const canUpload = !isProcessing && !uploading
  const canStart = files.length > 0 && !isProcessing && !uploading && !isFinished
  const showDashboard = job && (isProcessing || isFinished)

  return (
    <div className="max-w-6xl mx-auto py-8 px-6">
      <Space direction="vertical" size="large" className="w-full">
        {/* Header */}
        <div className="flex items-center justify-between">
          <Space>
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/')}
            >
              {t('back', '返回')}
            </Button>
            <Title level={3} style={{ margin: 0 }}>
              {t('batchUpload', '批量上传')}
            </Title>
          </Space>
          {isFinished && (
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              {t('newBatch', '新建批次')}
            </Button>
          )}
        </div>

        {/* Upload Area - show when not processing/finished */}
        {canUpload && !isFinished && (
          <BatchUploader
            onFilesSelected={handleFilesSelected}
            uploading={uploading}
            uploadProgress={uploadProgress}
          />
        )}

        {/* File List */}
        {files.length > 0 && !showDashboard && (
          <Card title={t('fileList', '文件列表')}>
            <BatchFileList
              files={files}
              onSettingsChange={handleSettingsChange}
              onDelete={handleDeleteFile}
              disabled={isProcessing || uploading}
            />
          </Card>
        )}

        {/* Start Processing Button */}
        {canStart && (
          <div className="flex justify-center">
            <Button
              type="primary"
              size="large"
              icon={<PlayCircleOutlined />}
              onClick={handleStartProcessing}
              loading={starting}
              style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                height: 48,
                paddingLeft: 32,
                paddingRight: 32,
                fontSize: 16,
              }}
            >
              {t('startBatchProcessing', '开始批量处理')} ({files.length}{' '}
              {t('files', '个文件')})
            </Button>
          </div>
        )}

        {/* Status Dashboard - show during/after processing */}
        {showDashboard && (
          <Card title={t('batchProcessingStatus', '处理状态')}>
            <BatchStatusDashboard
              job={job}
              onCancel={handleCancel}
              loading={cancelling}
            />
          </Card>
        )}
      </Space>
    </div>
  )
}
