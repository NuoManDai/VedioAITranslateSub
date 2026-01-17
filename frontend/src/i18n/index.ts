/**
 * i18n configuration using react-i18next
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translation files
import en from './locales/en.json';
import zhCN from './locales/zh-CN.json';
import zhHK from './locales/zh-HK.json';
import ja from './locales/ja.json';
import es from './locales/es.json';
import ru from './locales/ru.json';
import fr from './locales/fr.json';

// Custom translations for UI elements not in the original translations
const customTranslations = {
  en: {
    appName: 'VedioAITranslateSub',
    home: 'Home',
    settings: 'Settings',
    videoUpload: 'Upload Video',
    youtubeDownload: 'Download from YouTube',
    dragOrClick: 'Drag and drop video file here, or click to select',
    supportedFormats: 'Supported formats: MP4, AVI, MKV, MOV, WebM',
    enterYoutubeUrl: 'Enter YouTube URL',
    download: 'Download',
    downloading: 'Downloading...',
    uploading: 'Uploading...',
    processing: 'Processing',
    subtitleProcessing: 'Subtitle Processing',
    dubbingProcessing: 'Dubbing Processing',
    startSubtitle: 'Start Subtitle Processing',
    startDubbing: 'Start Dubbing',
    cancel: 'Cancel',
    download_srt: 'Download SRT',
    completed: 'Completed',
    failed: 'Failed',
    pending: 'Pending',
    running: 'Running',
    noVideo: 'No video loaded',
    deleteVideo: 'Delete Video',
    confirmDelete: 'Are you sure you want to delete this video?',
    yes: 'Yes',
    no: 'No',
    error: 'Error',
    success: 'Success',
    saveSettings: 'Save Settings',
    testApi: 'Test API',
    language: 'Language',
    recoveryPrompt: 'Unfinished task detected. Continue or start over?',
    continueTask: 'Continue',
    startOver: 'Start Over',
  },
  'zh-CN': {
    appName: 'VedioAITranslateSub',
    home: '首页',
    settings: '设置',
    videoUpload: '上传视频',
    youtubeDownload: '从 YouTube 下载',
    dragOrClick: '拖拽视频文件到此处，或点击选择',
    supportedFormats: '支持格式：MP4、AVI、MKV、MOV、WebM',
    enterYoutubeUrl: '输入 YouTube 链接',
    download: '下载',
    downloading: '下载中...',
    uploading: '上传中...',
    processing: '处理中',
    subtitleProcessing: '字幕处理',
    dubbingProcessing: '配音处理',
    startSubtitle: '开始字幕处理',
    startDubbing: '开始配音',
    cancel: '取消',
    download_srt: '下载字幕',
    completed: '已完成',
    failed: '失败',
    pending: '等待中',
    running: '处理中',
    noVideo: '未加载视频',
    deleteVideo: '删除视频',
    confirmDelete: '确定要删除此视频吗？',
    yes: '是',
    no: '否',
    error: '错误',
    success: '成功',
    saveSettings: '保存设置',
    testApi: '测试 API',
    language: '语言',
    recoveryPrompt: '检测到未完成的任务。是否继续？',
    continueTask: '继续',
    startOver: '重新开始',
  },
};

// Merge custom translations with original translations
const resources = {
  en: { translation: { ...en, ...customTranslations.en } },
  'zh-CN': { translation: { ...zhCN, ...customTranslations['zh-CN'] } },
  'zh-HK': { translation: { ...zhHK, ...customTranslations.en } },
  ja: { translation: { ...ja, ...customTranslations.en } },
  es: { translation: { ...es, ...customTranslations.en } },
  ru: { translation: { ...ru, ...customTranslations.en } },
  fr: { translation: { ...fr, ...customTranslations.en } },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    debug: import.meta.env.DEV,
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },
  });

export default i18n;

/**
 * Change the current language
 */
export const changeLanguage = (lng: string): Promise<void> => {
  return new Promise((resolve) => {
    i18n.changeLanguage(lng, () => {
      localStorage.setItem('i18nextLng', lng);
      resolve();
    });
  });
};

/**
 * Get the current language
 */
export const getCurrentLanguage = (): string => {
  return i18n.language || 'en';
};
