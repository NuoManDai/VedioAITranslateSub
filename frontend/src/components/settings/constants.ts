/**
 * Settings Constants
 * 设置相关的常量定义
 */

// API 来源链接
export const API_LINKS = {
  '302AI': 'https://302.ai/apis/',
  'SILICONFLOW': 'https://siliconflow.cn/',
  'ELEVENLABS': 'https://elevenlabs.io/',
  'FISH_AUDIO': 'https://fish.audio/zh-CN/discovery/',
  'GPT_SOVITS': 'https://github.com/RVC-Boss/GPT-SoVITS',
  'AZURE_DOCS': 'https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts',
}

// OpenAI TTS 预设语音
export const OPENAI_VOICES = [
  { value: 'alloy', label: 'Alloy' },
  { value: 'echo', label: 'Echo' },
  { value: 'fable', label: 'Fable' },
  { value: 'onyx', label: 'Onyx' },
  { value: 'nova', label: 'Nova' },
  { value: 'shimmer', label: 'Shimmer' },
]

// Fish TTS 角色预设
export const FISH_TTS_CHARACTERS = [
  { value: '派蒙', label: '派蒙 (原神)' },
  { value: '钟离', label: '钟离 (原神)' },
  { value: '胡桃', label: '胡桃 (原神)' },
  { value: '刻晴', label: '刻晴 (原神)' },
  { value: '甘雨', label: '甘雨 (原神)' },
  { value: '雷电将军', label: '雷电将军 (原神)' },
  { value: '纳西妲', label: '纳西妲 (原神)' },
  { value: '芙宁娜', label: '芙宁娜 (原神)' },
  { value: '流萤', label: '流萤 (崩铁)' },
  { value: '花火', label: '花火 (崩铁)' },
  { value: '赛马娘', label: '赛马娘' },
  { value: '雷军', label: '雷军' },
  { value: '央视配音', label: '央视配音' },
]

// GPT-SoVITS 参考模式
export const GPT_SOVITS_MODES = [
  { value: 1, labelKey: 'Mode 1: Use provided reference audio only' },
  { value: 2, labelKey: 'Mode 2: Use first audio from video as reference' },
  { value: 3, labelKey: 'Mode 3: Use each audio from video as reference' },
]
