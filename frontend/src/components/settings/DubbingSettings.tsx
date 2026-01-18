/**
 * Dubbing Settings Tab Component
 * 配音设置选项卡
 */
import { Form, Select, Input, Button } from 'antd'
import { useTranslation } from 'react-i18next'
import { TTS_METHODS, TTSMethodType } from '../../types'
import type { AzureVoice } from '../../types'
import TTSDescription from './TTSDescription'
import { API_LINKS, OPENAI_VOICES, FISH_TTS_CHARACTERS, GPT_SOVITS_MODES } from './constants'

interface DubbingSettingsProps {
  ttsMethod: TTSMethodType
  onTtsMethodChange: (value: TTSMethodType) => void
  azureVoices: AzureVoice[]
  loadingVoices: boolean
  onFetchAzureVoices: () => void
}

export default function DubbingSettings({ 
  ttsMethod, 
  onTtsMethodChange,
  azureVoices,
  loadingVoices,
  onFetchAzureVoices
}: DubbingSettingsProps) {
  const { t } = useTranslation()

  return (
    <>
      <Form.Item name="ttsMethod" label={t('TTS Method')}>
        <Select 
          options={TTS_METHODS.map(m => ({ value: m.value, label: m.label }))} 
          onChange={(value) => onTtsMethodChange(value as TTSMethodType)}
        />
      </Form.Item>
      
      {/* SiliconFlow Fish TTS */}
      {ttsMethod === 'sf_fish_tts' && (
        <>
          <TTSDescription type="clone" descKey="sf_fish_tts_desc" color="blue" />
          <Form.Item name="sfFishTtsApiKey" label="SiliconFlow API Key">
            <Input.Password 
              placeholder="Enter SiliconFlow API Key..." 
              addonAfter={
                <a href={API_LINKS['SILICONFLOW']} target="_blank" rel="noopener noreferrer">🔑</a>
              }
            />
          </Form.Item>
          <Form.Item 
            name="sfFishTtsMode" 
            label={t('Mode Selection')}
            tooltip={t('sf_fish_tts_mode_tooltip')}
          >
            <Select 
              options={[
                { value: 'preset', label: t('Preset') + ' - ' + t('preset_mode_desc') },
                { value: 'custom', label: t('Refer_stable') + ' - ' + t('custom_mode_desc') },
                { value: 'dynamic', label: t('Refer_dynamic') + ' - ' + t('dynamic_mode_desc') },
              ]}
            />
          </Form.Item>
          <Form.Item name="sfFishTtsVoice" label="Voice">
            <Input placeholder="anna" />
          </Form.Item>
        </>
      )}
      
      {/* OpenAI TTS - 302.ai */}
      {ttsMethod === 'openai_tts' && (
        <>
          <TTSDescription type="preset" descKey="openai_tts_desc" color="gray" />
          <Form.Item name="openaiTtsApiKey" label="302.ai API Key">
            <Input.Password 
              placeholder="Enter 302.ai API Key..." 
              addonAfter={
                <a href={API_LINKS['302AI']} target="_blank" rel="noopener noreferrer">🔑</a>
              }
            />
          </Form.Item>
          <Form.Item name="openaiVoice" label={t('OpenAI Voice')}>
            <Select options={OPENAI_VOICES} />
          </Form.Item>
        </>
      )}
      
      {/* Fish TTS - 302.ai */}
      {ttsMethod === 'fish_tts' && (
        <>
          <TTSDescription type="community" descKey="fish_tts_desc" color="purple" />
          <Form.Item name="fishTtsApiKey" label="302.ai API Key">
            <Input.Password 
              placeholder="Enter 302.ai API Key..." 
              addonAfter={
                <a href={API_LINKS['302AI']} target="_blank" rel="noopener noreferrer">🔑</a>
              }
            />
          </Form.Item>
          <Form.Item 
            name="fishTtsCharacter" 
            label={
              <span>
                {t('Fish TTS Character')}
                <a 
                  href={API_LINKS['FISH_AUDIO']} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="ml-2 text-purple-500 hover:text-purple-700"
                >
                  🎭 {t('Browse Voices')}
                </a>
              </span>
            }
            tooltip={t('fish_tts_character_tooltip')}
          >
            <Select options={FISH_TTS_CHARACTERS} />
          </Form.Item>
        </>
      )}
      
      {/* Azure TTS - 302.ai */}
      {ttsMethod === 'azure_tts' && (
        <>
          <TTSDescription type="preset" descKey="azure_tts_desc" color="gray" />
          <Form.Item name="azureKey" label="302.ai API Key">
            <Input.Password 
              placeholder="Enter 302.ai API Key..." 
              addonAfter={
                <a href={API_LINKS['302AI']} target="_blank" rel="noopener noreferrer">🔑</a>
              }
            />
          </Form.Item>
          <Form.Item name="azureVoice" label={t('Azure Voice')}>
            {azureVoices.length > 0 ? (
              <Select
                showSearch
                placeholder={t('Select a voice')}
                options={azureVoices.map(v => ({
                  value: v.shortName,
                  label: `${v.localeName} - ${v.displayName} (${v.gender})`
                }))}
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                loading={loadingVoices}
              />
            ) : (
              <Input placeholder="zh-CN-YunfengNeural" />
            )}
          </Form.Item>
          <div className="flex gap-2 mb-4">
            <Button loading={loadingVoices} onClick={onFetchAzureVoices}>
              📋 {t('Load Voice Presets')}
            </Button>
            <Button type="link" href={API_LINKS['AZURE_DOCS']} target="_blank">
              📖 {t('Full Voice List')}
            </Button>
          </div>
        </>
      )}
      
      {/* GPT-SoVITS - Local */}
      {ttsMethod === 'gpt_sovits' && (
        <>
          <TTSDescription type="local" descKey="gpt_sovits_desc" color="green" />
          <Form.Item>
            <Button 
              type="link" 
              href={API_LINKS['GPT_SOVITS']} 
              target="_blank"
              className="p-0"
            >
              📖 {t('GPT-SoVITS Setup Guide')}
            </Button>
          </Form.Item>
          <Form.Item name="sovitsCharacter" label={t('SoVITS Character')}>
            <Input placeholder="Huanyuv2" />
          </Form.Item>
          <Form.Item 
            name="gptSovitsReferMode" 
            label={t('Refer Mode')}
            tooltip={t('Configure reference audio mode for GPT-SoVITS')}
          >
            <Select 
              options={GPT_SOVITS_MODES.map(m => ({ value: m.value, label: t(m.labelKey) }))}
            />
          </Form.Item>
        </>
      )}
      
      {/* Edge TTS - Free */}
      {ttsMethod === 'edge_tts' && (
        <>
          <TTSDescription type="free" descKey="edge_tts_desc" color="green" />
          <Form.Item 
            name="edgeTtsVoice" 
            label={t('Edge TTS Voice')}
            tooltip={t('edge_tts_voice_tooltip')}
          >
            <Input placeholder="zh-CN-XiaoxiaoNeural" />
          </Form.Item>
        </>
      )}
      
      {/* SiliconFlow CosyVoice2 */}
      {ttsMethod === 'sf_cosyvoice2' && (
        <>
          <TTSDescription type="auto-clone" descKey="sf_cosyvoice2_desc" color="blue" />
          <Form.Item name="sfCosyvoice2ApiKey" label="SiliconFlow API Key">
            <Input.Password 
              placeholder="Enter SiliconFlow API Key..." 
              addonAfter={
                <a href={API_LINKS['SILICONFLOW']} target="_blank" rel="noopener noreferrer">🔑</a>
              }
            />
          </Form.Item>
        </>
      )}
      
      {/* F5-TTS - 302.ai */}
      {ttsMethod === 'f5tts' && (
        <>
          <TTSDescription type="auto-clone" descKey="f5tts_desc" color="blue" />
          <Form.Item name="f5ttsApiKey" label="302.ai API Key">
            <Input.Password 
              placeholder="Enter 302.ai API Key..." 
              addonAfter={
                <a href={API_LINKS['302AI']} target="_blank" rel="noopener noreferrer">🔑</a>
              }
            />
          </Form.Item>
        </>
      )}
      
      {/* Custom TTS */}
      {ttsMethod === 'custom_tts' && (
        <TTSDescription type="custom" descKey="custom_tts_desc" color="yellow" />
      )}
    </>
  )
}
