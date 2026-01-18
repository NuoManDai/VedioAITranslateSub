/**
 * Subtitle Settings Tab Component
 * 字幕设置选项卡
 */
import { Form, Select, Switch, Input } from 'antd'
import { useTranslation } from 'react-i18next'
import { SOURCE_LANGUAGES, TARGET_LANGUAGES, WHISPER_METHODS, WhisperMethod } from '../../types'
import { API_LINKS } from './constants'

interface SubtitleSettingsProps {
  whisperMethod: WhisperMethod
  onWhisperMethodChange: (value: WhisperMethod) => void
}

export default function SubtitleSettings({ whisperMethod, onWhisperMethodChange }: SubtitleSettingsProps) {
  const { t } = useTranslation()

  return (
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
        <Select 
          options={WHISPER_METHODS.map(m => ({ value: m.value, label: m.label }))} 
          onChange={(value) => onWhisperMethodChange(value as WhisperMethod)}
        />
      </Form.Item>
      
      {/* Cloud Whisper - 302.ai */}
      {whisperMethod === 'cloud' && (
        <Form.Item 
          name="whisperX302ApiKey" 
          label="302.ai API Key"
          tooltip={t('Click to get 302.ai API key')}
        >
          <Input.Password 
            placeholder="Enter 302.ai API Key..." 
            addonAfter={
              <a href={API_LINKS['302AI']} target="_blank" rel="noopener noreferrer">
                🔑
              </a>
            }
          />
        </Form.Item>
      )}
      
      {/* ElevenLabs Whisper */}
      {whisperMethod === 'elevenlabs' && (
        <Form.Item 
          name="elevenlabsApiKey" 
          label="ElevenLabs API Key"
          tooltip={t('Click to get ElevenLabs API key')}
        >
          <Input.Password 
            placeholder="Enter ElevenLabs API Key..." 
            addonAfter={
              <a href={API_LINKS['ELEVENLABS']} target="_blank" rel="noopener noreferrer">
                🔑
              </a>
            }
          />
        </Form.Item>
      )}
      
      <Form.Item name="demucs" label={t('Vocal separation enhance')} valuePropName="checked">
        <Switch />
      </Form.Item>
      <Form.Item name="burnSubtitles" label={t('Burn-in Subtitles')} valuePropName="checked">
        <Switch />
      </Form.Item>
    </>
  )
}
