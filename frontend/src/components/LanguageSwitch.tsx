/**
 * Language Switch Component - Placeholder
 * Will be fully implemented in Phase 7 (US5)
 */
import { Select } from 'antd'
import { GlobalOutlined } from '@ant-design/icons'
import { SUPPORTED_LANGUAGES } from '../types'
import { changeLanguage, getCurrentLanguage } from '../i18n'

export default function LanguageSwitch() {
  const currentLang = getCurrentLanguage()

  const handleChange = (value: string) => {
    changeLanguage(value)
    window.location.reload() // Reload to apply Ant Design locale
  }

  return (
    <Select
      value={currentLang}
      onChange={handleChange}
      style={{ width: 130 }}
      suffixIcon={<GlobalOutlined />}
      options={SUPPORTED_LANGUAGES.map((lang) => ({
        value: lang.code,
        label: lang.nativeName,
      }))}
    />
  )
}
