/**
 * Console Panel Component - Displays real-time processing logs
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { Typography, Select, Button, Switch, Tag } from 'antd'
import { ClearOutlined, DownOutlined, UpOutlined, InfoCircleOutlined, WarningOutlined, CloseCircleOutlined, FullscreenOutlined, FullscreenExitOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { createPortal } from 'react-dom'
import type { LogEntry, LogLevel } from '../types'
import { getLogs, clearLogs } from '../services/api'

const { Text } = Typography

interface ConsolePanelProps {
  isProcessing?: boolean
  className?: string
}

const POLL_INTERVAL = 3000 // 3 seconds
const MAX_VISIBLE_LOGS = 500 // Keep last 500 logs in view

const LogLevelIcon = ({ level }: { level: LogLevel }) => {
  switch (level) {
    case 'ERROR':
      return <CloseCircleOutlined className="text-red-500" />
    case 'WARNING':
      return <WarningOutlined className="text-yellow-500" />
    case 'INFO':
    default:
      return <InfoCircleOutlined className="text-blue-500" />
  }
}

const LogSourceTag = ({ source }: { source?: string }) => {
  if (!source) return null
  
  const colors: Record<string, string> = {
    subtitle: 'blue',
    dubbing: 'purple',
    llm: 'green',
    system: 'default'
  }
  
  return (
    <Tag color={colors[source] || 'default'} className="text-xs">
      {source}
    </Tag>
  )
}

export default function ConsolePanel({ isProcessing = false, className = '' }: ConsolePanelProps) {
  const { t } = useTranslation()
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [levelFilter, setLevelFilter] = useState<LogLevel | 'ALL'>('ALL')
  const [sourceFilter, setSourceFilter] = useState<string | 'ALL'>('ALL')
  const [autoScroll, setAutoScroll] = useState(true)
  const [collapsed, setCollapsed] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const logContainerRef = useRef<HTMLDivElement>(null)
  const fullscreenLogRef = useRef<HTMLDivElement>(null)
  const lastIdRef = useRef<number>(0)
  const fetchingRef = useRef<boolean>(false) // Prevent concurrent fetches
  const mountedRef = useRef<boolean>(false) // Track if already fetched on mount

  // Fetch logs - use refs to avoid stale closures
  const fetchLogs = useCallback(async (overrideLevel?: LogLevel | 'ALL', overrideSource?: string | 'ALL') => {
    // Prevent concurrent fetches
    if (fetchingRef.current) return
    fetchingRef.current = true
    
    // Use override values if provided (for filter changes), otherwise use state
    const effectiveLevel = overrideLevel !== undefined ? overrideLevel : levelFilter
    const effectiveSource = overrideSource !== undefined ? overrideSource : sourceFilter
    
    try {
      const response = await getLogs({
        lastId: lastIdRef.current > 0 ? lastIdRef.current : undefined,
        limit: 100,
        level: effectiveLevel !== 'ALL' ? effectiveLevel : undefined,
        source: effectiveSource !== 'ALL' ? effectiveSource : undefined,
      })
      
      if (response.logs.length > 0) {
        setLogs(prev => {
          // Deduplicate by ID before adding
          const existingIds = new Set(prev.map(l => l.id))
          const uniqueNewLogs = response.logs.filter(l => !existingIds.has(l.id))
          if (uniqueNewLogs.length === 0) return prev
          
          const newLogs = [...prev, ...uniqueNewLogs]
          // Keep only last MAX_VISIBLE_LOGS
          return newLogs.slice(-MAX_VISIBLE_LOGS)
        })
        
        // Update lastId to the highest ID received
        const maxId = Math.max(...response.logs.map(l => l.id))
        if (maxId > lastIdRef.current) {
          lastIdRef.current = maxId
        }
      }
    } catch (error) {
      console.error('Failed to fetch logs:', error)
    } finally {
      fetchingRef.current = false
    }
  }, [levelFilter, sourceFilter])

  // Single effect for both initial fetch and polling
  useEffect(() => {
    // Initial fetch only once per mount (avoid StrictMode double-fetch)
    if (!mountedRef.current) {
      mountedRef.current = true
      fetchLogs()
    }
    
    // Set up polling when processing
    if (!isProcessing) return
    
    const interval = setInterval(fetchLogs, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [isProcessing, fetchLogs])

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  // Clear logs
  const handleClearLogs = async () => {
    try {
      await clearLogs()
      setLogs([])
      lastIdRef.current = 0
    } catch (error) {
      console.error('Failed to clear logs:', error)
    }
  }

  // Reset lastId when filter changes to re-fetch filtered logs
  const handleFilterChange = async (newLevel: LogLevel | 'ALL', newSource: string | 'ALL') => {
    // Clear current logs and reset lastId
    setLogs([])
    lastIdRef.current = 0
    fetchingRef.current = false // Reset fetching flag to allow immediate fetch
    
    // Update state
    setLevelFilter(newLevel)
    setSourceFilter(newSource)
    
    // Immediately fetch with new filters (pass them directly to avoid stale state)
    await fetchLogs(newLevel, newSource)
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      hour12: false
    })
  }

  const filteredLogs = logs // Already filtered by backend, but can add client-side filtering if needed

  // Auto-scroll for fullscreen mode
  useEffect(() => {
    if (autoScroll && isFullscreen && fullscreenLogRef.current) {
      fullscreenLogRef.current.scrollTop = fullscreenLogRef.current.scrollHeight
    }
  }, [logs, autoScroll, isFullscreen])

  // Log entry renderer
  const renderLogEntry = (log: LogEntry) => (
    <div 
      key={log.id} 
      className="log-entry flex items-start gap-2 py-1 hover:bg-gray-800 px-1 rounded"
    >
      <span className="text-gray-500 text-xs whitespace-nowrap">
        {formatTimestamp(log.timestamp)}
      </span>
      <LogLevelIcon level={log.level} />
      <LogSourceTag source={log.source} />
      <span className={`flex-1 ${
        log.level === 'ERROR' ? 'text-red-400' :
        log.level === 'WARNING' ? 'text-yellow-400' :
        'text-gray-300'
      }`}>
        {log.message}
      </span>
      {log.durationMs !== undefined && (
        <span className="text-gray-500 text-xs">
          {log.durationMs}ms
        </span>
      )}
    </div>
  )

  return (
    <>
      <div className={`console-panel bg-gray-900 rounded-lg overflow-hidden ${className}`}>
        {/* Header */}
        <div className="console-header flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <Text className="text-white font-medium">{t('Console')}</Text>
            <Tag color={isProcessing ? 'processing' : 'default'}>
              {isProcessing ? t('running') : t('idle')}
            </Tag>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Level Filter */}
            <Select
              size="small"
              value={levelFilter}
              onChange={(v) => handleFilterChange(v, sourceFilter)}
              options={[
                { value: 'ALL', label: t('All Levels') },
                { value: 'INFO', label: 'INFO' },
                { value: 'WARNING', label: 'WARNING' },
                { value: 'ERROR', label: 'ERROR' },
              ]}
              className="w-28"
              popupClassName="console-select-popup"
            />
            
            {/* Source Filter */}
            <Select
              size="small"
              value={sourceFilter}
              onChange={(v) => handleFilterChange(levelFilter, v)}
              options={[
                { value: 'ALL', label: t('All Sources') },
                { value: 'subtitle', label: t('Subtitle') },
                { value: 'dubbing', label: t('Dubbing') },
                { value: 'llm', label: 'LLM' },
              ]}
              className="w-28"
              popupClassName="console-select-popup"
            />
            
            {/* Auto-scroll Toggle */}
            <div className="flex items-center gap-1">
              <Text className="text-gray-400 text-xs">{t('Auto Scroll')}</Text>
              <Switch 
                size="small" 
                checked={autoScroll} 
                onChange={setAutoScroll}
              />
            </div>
            
            {/* Clear Button */}
            <Button
              size="small"
              icon={<ClearOutlined />}
              onClick={handleClearLogs}
              className="text-gray-400 hover:text-white"
            >
              {t('Clear')}
            </Button>

            {/* Fullscreen Toggle */}
            <Button
              size="small"
              type="text"
              icon={<FullscreenOutlined />}
              onClick={() => setIsFullscreen(true)}
              className="text-gray-400 hover:text-white"
              title={t('Fullscreen')}
            />
            
            {/* Collapse Toggle */}
            <Button
              size="small"
              type="text"
              icon={collapsed ? <DownOutlined /> : <UpOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              className="text-gray-400 hover:text-white"
            />
          </div>
        </div>
        
        {/* Log Content - Increased height */}
        {!collapsed && (
          <div 
            ref={logContainerRef}
            className="console-content h-80 overflow-y-auto p-2 font-mono text-sm"
          >
            {filteredLogs.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                {t('No logs yet')}
              </div>
            ) : (
              filteredLogs.map(renderLogEntry)
            )}
          </div>
        )}
      </div>

      {/* Fullscreen Modal - rendered via Portal to escape parent styling */}
      {isFullscreen && createPortal(
        <div 
          className="console-fullscreen"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 9999,
            backgroundColor: '#111827',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Fullscreen Header */}
          <div 
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              backgroundColor: '#1f2937',
              borderBottom: '1px solid #374151',
            }}
          >
            <div className="flex items-center gap-2">
              <Text className="text-white font-medium text-lg">{t('Console')}</Text>
              <Tag color={isProcessing ? 'processing' : 'default'}>
                {isProcessing ? t('running') : t('idle')}
              </Tag>
              <span className="text-gray-400 text-sm ml-2">
                {filteredLogs.length} {t('logs')}
              </span>
            </div>
            
            <div className="flex items-center gap-3">
              {/* Level Filter */}
              <Select
                size="small"
                value={levelFilter}
                onChange={(v) => handleFilterChange(v, sourceFilter)}
                options={[
                  { value: 'ALL', label: t('All Levels') },
                  { value: 'INFO', label: 'INFO' },
                  { value: 'WARNING', label: 'WARNING' },
                  { value: 'ERROR', label: 'ERROR' },
                ]}
                className="w-28"
                popupClassName="console-select-popup"
              />
              
              {/* Source Filter */}
              <Select
                size="small"
                value={sourceFilter}
                onChange={(v) => handleFilterChange(levelFilter, v)}
                options={[
                  { value: 'ALL', label: t('All Sources') },
                  { value: 'subtitle', label: t('Subtitle') },
                  { value: 'dubbing', label: t('Dubbing') },
                  { value: 'llm', label: 'LLM' },
                ]}
                className="w-28"
                popupClassName="console-select-popup"
              />
              
              {/* Auto-scroll Toggle */}
              <div className="flex items-center gap-1">
                <Text className="text-gray-400 text-xs">{t('Auto Scroll')}</Text>
                <Switch 
                  size="small" 
                  checked={autoScroll} 
                  onChange={setAutoScroll}
                />
              </div>
              
              {/* Clear Button */}
              <Button
                size="small"
                icon={<ClearOutlined />}
                onClick={handleClearLogs}
                className="text-gray-400 hover:text-white"
              >
                {t('Clear')}
              </Button>

              {/* Exit Fullscreen */}
              <Button
                size="small"
                type="primary"
                icon={<FullscreenExitOutlined />}
                onClick={() => setIsFullscreen(false)}
              >
                {t('Exit Fullscreen')}
              </Button>
            </div>
          </div>
          
          {/* Fullscreen Log Content */}
          <div 
            ref={fullscreenLogRef}
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '16px',
              fontFamily: 'monospace',
              fontSize: '14px',
            }}
          >
            {filteredLogs.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                {t('No logs yet')}
              </div>
            ) : (
              filteredLogs.map(renderLogEntry)
            )}
          </div>
        </div>,
        document.body
      )}
    </>
  )
}
