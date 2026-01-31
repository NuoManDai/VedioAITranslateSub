/**
 * Subtitle Style Modal Component
 * 字幕样式设置弹窗 - 在字幕编辑器中配置字幕的字体大小、颜色等样式
 */
import { useEffect, useState } from 'react'
import { Modal, Form, InputNumber, Typography, Button, message, Spin, Input, Space } from 'antd'
import { useTranslation } from 'react-i18next'
import { getConfig, updateConfig } from '../../services/api'

const { Text } = Typography

interface SubtitleStyleConfig {
  translation: {
    fontSize: number
    fontColor: string
  }
  original: {
    fontSize: number
    fontColor: string
  }
  layout: {
    marginBottom: number
    lineSpacing: number
  }
}

interface SubtitleStyleModalProps {
  open: boolean
  onClose: () => void
  onStyleChange?: (style: SubtitleStyleConfig) => void
}

const DEFAULT_STYLE: SubtitleStyleConfig = {
  translation: { fontSize: 18, fontColor: '#FFFFFF' },
  original: { fontSize: 14, fontColor: '#CCCCCC' },
  layout: { marginBottom: 40, lineSpacing: 8 },
}

export default function SubtitleStyleModal({ open, onClose, onStyleChange }: SubtitleStyleModalProps) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  // Load current config when modal opens
  useEffect(() => {
    if (open) {
      loadStyleConfig()
    }
  }, [open])

  const loadStyleConfig = async () => {
    try {
      setLoading(true)
      const config = await getConfig()
      const styleConfig = config.subtitle?.style
      
      form.setFieldsValue({
        translationFontSize: styleConfig?.translation?.fontSize || DEFAULT_STYLE.translation.fontSize,
        translationFontColor: styleConfig?.translation?.fontColor || DEFAULT_STYLE.translation.fontColor,
        originalFontSize: styleConfig?.original?.fontSize || DEFAULT_STYLE.original.fontSize,
        originalFontColor: styleConfig?.original?.fontColor || DEFAULT_STYLE.original.fontColor,
        marginBottom: styleConfig?.layout?.marginBottom || DEFAULT_STYLE.layout.marginBottom,
        lineSpacing: styleConfig?.layout?.lineSpacing || DEFAULT_STYLE.layout.lineSpacing,
      })
    } catch (error) {
      console.error('Failed to load style config:', error)
      // Use defaults on error
      form.setFieldsValue({
        translationFontSize: DEFAULT_STYLE.translation.fontSize,
        translationFontColor: DEFAULT_STYLE.translation.fontColor,
        originalFontSize: DEFAULT_STYLE.original.fontSize,
        originalFontColor: DEFAULT_STYLE.original.fontColor,
        marginBottom: DEFAULT_STYLE.layout.marginBottom,
        lineSpacing: DEFAULT_STYLE.layout.lineSpacing,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)

      // Build the style config to save
      const styleToSave = {
        subtitle: {
          style: {
            translation: {
              font_size: values.translationFontSize,
              font_color: values.translationFontColor,
              bg_color: 'rgba(0,0,0,0.75)',
              outline_color: '#000000',
              outline_width: 1,
            },
            original: {
              font_size: values.originalFontSize,
              font_color: values.originalFontColor,
              bg_color: 'rgba(0,0,0,0.6)',
              outline_color: '#000000',
              outline_width: 1,
            },
            layout: {
              margin_bottom: values.marginBottom,
              line_spacing: values.lineSpacing,
            },
          },
        },
      }

      await updateConfig(styleToSave)
      
      // Notify parent of style change for preview update
      if (onStyleChange) {
        onStyleChange({
          translation: {
            fontSize: values.translationFontSize,
            fontColor: values.translationFontColor,
          },
          original: {
            fontSize: values.originalFontSize,
            fontColor: values.originalFontColor,
          },
          layout: {
            marginBottom: values.marginBottom,
            lineSpacing: values.lineSpacing,
          },
        })
      }

      message.success(t('success') || '保存成功')
      onClose()
    } catch (error) {
      console.error('Failed to save style config:', error)
      message.error(t('error') || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title={t('subtitleStyleSettings') || '字幕样式设置'}
      open={open}
      onCancel={onClose}
      width={480}
      footer={[
        <Button key="cancel" onClick={onClose}>
          {t('cancel') || '取消'}
        </Button>,
        <Button key="save" type="primary" loading={saving} onClick={handleSave}>
          {t('saveSettings') || '保存设置'}
        </Button>,
      ]}
    >
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Spin />
        </div>
      ) : (
        <Form form={form} layout="vertical" className="mt-4">
          {/* Translation Subtitle Settings */}
          <div className="border-l-2 border-indigo-400 pl-4 mb-4">
            <Text strong className="text-indigo-600 mb-2 block">
              {t('translationStyle') || '译文样式'}
            </Text>
            <div className="grid grid-cols-2 gap-4">
              <Form.Item 
                name="translationFontSize"
                label={t('fontSize') || '字体大小'}
              >
                <InputNumber 
                  min={10} 
                  max={40} 
                  addonAfter="px"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item 
                name="translationFontColor"
                label={t('fontColor') || '字体颜色'}
              >
                <Input
                  type="color"
                  style={{ width: 80, height: 32, padding: 2, cursor: 'pointer' }}
                />
              </Form.Item>
            </div>
          </div>

          {/* Original Subtitle Settings */}
          <div className="border-l-2 border-gray-400 pl-4 mb-4">
            <Text strong className="text-gray-600 mb-2 block">
              {t('originalStyle') || '原文样式'}
            </Text>
            <div className="grid grid-cols-2 gap-4">
              <Form.Item 
                name="originalFontSize"
                label={t('fontSize') || '字体大小'}
              >
                <InputNumber 
                  min={8} 
                  max={30} 
                  addonAfter="px"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item 
                name="originalFontColor"
                label={t('fontColor') || '字体颜色'}
              >
                <Input
                  type="color"
                  style={{ width: 80, height: 32, padding: 2, cursor: 'pointer' }}
                />
              </Form.Item>
            </div>
          </div>

          {/* Layout Settings */}
          <div className="border-l-2 border-green-400 pl-4">
            <Text strong className="text-green-600 mb-2 block">
              {t('layoutStyle') || '布局设置'}
            </Text>
            <div className="grid grid-cols-2 gap-4">
              <Form.Item 
                name="marginBottom"
                label={t('marginBottom') || '底部边距'}
                tooltip={t('marginBottomTooltip') || '字幕距离视频底部的距离'}
              >
                <InputNumber 
                  min={10} 
                  max={100} 
                  addonAfter="px"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item 
                name="lineSpacing"
                label={t('lineSpacing') || '行间距'}
                tooltip={t('lineSpacingTooltip') || '译文和原文之间的间距'}
              >
                <InputNumber 
                  min={0} 
                  max={30} 
                  addonAfter="px"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </div>
          </div>
        </Form>
      )}
    </Modal>
  )
}
