/**
 * BatchStatusDashboard - Live processing status display for batch jobs
 */
import { Progress, Tag, Button, Space, Tooltip } from 'antd'
import {
  StopOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { BatchJob, BatchFileStatus } from '@/types/batch'

interface BatchStatusDashboardProps {
  job: BatchJob | null
  onCancel: () => void
  loading?: boolean
}

function getJobStatusTag(status: string, t: (key: string, fallback: string) => string) {
  switch (status) {
    case 'processing':
      return (
        <Tag icon={<SyncOutlined spin />} color="processing">
          {t('batchStatus.processing', '处理中')}
        </Tag>
      )
    case 'completed':
      return (
        <Tag icon={<CheckCircleOutlined />} color="success">
          {t('batchStatus.completed', '已完成')}
        </Tag>
      )
    case 'failed':
      return (
        <Tag icon={<CloseCircleOutlined />} color="error">
          {t('batchStatus.failed', '失败')}
        </Tag>
      )
    case 'cancelled':
      return (
        <Tag icon={<ExclamationCircleOutlined />} color="warning">
          {t('batchStatus.cancelled', '已取消')}
        </Tag>
      )
    default:
      return (
        <Tag icon={<ClockCircleOutlined />} color="default">
          {t('batchStatus.pending', '等待中')}
        </Tag>
      )
  }
}

function getFileStatusColor(status: BatchFileStatus): string {
  switch (status) {
    case 'processing':
      return 'blue'
    case 'completed':
      return 'green'
    case 'failed':
      return 'red'
    case 'cancelled':
      return 'orange'
    default:
      return 'default'
  }
}

export default function BatchStatusDashboard({
  job,
  onCancel,
  loading = false,
}: BatchStatusDashboardProps) {
  const { t } = useTranslation()

  if (!job) return null

  const totalFiles = job.totalFiles || job.files.length
  const completedFiles = job.completedFiles || 0
  const failedFiles = job.failedFiles || 0
  const progressPercent =
    totalFiles > 0 ? Math.round(((completedFiles + failedFiles) / totalFiles) * 100) : 0

  const isProcessing = job.status === 'processing'
  const isFinished = ['completed', 'failed', 'cancelled'].includes(job.status)

  return (
    <div className="space-y-4">
      {/* Header: status badge + cancel button */}
      <div className="flex items-center justify-between">
        <Space>
          <span className="text-gray-300 font-medium">
            {t('batchProcessingStatus', '处理状态')}
          </span>
          {getJobStatusTag(job.status, t)}
        </Space>
        {isProcessing && (
          <Button
            danger
            icon={<StopOutlined />}
            onClick={onCancel}
            loading={loading}
          >
            {t('cancelBatch', '取消处理')}
          </Button>
        )}
      </div>

      {/* Overall progress */}
      <div>
        <div className="flex justify-between text-sm text-gray-400 mb-1">
          <span>
            {t('progress', '进度')}: {completedFiles + failedFiles} / {totalFiles}
          </span>
          <span>
            {completedFiles} {t('succeeded', '成功')}
            {failedFiles > 0 && (
              <span className="text-red-400 ml-2">
                {failedFiles} {t('failed', '失败')}
              </span>
            )}
          </span>
        </div>
        <Progress
          percent={progressPercent}
          status={
            isFinished
              ? failedFiles > 0 && completedFiles === 0
                ? 'exception'
                : 'success'
              : 'active'
          }
          strokeColor={{
            '0%': '#667eea',
            '100%': '#764ba2',
          }}
          trailColor="rgba(255,255,255,0.1)"
        />
      </div>

      {/* File-by-file status */}
      {job.files.length > 0 && (
        <div className="rounded-lg border border-white/10 overflow-hidden">
          <div className="px-4 py-2 border-b border-white/10 text-sm text-gray-400 font-medium">
            {t('fileProcessingDetails', '文件处理详情')}
          </div>
          <div className="max-h-64 overflow-y-auto">
            {job.files.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between px-4 py-2 border-b border-white/5 last:border-b-0"
              >
                <span className="text-sm text-gray-300 truncate flex-1 mr-3">
                  {file.filename}
                </span>
                <Space size="small">
                  <Tag color={getFileStatusColor(file.status)}>
                    {t(`batchStatus.${file.status}`, file.status)}
                  </Tag>
                  {file.errorMessage && (
                    <Tooltip title={file.errorMessage}>
                      <ExclamationCircleOutlined className="text-red-400 cursor-help" />
                    </Tooltip>
                  )}
                </Space>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
