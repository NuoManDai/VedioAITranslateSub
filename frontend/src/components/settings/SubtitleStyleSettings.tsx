/**
 * Subtitle Style Settings Component
 * 字幕样式设置组件 - 配置字幕的字体大小、颜色等样式
 */
import { Form, InputNumber, Collapse, Space, Typography, Tooltip } from 'antd'
import { useTranslation } from 'react-i18next'
import { QuestionCircleOutlined, BgColorsOutlined } from '@ant-design/icons'

const { Text } = Typography

export default function SubtitleStyleSettings() {
  const { t } = useTranslation()

  return (
    <Collapse 
      ghost
      items={[
        {
          key: 'subtitleStyle',
          label: (
            <Space>
              <BgColorsOutlined />
              <span>{t('subtitleStyleSettings') || '字幕样式设置'}</span>
              <Tooltip title={t('subtitleStyleTooltip') || '配置字幕的字体大小、颜色和布局。这些设置会影响预览和最终烧录到视频中的字幕样式。'}>
                <QuestionCircleOutlined style={{ color: '#999' }} />
              </Tooltip>
            </Space>
          ),
          children: (
            <div className="space-y-4 pt-2">
              {/* Translation Subtitle Settings */}
              <div className="border-l-2 border-indigo-400 pl-4">
                <Text strong className="text-indigo-600 mb-2 block">
                  {t('translationStyle') || '译文样式'}
                </Text>
                <div className="grid grid-cols-2 gap-4">
                  <Form.Item 
                    name={['subtitleStyle', 'translation', 'fontSize']}
                    label={t('fontSize') || '字体大小'}
                    initialValue={18}
                  >
                    <InputNumber 
                      min={10} 
                      max={40} 
                      addonAfter="px"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                  <Form.Item 
                    name={['subtitleStyle', 'translation', 'fontColor']}
                    label={t('fontColor') || '字体颜色'}
                    initialValue="#FFFFFF"
                  >
                    <input 
                      type="color" 
                      className="w-full h-8 rounded border border-gray-300 cursor-pointer"
                    />
                  </Form.Item>
                </div>
              </div>

              {/* Original Subtitle Settings */}
              <div className="border-l-2 border-gray-400 pl-4">
                <Text strong className="text-gray-600 mb-2 block">
                  {t('originalStyle') || '原文样式'}
                </Text>
                <div className="grid grid-cols-2 gap-4">
                  <Form.Item 
                    name={['subtitleStyle', 'original', 'fontSize']}
                    label={t('fontSize') || '字体大小'}
                    initialValue={14}
                  >
                    <InputNumber 
                      min={8} 
                      max={30} 
                      addonAfter="px"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                  <Form.Item 
                    name={['subtitleStyle', 'original', 'fontColor']}
                    label={t('fontColor') || '字体颜色'}
                    initialValue="#CCCCCC"
                  >
                    <input 
                      type="color" 
                      className="w-full h-8 rounded border border-gray-300 cursor-pointer"
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
                    name={['subtitleStyle', 'layout', 'marginBottom']}
                    label={t('marginBottom') || '底部边距'}
                    initialValue={40}
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
                    name={['subtitleStyle', 'layout', 'lineSpacing']}
                    label={t('lineSpacing') || '行间距'}
                    initialValue={8}
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
            </div>
          ),
        },
      ]}
    />
  )
}
