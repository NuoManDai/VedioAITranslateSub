/**
 * TypeScript type definitions for VedioAITranslateSub
 */

// Video types
export type VideoSourceType = 'upload' | 'youtube';
export type VideoStatus = 'uploading' | 'downloading' | 'ready' | 'processing' | 'completed' | 'error';

export interface Video {
  id: string;
  filename: string;
  filepath: string;
  sourceType: VideoSourceType;
  youtubeUrl?: string;
  status: VideoStatus;
  fileSize?: number;
  duration?: number;
  createdAt: string;
  errorMessage?: string;
}

// Processing types
export type JobType = 'subtitle' | 'dubbing';
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type StageStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

export interface ProcessingStage {
  name: string;
  displayName: string;
  status: StageStatus;
  progress?: number;
  message?: string;
  startedAt?: string;
  completedAt?: string;
  errorMessage?: string;
}

export interface ProcessingJob {
  id: string;
  videoId: string;
  jobType: JobType;
  status: JobStatus;
  currentStage?: string;
  progress: number;
  stages: ProcessingStage[];
  startedAt?: string;
  completedAt?: string;
  errorMessage?: string;
}

export interface ProcessingStatus {
  video?: Video;
  subtitleJob?: ProcessingJob;
  dubbingJob?: ProcessingJob;
  hasUnfinishedTask: boolean;
  canStartSubtitle: boolean;
  canStartDubbing: boolean;
}

// Log types
export type LogLevel = 'INFO' | 'WARNING' | 'ERROR';

export interface LogEntry {
  id: number;
  timestamp: string;
  level: LogLevel;
  message: string;
  source: string;
  jobId?: string;
  durationMs?: number;
}

export interface LogQueryResponse {
  logs: LogEntry[];
  nextId: number;
  hasMore: boolean;
}

// TTS Config types
export type TTSMethodType = 
  | 'azure_tts' 
  | 'openai_tts' 
  | 'edge_tts' 
  | 'fish_tts' 
  | 'sf_fish_tts'
  | 'gpt_sovits' 
  | 'sf_cosyvoice2'
  | 'f5tts'
  | 'custom_tts';

export interface TTSConfig {
  method: TTSMethodType;
  apiKeyMasked?: string;
  apiBase?: string;
  voice: string;
  region?: string;
  model?: string;
  speechRate: number;
}

// Alias for TTSConfig (same as response format)
export type TTSConfigResponse = TTSConfig;

export interface TTSConfigUpdate {
  method?: TTSMethodType;
  apiKey?: string;
  apiBase?: string;
  voice?: string;
  region?: string;
  model?: string;
  speechRate?: number;
}

export interface AzureVoice {
  name: string;
  displayName: string;
  localName: string;
  shortName: string;
  gender: 'Male' | 'Female';
  locale: string;
  localeName: string;
  styleList?: string[];
  voiceType: string;
}

export interface AzureVoiceListResponse {
  voices: AzureVoice[];
  total: number;
}

// Cleanup types
export interface CleanupResult {
  success: boolean;
  cleanedPaths: string[];
  preservedPaths: string[];
  message: string;
}

// Configuration types
export interface ApiConfig {
  key: string;
  baseUrl: string;
  model: string;
  llmSupportJson: boolean;
}

export interface WhisperConfig {
  method: string;
  whisperXModel: string;
  whisperX302ApiKey?: string;
  elevenlabsApiKey?: string;
  useSegmentMode?: boolean;  // 使用Whisper原生分句而非逐字输出
}

export interface SubtitleConfig {
  maxLength: number;  // 每行字幕最大字符数
  targetMultiplier: number;  // 译文长度权重倍数
}

export interface Configuration {
  displayLanguage: string;
  api: ApiConfig;
  resolution: string;
  sourceLanguage: string;
  targetLanguage: string;
  maxSplitLength: number;  // GPT 分句阈值（token 数）
  timeGapThreshold?: number;  // 时间间隔切分阈值（秒），日语推荐1.0，为空则不启用
  demucs: boolean;
  burnSubtitles: boolean;
  cjkSplit?: boolean;  // CJK 模式：使用 LLM 断句切分字幕
  subtitle?: SubtitleConfig;  // 字幕显示设置
  whisper: WhisperConfig;
  ttsMethod: string;
  // OpenAI TTS
  openaiTtsApiKey?: string;
  openaiVoice: string;
  // Azure TTS
  azureKey?: string;
  azureRegion?: string;
  azureVoice: string;
  // Fish TTS
  fishTtsApiKey?: string;
  fishTtsCharacter: string;
  fishTtsCharacterIdDict?: Record<string, string>;
  // SiliconFlow Fish TTS
  sfFishTtsApiKey?: string;
  sfFishTtsMode?: string;
  sfFishTtsVoice?: string;
  // GPT-SoVITS
  sovitsCharacter: string;
  gptSovitsReferMode: number;
  // Edge TTS
  edgeTtsVoice: string;
  // SiliconFlow CosyVoice2
  sfCosyvoice2ApiKey?: string;
  // F5-TTS
  f5ttsApiKey?: string;
  // Custom TTS
  customTtsApiKey?: string;
  customTtsBaseUrl?: string;
  customTtsModel?: string;
  // Other
  sfApiKey?: string;
  ytbCookiesPath?: string;
  httpProxy?: string;
  hfMirror?: string;
}

// API Request/Response types
export interface YouTubeDownloadRequest {
  url: string;
  resolution?: '360' | '1080' | 'best';
}

export interface ApiValidateRequest {
  key: string;
  baseUrl: string;
  model: string;
}

export interface ApiValidateResponse {
  valid: boolean;
  message: string;
}

export interface ApiError {
  detail: string;
  code?: string;
}

export interface MessageResponse {
  message: string;
}

// Utility types for API responses
export type ApiResponse<T> = {
  data?: T;
  error?: ApiError;
};

// Language options for UI display
export const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'zh-CN', name: 'Chinese (Simplified)', nativeName: '简体中文' },
  { code: 'zh-HK', name: 'Chinese (Traditional)', nativeName: '繁體中文' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語' },
  { code: 'es', name: 'Spanish', nativeName: 'Español' },
  { code: 'ru', name: 'Russian', nativeName: 'Русский' },
  { code: 'fr', name: 'French', nativeName: 'Français' },
] as const;

export type SupportedLanguageCode = typeof SUPPORTED_LANGUAGES[number]['code'];

// Source language options (ISO 639-1 codes for Whisper recognition)
export const SOURCE_LANGUAGES = [
  { value: 'auto', label: 'Auto Detect / 自动检测' },
  { value: 'en', label: 'English' },
  { value: 'zh', label: '中文 (Chinese)' },
  { value: 'ja', label: '日本語 (Japanese)' },
  { value: 'ko', label: '한국어 (Korean)' },
  { value: 'es', label: 'Español (Spanish)' },
  { value: 'fr', label: 'Français (French)' },
  { value: 'de', label: 'Deutsch (German)' },
  { value: 'it', label: 'Italiano (Italian)' },
  { value: 'pt', label: 'Português (Portuguese)' },
  { value: 'ru', label: 'Русский (Russian)' },
  { value: 'ar', label: 'العربية (Arabic)' },
  { value: 'hi', label: 'हिन्दी (Hindi)' },
  { value: 'th', label: 'ไทย (Thai)' },
  { value: 'vi', label: 'Tiếng Việt (Vietnamese)' },
  { value: 'id', label: 'Bahasa Indonesia' },
  { value: 'tr', label: 'Türkçe (Turkish)' },
  { value: 'pl', label: 'Polski (Polish)' },
  { value: 'nl', label: 'Nederlands (Dutch)' },
  { value: 'uk', label: 'Українська (Ukrainian)' },
] as const;

export type SourceLanguageCode = typeof SOURCE_LANGUAGES[number]['value'];

// Target language options (natural language names for translation prompts)
export const TARGET_LANGUAGES = [
  { value: '简体中文', label: '简体中文 (Simplified Chinese)' },
  { value: '繁體中文', label: '繁體中文 (Traditional Chinese)' },
  { value: 'English', label: 'English' },
  { value: '日本語', label: '日本語 (Japanese)' },
  { value: '한국어', label: '한국어 (Korean)' },
  { value: 'Español', label: 'Español (Spanish)' },
  { value: 'Français', label: 'Français (French)' },
  { value: 'Deutsch', label: 'Deutsch (German)' },
  { value: 'Italiano', label: 'Italiano (Italian)' },
  { value: 'Português', label: 'Português (Portuguese)' },
  { value: 'Русский', label: 'Русский (Russian)' },
  { value: 'العربية', label: 'العربية (Arabic)' },
  { value: 'हिन्दी', label: 'हिन्दी (Hindi)' },
  { value: 'ไทย', label: 'ไทย (Thai)' },
  { value: 'Tiếng Việt', label: 'Tiếng Việt (Vietnamese)' },
  { value: 'Bahasa Indonesia', label: 'Bahasa Indonesia' },
  { value: 'Türkçe', label: 'Türkçe (Turkish)' },
  { value: 'Polski', label: 'Polski (Polish)' },
  { value: 'Nederlands', label: 'Nederlands (Dutch)' },
  { value: 'Українська', label: 'Українська (Ukrainian)' },
] as const;

export type TargetLanguage = typeof TARGET_LANGUAGES[number]['value'];

// TTS methods
export const TTS_METHODS = [
  { value: 'azure_tts', label: 'Azure TTS' },
  { value: 'openai_tts', label: 'OpenAI TTS' },
  { value: 'fish_tts', label: 'Fish TTS' },
  { value: 'sf_fish_tts', label: 'SiliconFlow FishTTS' },
  { value: 'edge_tts', label: 'Edge TTS (Free)' },
  { value: 'gpt_sovits', label: 'GPT-SoVITS' },
  { value: 'sf_cosyvoice2', label: 'SiliconFlow CosyVoice2' },
  { value: 'f5tts', label: 'F5-TTS' },
  { value: 'custom_tts', label: 'Custom TTS' },
] as const;

export type TTSMethod = typeof TTS_METHODS[number]['value'];

// Whisper methods - values must match core code whisper.runtime values: whisper, whisperx_local, cloud, elevenlabs
export const WHISPER_METHODS = [
  { value: 'whisper', label: 'Faster-Whisper Native (Recommended)' },
  { value: 'whisperx_local', label: 'WhisperX (VAD + Align)' },
  { value: 'cloud', label: 'WhisperX Cloud (302.ai)' },
  { value: 'elevenlabs', label: 'ElevenLabs' },
] as const;

export type WhisperMethod = typeof WHISPER_METHODS[number]['value'];

// Whisper models for local mode
export const WHISPER_MODELS = [
  { value: 'large-v3', label: 'large-v3 (Best Quality)' },
  { value: 'medium', label: 'medium (More Punctuation)' },
] as const;

export type WhisperModel = typeof WHISPER_MODELS[number]['value'];

// ============ Subtitle Editor Types ============

export interface SubtitleEntry {
  index: number;
  startTime: number;  // seconds
  endTime: number;    // seconds
  text: string;       // Translation text
  originalText?: string;  // Original text
}

export interface SubtitleDataResponse {
  entries: SubtitleEntry[];
  files: Record<string, { path: string; exists: boolean }>;
  totalCount: number;
}

export interface SaveSubtitlesResponse {
  success: boolean;
  savedFiles: string[];
  entryCount: number;
}

export interface MergeVideoResponse {
  success: boolean;
  outputVideo?: string;
  exists?: boolean;
  error?: string;
}
