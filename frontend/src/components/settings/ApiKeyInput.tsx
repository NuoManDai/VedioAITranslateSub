/**
 * API Key Input Component with link button
 * 带有获取密钥链接的 API Key 输入框
 */
import { Form, Input } from 'antd'

interface ApiKeyInputProps {
  name: string
  label: string
  placeholder?: string
  linkUrl: string
  linkIcon?: string
}

export default function ApiKeyInput({ 
  name, 
  label, 
  placeholder = 'Enter API Key...', 
  linkUrl,
  linkIcon = '🔑'
}: ApiKeyInputProps) {
  return (
    <Form.Item 
      name={name} 
      label={label}
    >
      <Input.Password 
        placeholder={placeholder} 
        addonAfter={
          <a href={linkUrl} target="_blank" rel="noopener noreferrer">
            {linkIcon}
          </a>
        }
      />
    </Form.Item>
  )
}
