/**
 * Settings Modal Component - Placeholder
 * Will be fully implemented in Phase 6 (US4)
 */
import { Modal, Form, Input, Select, Switch, Button, Tabs, message } from 'antd'
import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'
import { TTS_METHODS, WHISPER_METHODS, SOURCE_LANGUAGES, TARGET_LANGUAGES } from '../types'
import { getConfig, updateConfig, validateApiKey } from '../services/api'

interface SettingsModalProps {
  open: boolean
  onClose: () => void
}

export default function SettingsModal({ open, onClose }: SettingsModalProps) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)

  useEffect(() => {
    if (open) {
      loadConfig()
    }
  }, [open])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const config = await getConfig()
      form.setFieldsValue({
        apiKey: config.api?.key || '',
        baseUrl: config.api?.baseUrl || 'https://api.openai.com',
        model: config.api?.model || 'gpt-4o-mini',
        llmSupportJson: config.api?.llmSupportJson ?? false,
        targetLanguage: config.targetLanguage || '简体中文',
        sourceLanguage: config.sourceLanguage || 'en',
        demucs: config.demucs ?? false,
        burnSubtitles: config.burnSubtitles ?? true,
        ttsMethod: config.ttsMethod || 'edge_tts',
        whisperMethod: config.whisper?.method || 'whisperX_local',
        httpProxy: config.httpProxy || '',
        hfMirror: config.hfMirror || '',
      })
    } catch (error) {
      message.error(t('error'))
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)
      
      await updateConfig({
        api: {
          key: values.apiKey,
          baseUrl: values.baseUrl,
          model: values.model,
          llmSupportJson: values.llmSupportJson ?? false,
        },
        targetLanguage: values.targetLanguage,
        sourceLanguage: values.sourceLanguage,
        demucs: values.demucs,
        burnSubtitles: values.burnSubtitles,
        ttsMethod: values.ttsMethod,
        whisper: {
          method: values.whisperMethod,
          whisperXModel: 'large-v2',
        },
        httpProxy: values.httpProxy || '',
        hfMirror: values.hfMirror || '',
      })
      
      message.success(t('success'))
      onClose()
    } catch (error) {
      message.error(t('error'))
    } finally {
      setLoading(false)
    }
  }

  const handleTestApi = async () => {
    try {
      const values = form.getFieldsValue(['apiKey', 'baseUrl', 'model'])
      setValidating(true)
      
      const result = await validateApiKey({
        key: values.apiKey,
        baseUrl: values.baseUrl,
        model: values.model,
      })
      
      if (result.valid) {
        message.success(t('API Key is valid'))
      } else {
        message.error(result.message || t('API Key is invalid'))
      }
    } catch (error) {
      message.error(t('API Key is invalid'))
    } finally {
      setValidating(false)
    }
  }

  return (
    <Modal
      title={t('settings')}
      open={open}
      onCancel={onClose}
      width={600}
      footer={[
        <Button key="cancel" onClick={onClose}>
          {t('cancel')}
        </Button>,
        <Button key="save" type="primary" loading={loading} onClick={handleSave}>
          {t('saveSettings')}
        </Button>,
      ]}
    >
      <Form form={form} layout="vertical" className="mt-4">
        <Tabs
          items={[
            {
              key: 'llm',
              label: t('LLM Configuration'),
              children: (
                <>
                  <Form.Item
                    name="apiKey"
                    label={t('API_KEY')}
                    rules={[{ required: true }]}
                  >
                    <Input.Password placeholder="sk-..." />
                  </Form.Item>
                  <Form.Item
                    name="baseUrl"
                    label={t('BASE_URL')}
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="https://api.openai.com" />
                  </Form.Item>
                  <Form.Item
                    name="model"
                    label={t('MODEL')}
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="gpt-4o-mini" />
                  </Form.Item>
                  <Form.Item 
                    name="llmSupportJson" 
                    label={t('LLM JSON Mode')}
                    tooltip={t('llmJsonModeTooltip')}
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                  <Button loading={validating} onClick={handleTestApi}>
                    {t('testApi')}
                  </Button>
                </>
              ),
            },
            {
              key: 'subtitle',
              label: t('Subtitles Settings'),
              children: (
                <>
                  <Form.Item name="sourceLanguage" label={t('Recog Lang')}>
                    <Select 
                      options={SOURCE_LANGUAGES.map(l => ({ value: l.value, label: l.label }))}
                      showSearch
                      filterOption={(input, option) =>
                        (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                      }
                    />
                  </Form.Item>
                  <Form.Item name="targetLanguage" label={t('Target Lang')}>
                    <Select 
                      options={TARGET_LANGUAGES.map(l => ({ value: l.value, label: l.label }))}
                      showSearch
                      filterOption={(input, option) =>
                        (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                      }
                    />
                  </Form.Item>
                  <Form.Item name="whisperMethod" label="Whisper Method">
                    <Select options={WHISPER_METHODS.map(m => ({ value: m.value, label: m.label }))} />
                  </Form.Item>
                  <Form.Item name="demucs" label={t('Vocal separation enhance')} valuePropName="checked">
                    <Switch />
                  </Form.Item>
                  <Form.Item name="burnSubtitles" label={t('Burn-in Subtitles')} valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </>
              ),
            },
            {
              key: 'dubbing',
              label: t('Dubbing Settings'),
              children: (
                <Form.Item name="ttsMethod" label={t('TTS Method')}>
                  <Select options={TTS_METHODS.map(m => ({ value: m.value, label: m.label }))} />
                </Form.Item>
              ),
            },
            {
              key: 'network',
              label: t('Network Settings'),
              children: (
                <>
                  <Form.Item 
                    name="httpProxy" 
                    label={t('HTTP Proxy')}
                    tooltip={t('proxyTooltip')}
                  >
                    <Input placeholder="http://127.0.0.1:10809" />
                  </Form.Item>
                  <Form.Item 
                    name="hfMirror" 
                    label={t('HuggingFace Mirror')}
                    tooltip={t('hfMirrorTooltip')}
                  >
                    <Input placeholder="https://hf-mirror.com" />
                  </Form.Item>
                </>
              ),
            },
          ]}
        />
      </Form>
    </Modal>
  )
}
