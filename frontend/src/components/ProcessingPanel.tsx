/**
 * Processing Panel Component
 */
import { useState, useEffect } from 'react'
import { Steps, Progress, message, Typography } from 'antd'
import { PlayCircleOutlined, PauseOutlined, DownloadOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { Video, ProcessingStatus, ProcessingJob, StageStatus, ProcessingStage } from '../types'
import {
  startSubtitleProcessing,
  startDubbingProcessing,
  cancelProcessing,
  getProcessingStatus,
  getSrtDownloadUrl,
} from '../services/api'

const { Text } = Typography

interface ProcessingPanelProps {
  video: Video
  initialStatus?: ProcessingStatus | null
  onStatusUpdate?: (status: ProcessingStatus) => void
}

const POLL_INTERVAL = 2000 // 2 seconds

// Default subtitle processing stages
const DEFAULT_SUBTITLE_STAGES: ProcessingStage[] = [
  { name: 'asr', displayName: '语音识别', status: 'pending' },
  { name: 'split_nlp', displayName: 'NLP 分句', status: 'pending' },
  { name: 'split_meaning', displayName: '语义分割', status: 'pending' },
  { name: 'summarize', displayName: '内容总结', status: 'pending' },
  { name: 'translate', displayName: '翻译', status: 'pending' },
  { name: 'split_sub', displayName: '字幕分割', status: 'pending' },
  { name: 'gen_sub', displayName: '生成字幕', status: 'pending' },
  { name: 'merge_sub', displayName: '合并字幕到视频', status: 'pending' },
]

// Default dubbing processing stages
const DEFAULT_DUBBING_STAGES: ProcessingStage[] = [
  { name: 'audio_task', displayName: '音频任务准备', status: 'pending' },
  { name: 'refer_audio', displayName: '参考音频提取', status: 'pending' },
  { name: 'gen_audio', displayName: '生成配音', status: 'pending' },
  { name: 'merge_audio', displayName: '合并音频', status: 'pending' },
  { name: 'dub_to_vid', displayName: '配音合成视频', status: 'pending' },
]

export default function ProcessingPanel({
  video: _video,
  initialStatus,
  onStatusUpdate,
}: ProcessingPanelProps) {
  const { t } = useTranslation()
  const [status, setStatus] = useState<ProcessingStatus | null>(initialStatus || null)
  const [_polling, setPolling] = useState(false)

  // Determine job states
  const subtitleJob = status?.subtitleJob
  const dubbingJob = status?.dubbingJob
  const isSubtitleProcessing = subtitleJob?.status === 'running'
  const isDubbingProcessing = dubbingJob?.status === 'running'
  const isProcessing = isSubtitleProcessing || isDubbingProcessing
  const subtitleCompleted = subtitleJob?.status === 'completed'

  // Poll for status updates
  useEffect(() => {
    if (!isProcessing) {
      setPolling(false)
      return
    }

    setPolling(true)
    const pollStatus = async () => {
      try {
        const newStatus = await getProcessingStatus()
        setStatus(newStatus)
        onStatusUpdate?.(newStatus)
      } catch (error) {
        console.error('Failed to poll status:', error)
      }
    }

    const interval = setInterval(pollStatus, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [isProcessing, onStatusUpdate])

  const handleStartSubtitle = async () => {
    try {
      await startSubtitleProcessing()
      const newStatus = await getProcessingStatus()
      setStatus(newStatus)
      onStatusUpdate?.(newStatus)
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('error'))
    }
  }

  const handleStartDubbing = async () => {
    try {
      await startDubbingProcessing()
      const newStatus = await getProcessingStatus()
      setStatus(newStatus)
      onStatusUpdate?.(newStatus)
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('error'))
    }
  }

  const handleCancel = async () => {
    try {
      await cancelProcessing()
      const newStatus = await getProcessingStatus()
      setStatus(newStatus)
      onStatusUpdate?.(newStatus)
      message.success(t('success'))
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('error'))
    }
  }

  const getStageStatus = (stage: { status: StageStatus }): 'wait' | 'process' | 'finish' | 'error' => {
    switch (stage.status) {
      case 'completed':
        return 'finish'
      case 'running':
        return 'process'
      case 'failed':
        return 'error'
      default:
        return 'wait'
    }
  }

  const renderJobProgress = (
    job: ProcessingJob | undefined, 
    title: string, 
    defaultStages: ProcessingStage[],
    showDefault: boolean = false
  ) => {
    const stages = job?.stages || (showDefault ? defaultStages : null)
    if (!stages) return null

    const jobStatus = job?.status || 'pending'
    const progress = job?.progress || 0
    const isActive = job !== undefined

    return (
      <div className="processing-job-card mb-6 p-5 rounded-2xl bg-gradient-to-br from-slate-50 to-slate-100 border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <Text strong className="text-slate-800 text-lg">{title}</Text>
          <span className={`status-tag ${
            jobStatus === 'completed' ? 'status-tag-success' :
            jobStatus === 'running' ? 'status-tag-processing' :
            jobStatus === 'failed' ? 'status-tag-error' :
            'status-tag-default'
          }`}>
            {isActive ? t(jobStatus) : t('pending')}
          </span>
        </div>
        
        <Progress 
          percent={Math.round(progress)} 
          status={
            jobStatus === 'completed' ? 'success' :
            jobStatus === 'failed' ? 'exception' :
            isActive ? 'active' : 'normal'
          }
          strokeColor={{
            '0%': '#667eea',
            '100%': '#764ba2',
          }}
          trailColor="rgba(0,0,0,0.06)"
        />

        <div className="mt-4 overflow-x-auto">
          <Steps
            size="small"
            className="modern-steps min-w-max"
            current={job ? job.stages.findIndex(s => s.status === 'running') : -1}
            items={stages.map((stage) => ({
              title: <span className="text-slate-600 text-xs whitespace-nowrap">{stage.displayName}</span>,
              status: getStageStatus(stage),
              description: stage.status === 'running' 
                ? <span className="text-purple-500 text-xs">
                    {stage.message || (stage.progress ? `${Math.round(stage.progress)}%` : '处理中...')}
                  </span>
                : stage.status === 'completed'
                ? <span className="text-green-500 text-xs">✓</span>
                : stage.status === 'failed'
                ? <span className="text-red-500 text-xs">✗</span>
                : null,
            }))}
          />
        </div>

        {job?.errorMessage && (
          <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
            {job.errorMessage}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="processing-panel space-y-6">
      {/* Subtitle Processing - Always show */}
      {renderJobProgress(
        subtitleJob, 
        t('subtitleProcessing'), 
        DEFAULT_SUBTITLE_STAGES, 
        true // Always show default stages
      )}

      {/* Dubbing Processing - Show only after subtitle completed */}
      {subtitleCompleted && renderJobProgress(
        dubbingJob, 
        t('dubbingProcessing'), 
        DEFAULT_DUBBING_STAGES,
        true
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-4 pt-2">
        {!subtitleJob && !isProcessing && (
          <button
            className="btn-primary flex items-center gap-2 text-white"
            onClick={handleStartSubtitle}
          >
            <PlayCircleOutlined />
            {t('startSubtitle')}
          </button>
        )}

        {subtitleCompleted && !dubbingJob && (
          <button
            className="btn-primary flex items-center gap-2 text-white"
            onClick={handleStartDubbing}
          >
            <PlayCircleOutlined />
            {t('startDubbing')}
          </button>
        )}

        {isProcessing && (
          <button
            className="btn-danger flex items-center gap-2 text-white"
            onClick={handleCancel}
          >
            <PauseOutlined />
            {t('cancel')}
          </button>
        )}

        {subtitleCompleted && (
          <a
            className="btn-secondary flex items-center gap-2"
            href={getSrtDownloadUrl()}
          >
            <DownloadOutlined />
            {t('download_srt')}
          </a>
        )}
      </div>
    </div>
  )
}
