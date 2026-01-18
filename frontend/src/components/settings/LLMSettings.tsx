/**
 * LLM Settings Tab Component
 * LLM 配置选项卡
 */
import { Form, Input, Switch, Button } from 'antd'
import { useTranslation } from 'react-i18next'

interface LLMSettingsProps {
  validating: boolean
  onTestApi: () => void
}

export default function LLMSettings({ validating, onTestApi }: LLMSettingsProps) {
  const { t } = useTranslation()

  return (
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
      <Button loading={validating} onClick={onTestApi}>
        {t('testApi')}
      </Button>
    </>
  )
}
