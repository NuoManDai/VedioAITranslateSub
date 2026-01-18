/**
 * Settings Modal Component
 * 设置弹窗组件 - 重构后的简化版本
 */
import { Modal, Form, Button, Tabs, message } from 'antd'
import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'
import { TTSMethodType, WhisperMethod } from '../types'
import { getConfig, updateConfig, validateApiKey, getAzureVoices } from '../services/api'
import type { AzureVoice } from '../types'
import { 
  LLMSettings, 
  SubtitleSettings, 
  DubbingSettings, 
  NetworkSettings 
} from './settings'
import { getDefaultMaxSplitLength } from './settings/SubtitleSettings'

interface SettingsModalProps {
  open: boolean
  onClose: () => void
}

export default function SettingsModal({ open, onClose }: SettingsModalProps) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [ttsMethod, setTtsMethod] = useState<TTSMethodType>('azure_tts')
  const [whisperMethod, setWhisperMethod] = useState<WhisperMethod>('local')
  const [azureVoices, setAzureVoices] = useState<AzureVoice[]>([])
  const [loadingVoices, setLoadingVoices] = useState(false)

  useEffect(() => {
    if (open) {
      loadConfig()
    }
  }, [open])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const config = await getConfig()
      const currentWhisperMethod = config.whisper?.method || 'local'
      const currentTtsMethod = config.ttsMethod || 'edge_tts'
      setWhisperMethod(currentWhisperMethod as WhisperMethod)
      setTtsMethod(currentTtsMethod as TTSMethodType)
      // 计算正确的分句阈值：如果配置中有值则用配置值，否则根据语言使用默认值
      // 但如果当前语言是日语且配置值是20（英语默认值），则修正为12
      const sourceLanguage = config.sourceLanguage || 'en'
      let maxSplitLength = config.maxSplitLength
      if (!maxSplitLength || (sourceLanguage === 'ja' && maxSplitLength === 20)) {
        maxSplitLength = getDefaultMaxSplitLength(sourceLanguage)
      }
      
      form.setFieldsValue({
        apiKey: config.api?.key || '',
        baseUrl: config.api?.baseUrl || 'https://api.openai.com',
        model: config.api?.model || 'gpt-4o-mini',
        llmSupportJson: config.api?.llmSupportJson ?? false,
        targetLanguage: config.targetLanguage || '简体中文',
        sourceLanguage: sourceLanguage,
        maxSplitLength: maxSplitLength,
        timeGapThreshold: config.timeGapThreshold || undefined,
        demucs: config.demucs ?? false,
        burnSubtitles: config.burnSubtitles ?? true,
        ttsMethod: currentTtsMethod,
        whisperMethod: currentWhisperMethod,
        whisperX302ApiKey: config.whisper?.whisperX302ApiKey || '',
        elevenlabsApiKey: config.whisper?.elevenlabsApiKey || '',
        // TTS configurations
        sfFishTtsApiKey: config.sfFishTtsApiKey || '',
        sfFishTtsMode: config.sfFishTtsMode || 'preset',
        sfFishTtsVoice: config.sfFishTtsVoice || 'anna',
        openaiTtsApiKey: config.openaiTtsApiKey || '',
        openaiVoice: config.openaiVoice || 'alloy',
        fishTtsApiKey: config.fishTtsApiKey || '',
        fishTtsCharacter: config.fishTtsCharacter || 'AD学姐',
        azureKey: config.azureKey || '',
        azureVoice: config.azureVoice || 'zh-CN-YunfengNeural',
        sovitsCharacter: config.sovitsCharacter || '',
        gptSovitsReferMode: config.gptSovitsReferMode || 3,
        edgeTtsVoice: config.edgeTtsVoice || 'zh-CN-XiaoxiaoNeural',
        sfCosyvoice2ApiKey: config.sfCosyvoice2ApiKey || '',
        f5ttsApiKey: config.f5ttsApiKey || '',
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
        maxSplitLength: values.maxSplitLength || getDefaultMaxSplitLength(values.sourceLanguage || 'en'),
        timeGapThreshold: values.timeGapThreshold || undefined,
        demucs: values.demucs,
        burnSubtitles: values.burnSubtitles,
        ttsMethod: values.ttsMethod,
        whisper: {
          method: values.whisperMethod,
          whisperXModel: 'large-v2',
          whisperX302ApiKey: values.whisperX302ApiKey || '',
          elevenlabsApiKey: values.elevenlabsApiKey || '',
        },
        // TTS configurations
        sfFishTtsApiKey: values.sfFishTtsApiKey || '',
        sfFishTtsMode: values.sfFishTtsMode || 'preset',
        sfFishTtsVoice: values.sfFishTtsVoice || '',
        openaiTtsApiKey: values.openaiTtsApiKey || '',
        openaiVoice: values.openaiVoice || 'alloy',
        fishTtsApiKey: values.fishTtsApiKey || '',
        fishTtsCharacter: values.fishTtsCharacter || '',
        azureKey: values.azureKey || '',
        azureVoice: values.azureVoice || '',
        sovitsCharacter: values.sovitsCharacter || '',
        gptSovitsReferMode: values.gptSovitsReferMode || 3,
        edgeTtsVoice: values.edgeTtsVoice || '',
        sfCosyvoice2ApiKey: values.sfCosyvoice2ApiKey || '',
        f5ttsApiKey: values.f5ttsApiKey || '',
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

  const handleFetchAzureVoices = async () => {
    try {
      setLoadingVoices(true)
      const response = await getAzureVoices()
      setAzureVoices(response.voices)
      message.success(t('Voice list fetched successfully'))
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('Failed to fetch voice list'))
    } finally {
      setLoadingVoices(false)
    }
  }

  // 语言切换时重置分词数量
  const handleSourceLanguageChange = (language: string) => {
    form.setFieldsValue({
      maxSplitLength: getDefaultMaxSplitLength(language)
    })
  }

  const tabItems = [
    {
      key: 'llm',
      label: t('LLM Configuration'),
      children: (
        <LLMSettings 
          validating={validating} 
          onTestApi={handleTestApi} 
        />
      ),
    },
    {
      key: 'subtitle',
      label: t('Subtitles Settings'),
      children: (
        <SubtitleSettings 
          whisperMethod={whisperMethod}
          onWhisperMethodChange={setWhisperMethod}
          onSourceLanguageChange={handleSourceLanguageChange}
        />
      ),
    },
    {
      key: 'dubbing',
      label: t('Dubbing Settings'),
      children: (
        <DubbingSettings 
          ttsMethod={ttsMethod}
          onTtsMethodChange={setTtsMethod}
          azureVoices={azureVoices}
          loadingVoices={loadingVoices}
          onFetchAzureVoices={handleFetchAzureVoices}
        />
      ),
    },
    {
      key: 'network',
      label: t('Network Settings'),
      children: <NetworkSettings />,
    },
  ]

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
        <Tabs items={tabItems} />
      </Form>
    </Modal>
  )
}
