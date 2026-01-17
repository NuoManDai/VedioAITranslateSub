/**
 * YouTube Download Component
 */
import { useState } from 'react'
import { message, Progress } from 'antd'
import { DownloadOutlined, YoutubeOutlined, SettingOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { Video } from '../types'
import { downloadYouTube } from '../services/api'

interface YouTubeDownloadProps {
  onSuccess: (video: Video) => void
}

const resolutionOptions = [
  { value: '360', label: '360p (快速)' },
  { value: '1080', label: '1080p (高清)' },
  { value: 'best', label: '最佳质量' },
]

export default function YouTubeDownload({ onSuccess }: YouTubeDownloadProps) {
  const { t } = useTranslation()
  const [url, setUrl] = useState('')
  const [resolution, setResolution] = useState<'360' | '1080' | 'best'>('1080')
  const [downloading, setDownloading] = useState(false)

  const handleDownload = async () => {
    if (!url.trim()) {
      message.warning(t('enterYoutubeUrl'))
      return
    }

    try {
      setDownloading(true)
      
      const video = await downloadYouTube({
        url: url.trim(),
        resolution,
      })
      
      message.success(t('success'))
      onSuccess(video)
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('error'))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-300 mb-3">
          <YoutubeOutlined className="text-red-500" />
          {t('enterYoutubeUrl')}
        </label>
        <input
          type="text"
          className="modern-input"
          placeholder="https://www.youtube.com/watch?v=..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={downloading}
        />
      </div>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-300 mb-3">
          <SettingOutlined className="text-purple-400" />
          {t('Resolution')}
        </label>
        <select
          className="modern-select"
          value={resolution}
          onChange={(e) => setResolution(e.target.value as '360' | '1080' | 'best')}
          disabled={downloading}
        >
          {resolutionOptions.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <button
        className={`btn-primary w-full flex items-center justify-center gap-2 ${downloading ? 'opacity-70 cursor-wait' : ''}`}
        onClick={handleDownload}
        disabled={downloading}
      >
        {downloading ? (
          <>
            <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            {t('downloading')}
          </>
        ) : (
          <>
            <DownloadOutlined />
            {t('download')}
          </>
        )}
      </button>

      {downloading && (
        <div className="download-progress p-4 rounded-xl bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-white/10">
          <Progress 
            percent={0} 
            status="active" 
            showInfo={false}
            strokeColor={{
              '0%': '#667eea',
              '100%': '#764ba2',
            }}
            trailColor="rgba(255,255,255,0.1)"
          />
          <p className="text-center text-gray-400 mt-3 flex items-center justify-center gap-2">
            <span className="inline-block w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
            {t('downloading')}
          </p>
        </div>
      )}
    </div>
  )
}
