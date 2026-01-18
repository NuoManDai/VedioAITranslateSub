/**
 * Network Settings Tab Component
 * 网络设置选项卡
 */
import { Form, Input } from 'antd'
import { useTranslation } from 'react-i18next'

export default function NetworkSettings() {
  const { t } = useTranslation()

  return (
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
  )
}
