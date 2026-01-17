import { useState, lazy, Suspense } from 'react'
import { Layout, Typography, Button, Space, Spin } from 'antd'
import { SettingOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import LanguageSwitch from './components/LanguageSwitch'

// Lazy load heavy components
const Home = lazy(() => import('./pages/Home'))
const SettingsModal = lazy(() => import('./components/SettingsModal'))

const { Header, Content, Footer } = Layout
const { Title } = Typography

// Loading fallback component
const LoadingFallback = () => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center">
      <Spin size="large" />
      <p className="mt-4 text-gray-500">Loading...</p>
    </div>
  </div>
)

function App() {
  const { t } = useTranslation()
  const [settingsVisible, setSettingsVisible] = useState(false)

  return (
    <Layout className="min-h-screen app-bg">
      <Header className="modern-header !flex !items-center justify-between px-8" style={{ height: 64, lineHeight: 'normal' }}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center" 
               style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <ThunderboltOutlined className="text-white text-xl" />
          </div>
          <Title level={4} className="app-logo" style={{ margin: 0 }}>
            {t('appName')}
          </Title>
        </div>
        <Space size="middle" className="flex items-center">
          <LanguageSwitch />
          <Button
            type="text"
            icon={<SettingOutlined />}
            className="flex items-center gap-2 hover:bg-gray-100 rounded-lg px-4 h-10"
            onClick={() => setSettingsVisible(true)}
          >
            {t('settings')}
          </Button>
        </Space>
      </Header>
      
      <Content className="page-container">
        <Suspense fallback={<LoadingFallback />}>
          <Home />
        </Suspense>
      </Content>
      
      <Footer className="modern-footer text-center py-6">
        <span className="opacity-60">{t('appName')} ©{new Date().getFullYear()} — </span>
        <span className="opacity-40">AI-Powered Video Translation</span>
      </Footer>

      <Suspense fallback={null}>
        <SettingsModal
          open={settingsVisible}
          onClose={() => setSettingsVisible(false)}
        />
      </Suspense>
    </Layout>
  )
}

export default App
