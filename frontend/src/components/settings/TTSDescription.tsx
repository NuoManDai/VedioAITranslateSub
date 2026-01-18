/**
 * TTS Description Card Component
 * 显示 TTS 方法的说明卡片
 */
import { useTranslation } from 'react-i18next'

interface TTSDescriptionProps {
  type: 'clone' | 'preset' | 'free' | 'local' | 'custom' | 'auto-clone' | 'community'
  title?: string
  descKey: string
  color?: 'blue' | 'purple' | 'green' | 'gray' | 'yellow'
}

const colorClasses = {
  blue: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    title: 'text-blue-700 dark:text-blue-300'
  },
  purple: {
    bg: 'bg-purple-50 dark:bg-purple-900/20',
    title: 'text-purple-700 dark:text-purple-300'
  },
  green: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    title: 'text-green-700 dark:text-green-300'
  },
  gray: {
    bg: 'bg-gray-50 dark:bg-gray-800',
    title: 'text-gray-700 dark:text-gray-300'
  },
  yellow: {
    bg: 'bg-yellow-50 dark:bg-yellow-900/20',
    title: 'text-yellow-700 dark:text-yellow-300'
  }
}

const typeIcons = {
  'clone': '🎭',
  'preset': '🔊',
  'free': '✨',
  'local': '🎯',
  'custom': '⚙️',
  'auto-clone': '🎭',
  'community': '🎤'
}

const typeTitleKeys = {
  'clone': 'Voice Clone Support',
  'preset': 'Preset Voices Only',
  'free': 'Free - No API Key Required',
  'local': 'Voice Clone Support',
  'custom': 'Custom Implementation',
  'auto-clone': 'Auto Voice Clone',
  'community': 'Community Voice Library'
}

export default function TTSDescription({ type, title, descKey, color = 'blue' }: TTSDescriptionProps) {
  const { t } = useTranslation()
  const classes = colorClasses[color]
  const icon = typeIcons[type]
  const titleKey = title || typeTitleKeys[type]

  return (
    <div className={`mb-3 p-3 ${classes.bg} rounded-lg text-sm`}>
      <div className={`font-medium ${classes.title} mb-1`}>
        {icon} {t(titleKey)}
        {type === 'local' && ` - ${t('Local Training')}`}
      </div>
      <div className="text-gray-600 dark:text-gray-400">
        {t(descKey)}
      </div>
    </div>
  )
}
