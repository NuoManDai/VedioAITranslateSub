/**
 * BatchUploader - Drag & drop file/folder upload for batch processing
 */
import { useState, useCallback } from 'react'
import { Progress, message } from 'antd'
import { CloudUploadOutlined, FolderOpenOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

const ALLOWED_EXTENSIONS = new Set(['.mp4', '.avi', '.mkv', '.mov', '.webm', '.m4v'])

interface BatchUploaderProps {
  onFilesSelected: (files: File[]) => void
  uploading?: boolean
  uploadProgress?: Record<string, number>
}

function getFileExtension(filename: string): string {
  const idx = filename.lastIndexOf('.')
  return idx >= 0 ? filename.slice(idx).toLowerCase() : ''
}

function filterVideoFiles(files: File[]): File[] {
  return files.filter((f) => ALLOWED_EXTENSIONS.has(getFileExtension(f.name)))
}

/**
 * Recursively collect files from DataTransferItem (folder support)
 */
async function collectFilesFromEntries(items: DataTransferItemList): Promise<File[]> {
  const files: File[] = []

  async function readEntry(entry: FileSystemEntry): Promise<void> {
    if (entry.isFile) {
      const fileEntry = entry as FileSystemFileEntry
      const file = await new Promise<File>((resolve, reject) => {
        fileEntry.file(resolve, reject)
      })
      if (ALLOWED_EXTENSIONS.has(getFileExtension(file.name))) {
        files.push(file)
      }
    } else if (entry.isDirectory) {
      const dirEntry = entry as FileSystemDirectoryEntry
      const reader = dirEntry.createReader()
      const entries = await new Promise<FileSystemEntry[]>((resolve, reject) => {
        reader.readEntries(resolve, reject)
      })
      for (const childEntry of entries) {
        await readEntry(childEntry)
      }
    }
  }

  const entries: FileSystemEntry[] = []
  for (let i = 0; i < items.length; i++) {
    const entry = items[i].webkitGetAsEntry?.()
    if (entry) {
      entries.push(entry)
    }
  }

  for (const entry of entries) {
    await readEntry(entry)
  }

  return files
}

export default function BatchUploader({
  onFilesSelected,
  uploading = false,
  uploadProgress = {},
}: BatchUploaderProps) {
  const { t } = useTranslation()
  const [dragActive, setDragActive] = useState(false)

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault()
      setDragActive(false)
      if (uploading) return

      let files: File[] = []

      // Try webkitGetAsEntry for folder support
      if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
        const supportsEntries = typeof e.dataTransfer.items[0].webkitGetAsEntry === 'function'
        if (supportsEntries) {
          files = await collectFilesFromEntries(e.dataTransfer.items)
        }
      }

      // Fallback to regular files
      if (files.length === 0 && e.dataTransfer.files.length > 0) {
        files = filterVideoFiles(Array.from(e.dataTransfer.files))
      }

      if (files.length === 0) {
        message.warning(t('noVideoFiles', '未找到支持的视频文件'))
        return
      }

      onFilesSelected(files)
    },
    [uploading, onFilesSelected, t]
  )

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      if (!uploading) {
        setDragActive(true)
      }
    },
    [uploading]
  )

  const handleDragLeave = useCallback(() => {
    setDragActive(false)
  }, [])

  const handleClickFiles = useCallback(() => {
    if (uploading) return
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'video/*,.mp4,.avi,.mkv,.mov,.webm,.m4v'
    input.multiple = true
    input.onchange = (e) => {
      const fileList = (e.target as HTMLInputElement).files
      if (fileList && fileList.length > 0) {
        const videoFiles = filterVideoFiles(Array.from(fileList))
        if (videoFiles.length > 0) {
          onFilesSelected(videoFiles)
        } else {
          message.warning(t('noVideoFiles', '未找到支持的视频文件'))
        }
      }
    }
    input.click()
  }, [uploading, onFilesSelected, t])

  const handleClickFolder = useCallback(() => {
    if (uploading) return
    const input = document.createElement('input')
    input.type = 'file'
    input.setAttribute('webkitdirectory', '')
    input.setAttribute('directory', '')
    input.multiple = true
    input.onchange = (e) => {
      const fileList = (e.target as HTMLInputElement).files
      if (fileList && fileList.length > 0) {
        const videoFiles = filterVideoFiles(Array.from(fileList))
        if (videoFiles.length > 0) {
          onFilesSelected(videoFiles)
        } else {
          message.warning(t('noVideoFiles', '未找到支持的视频文件'))
        }
      }
    }
    input.click()
  }, [uploading, onFilesSelected, t])

  // Calculate overall progress
  const progressValues = Object.values(uploadProgress)
  const overallProgress =
    progressValues.length > 0
      ? Math.round(
          progressValues.reduce((a, b) => a + b, 0) / progressValues.length
        )
      : 0

  return (
    <div className="space-y-4">
      <div
        className={`upload-area ${dragActive ? 'upload-area-active' : ''} ${uploading ? 'pointer-events-none opacity-50' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <div className="upload-icon">
          <CloudUploadOutlined style={{ fontSize: 48 }} />
        </div>
        <p className="upload-text">
          {t('batchDragHint', '拖拽文件或文件夹到此处')}
        </p>
        <p className="upload-hint">
          {t('supportedFormats', '支持 MP4、AVI、MKV、MOV、WebM 格式')}
        </p>
        <div className="flex gap-3 justify-center mt-4">
          <button
            className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-sm text-gray-300 transition-colors flex items-center gap-2"
            onClick={handleClickFiles}
            disabled={uploading}
          >
            <CloudUploadOutlined />
            {t('selectFiles', '选择文件')}
          </button>
          <button
            className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-sm text-gray-300 transition-colors flex items-center gap-2"
            onClick={handleClickFolder}
            disabled={uploading}
          >
            <FolderOpenOutlined />
            {t('selectFolder', '选择文件夹')}
          </button>
        </div>
      </div>

      {uploading && (
        <div className="upload-progress">
          <Progress
            percent={overallProgress}
            status="active"
            strokeColor={{
              '0%': '#667eea',
              '100%': '#764ba2',
            }}
            trailColor="rgba(255,255,255,0.1)"
          />
          <p className="text-center text-gray-400 mt-3 flex items-center justify-center gap-2">
            <span className="inline-block w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
            {t('uploading', '上传中...')} ({progressValues.length} {t('files', '个文件')})
          </p>
        </div>
      )}
    </div>
  )
}
