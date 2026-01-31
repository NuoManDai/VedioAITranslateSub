/**
 * SubtitleEditor Page - Timeline-based subtitle editor
 */
import { useEffect, useRef, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout, Button, Space, Spin, Modal, Typography, Badge, Radio, Switch, Tooltip } from 'antd';
import { 
  ArrowLeftOutlined, 
  SaveOutlined, 
  VideoCameraOutlined,
  ExclamationCircleOutlined,
  UndoOutlined,
  SettingOutlined,
  BgColorsOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useSubtitleEditor, resetDraftRestoreMessageFlag } from '../hooks/useSubtitleEditor';
import { VideoSync, SubtitleList, Timeline, SubtitleStyleModal, VideoSyncRef, TimelineRef } from '../components/subtitle-editor';
import { DEFAULT_SUBTITLE_STYLE } from '../components/subtitle-editor/VideoSync';
import { getCurrentVideo, getConfig } from '../services/api';
import { loadEditorSettings, saveEditorSettings, EditorSettings } from '../services/editorSettings';
import type { Video, SubtitleDisplayStyle } from '../types';
import type { SubtitleMergeType } from '../services/subtitleApi';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

export default function SubtitleEditor() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const videoRef = useRef<VideoSyncRef>(null);
  const timelineRef = useRef<TimelineRef>(null);
  const videoDataRef = useRef<Video | null>(null);
  const playUntilRef = useRef<number | null>(null);
  
  // Editor settings
  const [editorSettings, setEditorSettings] = useState<EditorSettings>(() => loadEditorSettings());
  
  // Subtitle style for video preview
  const [subtitleStyle, setSubtitleStyle] = useState<SubtitleDisplayStyle>(DEFAULT_SUBTITLE_STYLE);
  
  // Update editor setting and persist
  const updateEditorSetting = useCallback(<K extends keyof EditorSettings>(key: K, value: EditorSettings[K]) => {
    const updated = saveEditorSettings({ [key]: value });
    setEditorSettings(updated);
  }, []);

  const {
    entries,
    currentTime,
    isPlaying,
    selectedIndex,
    isDirty,
    isLoading,
    isSaving,
    isMerging,
    isRestoring,
    hasBackup,
    loadSubtitles,
    updateEntry,
    addEntry,
    deleteEntry,
    saveToServer,
    mergeVideo,
    restoreToOriginal,
    setCurrentTime,
    setIsPlaying,
    setSelectedIndex,
  } = useSubtitleEditor();

  // Load video info and subtitles on mount
  useEffect(() => {
    const init = async () => {
      const video = await getCurrentVideo();
      videoDataRef.current = video;
      await loadSubtitles();
      
      // Load subtitle style from config
      try {
        const config = await getConfig();
        if (config.subtitle?.style) {
          setSubtitleStyle(config.subtitle.style);
        }
      } catch (error) {
        console.warn('Failed to load subtitle style config, using defaults');
      }
    };
    init();
    
    // Reset the draft restore message flag when component unmounts
    return () => {
      resetDraftRestoreMessageFlag();
    };
  }, [loadSubtitles]);

  // Seek to time (syncs video and timeline)
  const handleSeekTo = useCallback((time: number) => {
    setCurrentTime(time);
    videoRef.current?.seekTo(time);
    timelineRef.current?.seekTo(time);
  }, [setCurrentTime]);

  // Space key to play selected segment (Aegisub-style)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger when typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      
      if (e.code === 'Space' && selectedIndex !== null) {
        e.preventDefault();
        const entry = entries[selectedIndex];
        if (entry) {
          // First stop playback if currently playing
          setIsPlaying(false);
          
          // Set the end time marker only if auto-stop is enabled
          if (editorSettings.autoStopAtSegmentEnd) {
            playUntilRef.current = entry.endTime;
          } else {
            playUntilRef.current = null;
          }
          
          // Seek to start time, then start playing after a short delay
          // to ensure seek completes before playback begins
          handleSeekTo(entry.startTime);
          setTimeout(() => {
            setIsPlaying(true);
          }, 50);
        }
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedIndex, entries, handleSeekTo, setIsPlaying, editorSettings.autoStopAtSegmentEnd]);

  // Stop playback when reaching end time of selected segment
  useEffect(() => {
    // Only check if we have an active playUntil marker and we're playing
    if (playUntilRef.current === null || !isPlaying) return;
    
    const endTime = playUntilRef.current;
    
    // Check if we've reached or passed the end time (with small tolerance)
    // Use a tighter tolerance to avoid overshooting into next segment
    if (currentTime >= endTime - 0.05) {
      // Clear the marker first to prevent re-triggering
      playUntilRef.current = null;
      // Stop playback immediately
      setIsPlaying(false);
      // Sync all components (video, timeline, and state) to the end time
      // Use a small offset before endTime to stay within current segment's visual range
      const seekTime = endTime - 0.01;
      setCurrentTime(seekTime);
      videoRef.current?.seekTo(seekTime);
      timelineRef.current?.seekTo(seekTime);
    }
  }, [currentTime, isPlaying, setIsPlaying, setCurrentTime]);

  // Handle time update from video
  const handleTimeUpdate = useCallback((time: number) => {
    setCurrentTime(time);
  }, [setCurrentTime]);

  // Handle navigation back with unsaved changes warning
  const handleBack = useCallback(() => {
    if (isDirty) {
      Modal.confirm({
        title: t('unsavedChanges') || '有未保存的更改',
        icon: <ExclamationCircleOutlined />,
        content: t('discardChangesConfirm') || '确定要放弃更改并返回吗？',
        okText: t('discard') || '放弃',
        cancelText: t('cancel') || '取消',
        onOk: () => navigate('/'),
      });
    } else {
      navigate('/');
    }
  }, [isDirty, navigate, t]);

  // Handle save
  const handleSave = useCallback(async () => {
    await saveToServer();
  }, [saveToServer]);

  // Handle merge to video - show subtitle type selection modal
  const [mergeModalVisible, setMergeModalVisible] = useState(false);
  const [selectedMergeType, setSelectedMergeType] = useState<SubtitleMergeType>('dual');
  
  // Subtitle style modal
  const [styleModalVisible, setStyleModalVisible] = useState(false);

  const handleMergeClick = useCallback(() => {
    setMergeModalVisible(true);
  }, []);

  const handleMergeConfirm = useCallback(async () => {
    setMergeModalVisible(false);
    const success = await mergeVideo(selectedMergeType);
    if (success) {
      Modal.success({
        title: t('mergeSuccess') || '合并成功',
        content: t('mergeSuccessDesc') || '字幕已成功合并到视频中，即将返回首页查看结果',
        onOk: () => {
          navigate('/');
        },
      });
    }
  }, [mergeVideo, selectedMergeType, t, navigate]);

  // Handle restore to original
  const handleRestore = useCallback(() => {
    Modal.confirm({
      title: t('restoreConfirmTitle') || '还原字幕',
      icon: <ExclamationCircleOutlined />,
      content: t('restoreConfirmContent') || '确定要还原到原始字幕吗？所有编辑将被丢弃。',
      okText: t('confirm') || '确定',
      okButtonProps: { danger: true },
      cancelText: t('cancel') || '取消',
      onOk: async () => {
        await restoreToOriginal();
      },
    });
}, [restoreToOriginal, t]);

  // Handle subtitle style change from modal
  const handleStyleChange = useCallback((style: {
    translation: { fontSize: number; fontColor: string };
    original: { fontSize: number; fontColor: string };
    layout: { marginBottom: number; lineSpacing: number };
  }) => {
    // Update subtitleStyle with camelCase property names (matching backend API response format)
    setSubtitleStyle(prev => ({
      translation: {
        ...prev.translation,
        fontSize: style.translation.fontSize,
        fontColor: style.translation.fontColor,
      },
      original: {
        ...prev.original,
        fontSize: style.original.fontSize,
        fontColor: style.original.fontColor,
      },
      layout: {
        marginBottom: style.layout.marginBottom,
        lineSpacing: style.layout.lineSpacing,
      },
    }));
  }, []);

  if (isLoading) {
    return (
      <Layout className="min-h-screen">
        <div className="flex items-center justify-center h-screen">
          <Spin size="large" tip={t('loading') || '加载中...'} />
        </div>
      </Layout>
    );
  }

  const videoFilename = videoDataRef.current?.filename || '';

  return (
    <Layout className="min-h-screen bg-gradient-to-br from-slate-100 via-slate-50 to-indigo-50/30">
      {/* Header */}
      <Header 
        className="bg-white/80 backdrop-blur-md shadow-sm px-6 flex items-center justify-between border-b border-slate-200/50" 
        style={{ height: 64, lineHeight: 'normal' }}
      >
        <div className="flex items-center gap-4">
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={handleBack}
            className="hover:bg-slate-100 transition-colors"
          >
            {t('back') || '返回'}
          </Button>
          <div className="w-px h-6 bg-slate-200" />
          <Title level={4} className="!mb-0 !mt-0 !leading-none !text-lg bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            {t('subtitleEditor') || '字幕校对编辑器'}
          </Title>
          {isDirty && (
            <Badge 
              status="warning" 
              text={<Text className="text-amber-600 text-sm font-medium">{t('unsaved') || '未保存'}</Text>} 
            />
          )}
        </div>

        <Space size="middle">
          {/* Editor Settings: Auto-stop toggle */}
          <Tooltip title={t('autoStopTooltip') || '按空格键播放时，自动在片段结束处停止'}>
            <div className="flex items-center gap-2 px-3 py-1 bg-slate-50 rounded-lg border border-slate-200">
              <SettingOutlined className="text-slate-400" />
              <Text className="text-xs text-slate-500">{t('autoStop') || '自动停止'}</Text>
              <Switch
                size="small"
                checked={editorSettings.autoStopAtSegmentEnd}
                onChange={(checked) => updateEditorSetting('autoStopAtSegmentEnd', checked)}
              />
            </div>
          </Tooltip>
          {/* Subtitle Style Settings */}
          <Tooltip title={t('subtitleStyleTooltip') || '设置字幕字体大小、颜色等样式'}>
            <Button
              icon={<BgColorsOutlined />}
              onClick={() => setStyleModalVisible(true)}
              className="hover:border-indigo-400 hover:text-indigo-600"
            >
              {t('subtitleStyle') || '样式'}
            </Button>
          </Tooltip>
          <Button
            icon={<UndoOutlined />}
            onClick={handleRestore}
            loading={isRestoring}
            disabled={!hasBackup}
            className="hover:border-amber-400 hover:text-amber-600"
          >
            {t('restoreOriginal') || '还原'}
          </Button>
          <Button
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={isSaving}
            disabled={!isDirty}
            className="hover:border-indigo-400 hover:text-indigo-600"
          >
            {t('saveSubtitles') || '保存字幕'}
          </Button>
          <Button
            type="primary"
            icon={<VideoCameraOutlined />}
            onClick={handleMergeClick}
            loading={isMerging}
            className="bg-gradient-to-r from-indigo-500 to-purple-500 border-0 shadow-md hover:shadow-lg hover:from-indigo-600 hover:to-purple-600"
          >
            {t('mergeToVideo') || '合并到视频'}
          </Button>
        </Space>
      </Header>

      {/* Merge Subtitle Type Selection Modal */}
      <Modal
        title={t('selectSubtitleType') || '选择字幕格式'}
        open={mergeModalVisible}
        onOk={handleMergeConfirm}
        onCancel={() => setMergeModalVisible(false)}
        okText={t('startMerge') || '开始合并'}
        cancelText={t('cancel') || '取消'}
        confirmLoading={isMerging}
      >
        <div className="py-4">
          <Text className="text-gray-600 mb-4 block">
            {t('selectSubtitleTypeDesc') || '选择要合并到视频中的字幕格式：'}
          </Text>
          <Radio.Group 
            value={selectedMergeType} 
            onChange={(e) => setSelectedMergeType(e.target.value)}
            className="flex flex-col gap-3"
          >
            <Radio value="dual">
              <span className="font-medium">{t('dualSubtitle') || '双语字幕（分层）'}</span>
              <Text className="text-gray-400 text-xs block ml-6">
                {t('dualSubtitleDesc') || '原文和译文分别渲染，两行显示'}
              </Text>
            </Radio>
            <Radio value="trans_src">
              <span className="font-medium">{t('transSrcSubtitle') || '双语字幕（译文在上）'}</span>
              <Text className="text-gray-400 text-xs block ml-6">
                {t('transSrcSubtitleDesc') || '译文在上，原文在下，单个字幕文件'}
              </Text>
            </Radio>
            <Radio value="src_trans">
              <span className="font-medium">{t('srcTransSubtitle') || '双语字幕（原文在上）'}</span>
              <Text className="text-gray-400 text-xs block ml-6">
                {t('srcTransSubtitleDesc') || '原文在上，译文在下，单个字幕文件'}
              </Text>
            </Radio>
            <Radio value="trans_only">
              <span className="font-medium">{t('transOnlySubtitle') || '仅译文字幕'}</span>
              <Text className="text-gray-400 text-xs block ml-6">
                {t('transOnlySubtitleDesc') || '只显示翻译后的字幕'}
              </Text>
            </Radio>
            <Radio value="src_only">
              <span className="font-medium">{t('srcOnlySubtitle') || '仅原文字幕'}</span>
              <Text className="text-gray-400 text-xs block ml-6">
                {t('srcOnlySubtitleDesc') || '只显示原始语言的字幕'}
              </Text>
            </Radio>
</Radio.Group>
        </div>
      </Modal>

      {/* Subtitle Style Modal */}
      <SubtitleStyleModal
        open={styleModalVisible}
        onClose={() => setStyleModalVisible(false)}
        onStyleChange={handleStyleChange}
      />

      {/* Main Content */}
      <Content className="p-6">
        <div 
          className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 overflow-hidden border border-slate-200/50" 
          style={{ height: 'calc(100vh - 180px)' }}
        >
          {/* Top: Video + Subtitle List */}
          <div className="flex" style={{ height: 'calc(100% - 180px)' }}>
            {/* Video Player - 40% */}
            <div className="w-2/5 p-5 bg-gradient-to-b from-slate-900 to-slate-800">
{videoFilename ? (
                <VideoSync
                  ref={videoRef}
                  videoFilename={videoFilename}
                  currentTime={currentTime}
                  isPlaying={isPlaying}
                  entries={entries}
                  subtitleStyle={subtitleStyle}
                  onTimeUpdate={handleTimeUpdate}
                  onPlayingChange={setIsPlaying}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-slate-400">
                  <div className="text-center">
                    <VideoCameraOutlined className="text-4xl mb-2 opacity-40" />
                    <div>{t('noVideo') || '没有视频'}</div>
                  </div>
                </div>
              )}
            </div>

            {/* Subtitle List - 60% */}
            <div className="w-3/5 border-l border-slate-200/50 overflow-hidden flex flex-col">
              <div className="px-5 py-3.5 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-1 h-5 rounded-full bg-gradient-to-b from-indigo-500 to-purple-500" />
                  <Text className="text-sm font-semibold text-slate-700">
                    {t('subtitleList') || '字幕列表'}
                  </Text>
                  <span className="px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-600 text-xs font-medium">
                    {entries.length}
                  </span>
                </div>
                <Text className="text-xs text-slate-400">
                  {t('pressSpaceToPlay')}
                </Text>
              </div>
              <div className="flex-1 overflow-hidden">
                <SubtitleList
                  entries={entries}
                  currentTime={currentTime}
                  selectedIndex={selectedIndex}
                  onSelectEntry={setSelectedIndex}
                  onUpdateEntry={updateEntry}
                  onDeleteEntry={deleteEntry}
                  onSeekTo={handleSeekTo}
                />
              </div>
            </div>
          </div>

          {/* Bottom: Timeline */}
          <div className="border-t border-slate-200 p-4 bg-gradient-to-b from-slate-50/50 to-white" style={{ height: 180 }}>
            <Timeline
              ref={timelineRef}
              entries={entries}
              currentTime={currentTime}
              isPlaying={isPlaying}
              selectedIndex={selectedIndex}
              onSeek={handleTimeUpdate}
              onUpdateEntry={updateEntry}
              onAddEntry={addEntry}
              onSelectEntry={setSelectedIndex}
              onPlayingChange={setIsPlaying}
            />
          </div>
        </div>
      </Content>
    </Layout>
  );
}
