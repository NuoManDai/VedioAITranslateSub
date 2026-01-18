/**
 * Stage Output Files Component - Shows output files for each processing stage
 */
import { useState, useEffect } from 'react'
import { Button, Modal, Spin, Collapse, Tooltip, message, Empty } from 'antd'
import { 
  FileTextOutlined, 
  FileExcelOutlined, 
  VideoCameraOutlined,
  AudioOutlined,
  FolderOutlined,
  EyeOutlined,
  DownloadOutlined,
  ReloadOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { 
  getStageFiles, 
  previewFile, 
  getFileDownloadUrl, 
  listFolder,
  type StageOutputFile,
  type FilePreviewResponse,
  type FolderFile
} from '../services/api'

interface StageOutputFilesProps {
  stages: Array<{
    name: string
    displayName: string
    status: string
  }>
}

const fileTypeIcons: Record<string, React.ReactNode> = {
  xlsx: <FileExcelOutlined className="text-green-600" />,
  txt: <FileTextOutlined className="text-blue-600" />,
  json: <FileTextOutlined className="text-yellow-600" />,
  srt: <FileTextOutlined className="text-purple-600" />,
  mp4: <VideoCameraOutlined className="text-red-600" />,
  mp3: <AudioOutlined className="text-orange-600" />,
  folder: <FolderOutlined className="text-amber-600" />,
}

function formatFileSize(bytes: number | null): string {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function FileIcon({ type }: { type: string }) {
  return fileTypeIcons[type] || <FileTextOutlined className="text-gray-500" />
}

// JSON 语法高亮渲染组件
function JsonHighlight({ content }: { content: string }) {
  // 简单的 JSON 语法高亮
  const highlightJson = (json: string): React.ReactNode[] => {
    const lines = json.split('\n')
    return lines.map((line, i) => {
      // 高亮处理
      const highlighted = line
        // 字符串键
        .replace(/"([^"]+)":/g, '<span class="text-purple-600">"$1"</span>:')
        // 字符串值
        .replace(/: "([^"]*)"/g, ': <span class="text-green-600">"$1"</span>')
        // 数字
        .replace(/: (\d+\.?\d*)/g, ': <span class="text-blue-600">$1</span>')
        // 布尔和 null
        .replace(/: (true|false|null)/g, ': <span class="text-orange-600">$1</span>')
      
      return (
        <div key={i} className="hover:bg-gray-100" dangerouslySetInnerHTML={{ __html: highlighted }} />
      )
    })
  }

  return (
    <div className="font-mono text-xs leading-relaxed">
      {highlightJson(content)}
    </div>
  )
}

function PreviewModal({ 
  visible, 
  onClose, 
  filePath 
}: { 
  visible: boolean
  onClose: () => void
  filePath: string | null
}) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState<FilePreviewResponse | null>(null)

  useEffect(() => {
    if (visible && filePath) {
      setLoading(true)
      previewFile(filePath)
        .then(setPreview)
        .catch(err => {
          message.error(err.message || t('error'))
          setPreview(null)
        })
        .finally(() => setLoading(false))
    } else {
      setPreview(null)
    }
  }, [visible, filePath, t])

  // 根据文件类型渲染内容
  const renderContent = () => {
    if (!preview?.content) return null
    
    if (preview.type === 'json') {
      return (
        <div className="bg-gray-50 p-4 rounded-lg overflow-auto max-h-[60vh]">
          <JsonHighlight content={preview.content} />
        </div>
      )
    }
    
    // xlsx 使用 markdown 表格样式
    if (preview.type === 'xlsx') {
      return (
        <div className="bg-gray-50 p-4 rounded-lg overflow-auto max-h-[60vh]">
          <pre className="text-xs font-mono whitespace-pre">{preview.content}</pre>
        </div>
      )
    }
    
    // txt, srt 等文本文件
    return (
      <pre className="bg-gray-50 p-4 rounded-lg overflow-auto max-h-[60vh] text-sm whitespace-pre-wrap break-words">
        {preview.content}
      </pre>
    )
  }

  return (
    <Modal
      title={preview?.name || t('preview')}
      open={visible}
      onCancel={onClose}
      width={900}
      footer={[
        <Button key="close" onClick={onClose}>{t('close')}</Button>,
        preview && (
          <Button 
            key="download" 
            type="primary" 
            icon={<DownloadOutlined />}
            href={getFileDownloadUrl(preview.path)}
          >
            {t('download')}
          </Button>
        )
      ].filter(Boolean)}
    >
      {loading ? (
        <div className="flex justify-center py-8">
          <Spin size="large" />
        </div>
      ) : preview?.previewAvailable ? (
        renderContent()
      ) : preview?.error ? (
        <div className="text-red-500 p-4 bg-red-50 rounded-lg">
          {preview.error}
        </div>
      ) : (
        <Empty description={t('previewNotAvailable')} />
      )}
    </Modal>
  )
}

function FolderModal({
  visible,
  onClose,
  folderPath,
  onPreviewFile
}: {
  visible: boolean
  onClose: () => void
  folderPath: string | null
  onPreviewFile: (path: string) => void
}) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [files, setFiles] = useState<FolderFile[]>([])
  const [currentPath, setCurrentPath] = useState<string>('')

  useEffect(() => {
    if (visible && folderPath) {
      setCurrentPath(folderPath)
      loadFolder(folderPath)
    }
  }, [visible, folderPath])

  const loadFolder = async (path: string) => {
    setLoading(true)
    try {
      const result = await listFolder(path)
      setFiles(result.files)
      setCurrentPath(path)
    } catch (err) {
      message.error(err instanceof Error ? err.message : t('error'))
    } finally {
      setLoading(false)
    }
  }

  const handleFileClick = (file: FolderFile) => {
    if (file.isDir) {
      loadFolder(file.path)
    } else {
      onPreviewFile(file.path)
    }
  }

  return (
    <Modal
      title={
        <div className="flex items-center gap-2">
          <FolderOutlined />
          <span>{currentPath}</span>
        </div>
      }
      open={visible}
      onCancel={onClose}
      width={600}
      footer={[
        <Button key="close" onClick={onClose}>{t('close')}</Button>
      ]}
    >
      {loading ? (
        <div className="flex justify-center py-8">
          <Spin size="large" />
        </div>
      ) : files.length === 0 ? (
        <Empty description={t('emptyFolder')} />
      ) : (
        <div className="max-h-[50vh] overflow-auto">
          {files.map(file => (
            <div
              key={file.path}
              className="flex items-center justify-between p-2 hover:bg-gray-50 rounded cursor-pointer border-b border-gray-100"
              onClick={() => handleFileClick(file)}
            >
              <div className="flex items-center gap-2">
                <FileIcon type={file.type} />
                <span className={file.isDir ? 'font-medium' : ''}>{file.name}</span>
              </div>
              <div className="flex items-center gap-4 text-gray-500 text-sm">
                <span>{formatFileSize(file.size)}</span>
                {!file.isDir && (
                  <Button 
                    size="small" 
                    icon={<DownloadOutlined />}
                    href={getFileDownloadUrl(file.path)}
                    onClick={e => e.stopPropagation()}
                  />
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Modal>
  )
}

function StageFileList({ 
  stageName,
  onPreviewFile,
  onOpenFolder
}: { 
  stageName: string
  onPreviewFile: (path: string) => void
  onOpenFolder: (path: string) => void
}) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [files, setFiles] = useState<StageOutputFile[]>([])
  const [loaded, setLoaded] = useState(false)

  const loadFiles = async () => {
    setLoading(true)
    try {
      const result = await getStageFiles(stageName)
      setFiles(result.files)
      setLoaded(true)
    } catch (err) {
      message.error(err instanceof Error ? err.message : t('error'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // Auto-load when component mounts
    loadFiles()
  }, [stageName])

  const existingFiles = files.filter(f => f.exists)

  if (loading && !loaded) {
    return (
      <div className="flex justify-center py-4">
        <Spin size="small" />
      </div>
    )
  }

  if (existingFiles.length === 0) {
    return (
      <div className="text-gray-400 text-sm py-2 px-4">
        {t('noOutputFiles')}
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {existingFiles.map(file => (
        <div 
          key={file.path}
          className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded hover:bg-gray-100"
        >
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <FileIcon type={file.type} />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{file.name}</div>
              <div className="text-xs text-gray-500 truncate">{file.description}</div>
            </div>
          </div>
          
          <div className="flex items-center gap-2 ml-2">
            <span className="text-xs text-gray-400">
              {formatFileSize(file.size)}
            </span>
            
            {file.type === 'folder' ? (
              <Tooltip title={t('openFolder')}>
                <Button 
                  size="small" 
                  icon={<FolderOutlined />}
                  onClick={() => onOpenFolder(file.path)}
                />
              </Tooltip>
            ) : file.type === 'mp4' || file.type === 'mp3' ? (
              <Tooltip title={t('download')}>
                <Button 
                  size="small" 
                  icon={<DownloadOutlined />}
                  href={getFileDownloadUrl(file.path)}
                />
              </Tooltip>
            ) : (
              <>
                <Tooltip title={t('preview')}>
                  <Button 
                    size="small" 
                    icon={<EyeOutlined />}
                    onClick={() => onPreviewFile(file.path)}
                  />
                </Tooltip>
                <Tooltip title={t('download')}>
                  <Button 
                    size="small" 
                    icon={<DownloadOutlined />}
                    href={getFileDownloadUrl(file.path)}
                  />
                </Tooltip>
              </>
            )}
          </div>
        </div>
      ))}
      
      <div className="flex justify-end pt-2">
        <Button 
          size="small" 
          icon={<ReloadOutlined />} 
          onClick={loadFiles}
          loading={loading}
        >
          {t('refresh')}
        </Button>
      </div>
    </div>
  )
}

export default function StageOutputFiles({ stages }: StageOutputFilesProps) {
  const { t } = useTranslation()
  const [previewFile, setPreviewFile] = useState<string | null>(null)
  const [folderPath, setFolderPath] = useState<string | null>(null)

  // Only show completed stages
  const completedStages = stages.filter(s => s.status === 'completed')

  if (completedStages.length === 0) {
    return null
  }

  const collapseItems = completedStages.map(stage => ({
    key: stage.name,
    label: (
      <span className="flex items-center gap-2">
        <span>{stage.displayName}</span>
        <span className="text-green-500 text-xs">✓</span>
      </span>
    ),
    children: (
      <StageFileList 
        stageName={stage.name}
        onPreviewFile={setPreviewFile}
        onOpenFolder={setFolderPath}
      />
    ),
  }))

  return (
    <div className="stage-output-files mt-4">
      <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
        <FileTextOutlined />
        {t('outputFiles')}
      </h4>
      
      <Collapse 
        items={collapseItems}
        size="small"
        className="bg-white"
      />

      <PreviewModal 
        visible={!!previewFile}
        onClose={() => setPreviewFile(null)}
        filePath={previewFile}
      />

      <FolderModal
        visible={!!folderPath}
        onClose={() => setFolderPath(null)}
        folderPath={folderPath}
        onPreviewFile={(path) => {
          setFolderPath(null)
          setPreviewFile(path)
        }}
      />
    </div>
  )
}
