/**
 * BatchFileList - Display uploaded files with inline settings
 */
import { Table, Select, Switch, Button, Tag, Popconfirm } from 'antd'
import { DeleteOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { ColumnsType } from 'antd/es/table'
import { SOURCE_LANGUAGES, TARGET_LANGUAGES } from '@/types'
import type { BatchFile, BatchFileSettingsUpdate } from '@/types/batch'

interface BatchFileListProps {
  files: BatchFile[]
  onSettingsChange: (fileId: string, settings: BatchFileSettingsUpdate) => void
  onDelete: (fileId: string) => void
  disabled?: boolean
}

export default function BatchFileList({
  files,
  onSettingsChange,
  onDelete,
  disabled = false,
}: BatchFileListProps) {
  const { t } = useTranslation()

  const getStatusColor = (status: BatchFile['status']) => {
    switch (status) {
      case 'pending':
      case 'uploading':
      case 'queued':
        return 'default'
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

  const columns: ColumnsType<BatchFile> = [
    {
      title: t('filename', '文件名'),
      dataIndex: 'filename',
      key: 'filename',
      ellipsis: true,
      width: 200,
    },
    {
      title: t('sourceLanguage', '源语言'),
      dataIndex: 'sourceLang',
      key: 'sourceLang',
      width: 150,
      render: (sourceLang: string, record: BatchFile) => (
        <Select
          value={sourceLang}
          onChange={(value) => onSettingsChange(record.id, { sourceLang: value })}
          disabled={disabled}
          style={{ width: '100%' }}
          options={SOURCE_LANGUAGES.map((lang) => ({
            value: lang.value,
            label: lang.label,
          }))}
        />
      ),
    },
    {
      title: t('targetLanguage', '目标语言'),
      dataIndex: 'targetLang',
      key: 'targetLang',
      width: 180,
      render: (targetLang: string, record: BatchFile) => (
        <Select
          value={targetLang}
          onChange={(value) => onSettingsChange(record.id, { targetLang: value })}
          disabled={disabled}
          style={{ width: '100%' }}
          options={TARGET_LANGUAGES.map((lang) => ({
            value: lang.value,
            label: lang.label,
          }))}
        />
      ),
    },
    {
      title: t('dubbing', '配音'),
      dataIndex: 'dubbing',
      key: 'dubbing',
      width: 80,
      render: (dubbing: boolean, record: BatchFile) => (
        <Switch
          checked={dubbing}
          onChange={(checked) => onSettingsChange(record.id, { dubbing: checked })}
          disabled={disabled}
        />
      ),
    },
    {
      title: t('status', '状态'),
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: BatchFile['status']) => (
        <Tag color={getStatusColor(status)}>
          {t(`batchStatus.${status}`, status)}
        </Tag>
      ),
    },
    {
      title: t('actions', '操作'),
      key: 'actions',
      width: 80,
      fixed: 'right',
      render: (_: unknown, record: BatchFile) => (
        <Popconfirm
          title={t('confirmDelete', '确认删除？')}
          onConfirm={() => onDelete(record.id)}
          disabled={disabled}
          okText={t('yes', '是')}
          cancelText={t('no', '否')}
        >
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            disabled={disabled}
          />
        </Popconfirm>
      ),
    },
  ]

  return (
    <Table
      columns={columns}
      dataSource={files}
      rowKey="id"
      pagination={false}
      scroll={{ x: 900 }}
      locale={{
        emptyText: t('noFilesYet', '暂无文件，请先上传视频文件'),
      }}
    />
  )
}
