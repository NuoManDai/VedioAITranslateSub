/**
 * Processing Panel Component
 */
import { useState, useEffect } from 'react'
import { Steps, Progress, message, Typography, Modal, Tabs } from 'antd'
import { PlayCircleOutlined, PauseOutlined, DownloadOutlined, ReloadOutlined, FileTextOutlined, SoundOutlined, CheckCircleOutlined, DeleteOutlined, EditOutlined, MergeCellsOutlined } from '@ant-design/icons'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { Video, ProcessingStatus, ProcessingJob, StageStatus, ProcessingStage } from '../types'
import {
  startSubtitleProcessing,
  startDubbingProcessing,
  cancelProcessing,
  getProcessingStatus,
  getSrtDownloadUrl,
  cleanupSubtitleFiles,
  cleanupDubbingFiles,
  cleanupAllFiles,
} from '../services/api'
import StageOutputFiles from './StageOutputFiles'

const { Text } = Typography
const { confirm } = Modal

interface ProcessingPanelProps {
  video: Video
  initialStatus?: ProcessingStatus | null
  onStatusUpdate?: (status: ProcessingStatus) => void
}

const POLL_INTERVAL = 3000 // 3 seconds

// Default subtitle processing stages (校对和合并移至独立Tab)
const DEFAULT_SUBTITLE_STAGES: ProcessingStage[] = [
  { name: 'asr', displayName: '语音识别', status: 'pending' },
  { name: 'split_nlp', displayName: '文本粗切分', status: 'pending' },
  { name: 'split_meaning', displayName: 'GPT 语义分句', status: 'pending' },
  { name: 'summarize', displayName: '内容总结', status: 'pending' },
  { name: 'translate', displayName: '翻译', status: 'pending' },
  { name: 'split_sub', displayName: '字幕分割', status: 'pending' },
  { name: 'gen_sub', displayName: '生成字幕', status: 'pending' },
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
  const subtitleMerged = status?.subtitleMerged ?? false
  
  // Use backend-provided flags for button states
  const canStartSubtitle = status?.canStartSubtitle ?? false
  const canStartDubbing = status?.canStartDubbing ?? false

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

  const handleRestartSubtitle = () => {
    confirm({
      title: t('confirmRestartSubtitle'),
      content: t('confirmRestartSubtitleDesc'),
      okText: t('yes'),
      cancelText: t('no'),
      onOk: async () => {
        try {
          await cleanupSubtitleFiles()
          const newStatus = await getProcessingStatus()
          setStatus(newStatus)
          onStatusUpdate?.(newStatus)
          message.success(t('cleanupSuccess'))
        } catch (error) {
          message.error(error instanceof Error ? error.message : t('error'))
        }
      },
    })
  }

  const handleRestartDubbing = () => {
    confirm({
      title: t('confirmRestartDubbing'),
      content: t('confirmRestartDubbingDesc'),
      okText: t('yes'),
      cancelText: t('no'),
      onOk: async () => {
        try {
          await cleanupDubbingFiles()
          const newStatus = await getProcessingStatus()
          setStatus(newStatus)
          onStatusUpdate?.(newStatus)
          message.success(t('cleanupSuccess'))
        } catch (error) {
          message.error(error instanceof Error ? error.message : t('error'))
        }
      },
    })
  }

  const handleCleanupAll = () => {
    confirm({
      title: t('confirmCleanupAll') || '清理所有缓存',
      content: t('confirmCleanupAllDesc') || '这将删除所有处理中间文件（包括音频、字幕、日志等），仅保留原始视频。确定要重新开始吗？',
      okText: t('yes'),
      cancelText: t('no'),
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await cleanupAllFiles()
          const newStatus = await getProcessingStatus()
          setStatus(newStatus)
          onStatusUpdate?.(newStatus)
          message.success(t('cleanupAllSuccess') || '已清理所有缓存，可以重新开始处理')
        } catch (error) {
          message.error(error instanceof Error ? error.message : t('error'))
        }
      },
    })
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
    defaultStages: ProcessingStage[],
    showOutputFiles: boolean = true
  ) => {
    const stages = job?.stages || defaultStages
    const jobStatus = job?.status || 'pending'
    const progress = job?.progress || 0
    const isActive = job !== undefined

    return (
      <div className="processing-job-content">
        <div className="flex items-center justify-between mb-4">
          <span className={`status-tag ${
            jobStatus === 'completed' ? 'status-tag-success' :
            jobStatus === 'running' ? 'status-tag-processing' :
            jobStatus === 'failed' ? 'status-tag-error' :
            'status-tag-default'
          }`}>
            {isActive ? t(jobStatus) : t('pending')}
          </span>
          <Text className="text-slate-500 text-sm">{Math.round(progress)}%</Text>
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
          showInfo={false}
        />

        <div className="mt-4 overflow-x-auto pb-2">
          <Steps
            size="small"
            className="modern-steps min-w-max"
            current={job ? job.stages.findIndex(s => s.status === 'running') : -1}
            items={stages.map((stage) => ({
              title: <span className="text-slate-600 text-xs">{stage.displayName}</span>,
              status: getStageStatus(stage),
              description: stage.status === 'running' 
                ? <div className="text-purple-500 text-xs mt-1 break-words max-w-[100px]">
                    {stage.message || (stage.progress ? `${Math.round(stage.progress)}%` : '处理中...')}
                  </div>
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

        {/* Show output files for completed stages */}
        {showOutputFiles && stages.some(s => s.status === 'completed') && (
          <StageOutputFiles stages={stages} />
        )}
      </div>
    )
  }

  // Tab items configuration
  const tabItems = [
    {
      key: 'subtitle',
      label: (
        <span className="flex items-center gap-2">
          <FileTextOutlined />
          {t('subtitleProcessing')}
          {subtitleCompleted && <CheckCircleOutlined className="text-green-500" />}
        </span>
      ),
      children: (
        <div className="p-4">
          {renderJobProgress(subtitleJob, DEFAULT_SUBTITLE_STAGES)}
          
          <div className="flex flex-wrap gap-3 mt-6 pt-4 border-t border-slate-200">
            {canStartSubtitle && !isProcessing && (
              <button
                className="btn-primary flex items-center gap-2"
                onClick={handleStartSubtitle}
              >
                <PlayCircleOutlined />
                {t('startSubtitle')}
              </button>
            )}
            
            {isSubtitleProcessing && (
              <button
                className="btn-danger flex items-center gap-2"
                onClick={handleCancel}
              >
                <PauseOutlined />
                {t('cancel')}
              </button>
            )}

            {subtitleCompleted && !isProcessing && (
              <button
                className="btn-warning flex items-center gap-2"
                onClick={handleRestartSubtitle}
              >
                <ReloadOutlined />
                {t('restartSubtitle')}
              </button>
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'proofread',
      label: (
        <span className="flex items-center gap-2">
          <MergeCellsOutlined />
          {t('proofreadAndMerge') || '校对与合并'}
        </span>
      ),
      children: (
        <div className="p-4">
          {/* Status and progress header - matching subtitle tab style */}
          <div className="processing-job-content">
            <div className="flex items-center justify-between mb-4">
              <span className={`status-tag ${
                subtitleMerged ? 'status-tag-success' :
                subtitleCompleted ? 'status-tag-success' : 'status-tag-default'
              }`}>
                {subtitleMerged ? t('completed') || '已完成' :
                 subtitleCompleted ? t('ready') || '就绪' : t('pending')}
              </span>
              <Text className="text-slate-500 text-sm">
                {subtitleMerged ? '100%' : subtitleCompleted ? '66%' : '0%'}
              </Text>
            </div>
            
            <Progress 
              percent={subtitleMerged ? 100 : subtitleCompleted ? 66 : 0} 
              status={subtitleMerged ? 'success' : subtitleCompleted ? 'active' : 'normal'}
              strokeColor={{
                '0%': '#667eea',
                '100%': '#764ba2',
              }}
              trailColor="rgba(0,0,0,0.06)"
              showInfo={false}
            />

            {/* Steps indicator - matching subtitle tab style */}
            <div className="mt-4 overflow-x-auto pb-2">
              <Steps
                size="small"
                className="modern-steps min-w-max"
                current={subtitleMerged ? 3 : subtitleCompleted ? 2 : -1}
                items={[
                  {
                    title: <span className="text-slate-600 text-xs">{t('proofreadStep1Title') || '校对字幕'}</span>,
                    status: subtitleCompleted ? 'finish' : 'wait',
                    description: subtitleCompleted 
                      ? <span className="text-green-500 text-xs">✓</span>
                      : null,
                  },
                  {
                    title: <span className="text-slate-600 text-xs">{t('proofreadStep2Title') || '下载字幕'}</span>,
                    status: subtitleCompleted ? 'finish' : 'wait',
                    description: subtitleCompleted 
                      ? <span className="text-green-500 text-xs">✓</span>
                      : null,
                  },
                  {
                    title: <span className="text-slate-600 text-xs">{t('proofreadMergeTip') || '合并到视频'}</span>,
                    status: subtitleMerged ? 'finish' : 'wait',
                    description: subtitleMerged 
                      ? <span className="text-green-500 text-xs">✓</span>
                      : null,
                  },
                ]}
              />
            </div>

            {/* Warning message if subtitle not completed */}
            {!subtitleCompleted && (
              <div className="mt-4 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-700 text-sm flex items-center gap-2">
                <span>⚠️</span>
                <span>{t('proofreadRequiresSubtitle') || '需要先完成字幕处理'}</span>
              </div>
            )}

            {/* Success message if subtitle merged */}
            {subtitleMerged && (
              <div className="mt-4 p-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm flex items-center gap-2">
                <span>✅</span>
                <span>{t('subtitleMergedSuccess') || '字幕已成功合并到视频中'}</span>
              </div>
            )}

            {/* Info tip - only show when subtitle completed but not yet merged */}
            {subtitleCompleted && !subtitleMerged && (
              <div className="mt-4 p-3 rounded-lg bg-blue-50 border border-blue-100 text-blue-700 text-sm flex items-center gap-2">
                <span>💡</span>
                <span>{t('proofreadMergeTipDesc') || '在字幕编辑器中点击"合并到视频"按钮，即可将字幕烧录到视频中'}</span>
              </div>
            )}
          </div>
          
          {/* Action buttons - matching subtitle tab style */}
          <div className="flex flex-wrap gap-3 mt-6 pt-4 border-t border-slate-200">
            <Link
              to="/editor"
              className={`inline-flex items-center gap-2 ${subtitleCompleted ? 'btn-primary' : 'btn-disabled opacity-50 cursor-not-allowed pointer-events-none'}`}
            >
              <EditOutlined />
              {t('enterEditor') || '进入字幕编辑器'}
            </Link>
            
            <a
              className={`inline-flex items-center gap-2 ${subtitleCompleted ? 'btn-secondary' : 'btn-disabled opacity-50 cursor-not-allowed pointer-events-none'}`}
              href={subtitleCompleted ? getSrtDownloadUrl() : undefined}
            >
              <DownloadOutlined />
              {t('download_srt') || '下载 SRT'}
            </a>
          </div>
        </div>
      ),
    },
    {
      key: 'dubbing',
      label: (
        <span className="flex items-center gap-2">
          <SoundOutlined />
          {t('dubbingProcessing')}
          {dubbingJob?.status === 'completed' && <CheckCircleOutlined className="text-green-500" />}
        </span>
      ),
      // Tab is always accessible
      children: (
        <div className="p-4">
          {/* Show warning if subtitle not completed */}
          {!subtitleCompleted && !dubbingJob && (
            <div className="mb-4 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-700 text-sm flex items-center gap-2">
              <span>⚠️</span>
              <span>{t('dubbingRequiresSubtitle')}</span>
            </div>
          )}
          
          {/* Always show progress stages */}
          {renderJobProgress(dubbingJob, DEFAULT_DUBBING_STAGES)}
          
          <div className="flex flex-wrap gap-3 mt-6 pt-4 border-t border-slate-200">
            {/* Show start button - disabled if subtitle not completed */}
            {!isProcessing && !dubbingJob?.status && (
              <button
                className={`flex items-center gap-2 ${canStartDubbing ? 'btn-primary' : 'btn-disabled opacity-50 cursor-not-allowed'}`}
                onClick={canStartDubbing ? handleStartDubbing : undefined}
                disabled={!canStartDubbing}
                title={!canStartDubbing ? t('dubbingRequiresSubtitle') : ''}
              >
                <PlayCircleOutlined />
                {t('startDubbing')}
              </button>
            )}
            
            {/* Active dubbing button when can start and no job yet */}
            {canStartDubbing && !isProcessing && dubbingJob?.status === 'failed' && (
              <button
                className="btn-primary flex items-center gap-2"
                onClick={handleStartDubbing}
              >
                <PlayCircleOutlined />
                {t('startDubbing')}
              </button>
            )}
            
            {isDubbingProcessing && (
              <button
                className="btn-danger flex items-center gap-2"
                onClick={handleCancel}
              >
                <PauseOutlined />
                {t('cancel')}
              </button>
            )}

            {dubbingJob?.status === 'completed' && !isProcessing && (
              <button
                className="btn-warning flex items-center gap-2"
                onClick={handleRestartDubbing}
              >
                <ReloadOutlined />
                {t('restartDubbing')}
              </button>
            )}
          </div>
        </div>
      ),
    },
  ]

  return (
    <div className="processing-panel">
      <Tabs
        defaultActiveKey="subtitle"
        items={tabItems}
        className="processing-tabs"
        type="card"
        tabBarExtraContent={
          !isProcessing && (
            <button
              className="btn-danger flex items-center gap-2 text-sm"
              onClick={handleCleanupAll}
              title={t('cleanupAllTooltip') || '清理所有缓存并重新开始'}
            >
              <DeleteOutlined />
              {t('cleanupAll') || '清理缓存'}
            </button>
          )
        }
      />
    </div>
  )
}
