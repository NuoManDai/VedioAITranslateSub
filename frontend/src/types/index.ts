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
}

export interface Configuration {
  displayLanguage: string;
  api: ApiConfig;
  resolution: string;
  sourceLanguage: string;
  targetLanguage: string;
  demucs: boolean;
  burnSubtitles: boolean;
  whisper: WhisperConfig;
  ttsMethod: string;
  openaiTtsApiKey?: string;
  openaiVoice: string;
  azureKey?: string;
  azureRegion?: string;
  azureVoice: string;
  fishTtsApiKey?: string;
  fishTtsCharacter: string;
  sfApiKey?: string;
  sovitsCharacter: string;
  gptSovitsReferMode: number;
  edgeTtsVoice: string;
  customTtsApiKey?: string;
  customTtsBaseUrl?: string;
  customTtsModel?: string;
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
  { value: 'openai_tts', label: 'OpenAI TTS' },
  { value: 'azure_tts', label: 'Azure TTS' },
  { value: 'edge_tts', label: 'Edge TTS (Free)' },
  { value: 'fish_tts', label: 'Fish TTS' },
  { value: 'gpt_sovits', label: 'GPT-SoVITS' },
  { value: 'sf_cosyvoice2', label: 'SiliconFlow CosyVoice2' },
  { value: 'sf_fishtts', label: 'SiliconFlow FishTTS' },
  { value: 'custom_tts', label: 'Custom TTS' },
] as const;

export type TTSMethod = typeof TTS_METHODS[number]['value'];

// Whisper methods - values must match core code whisper.runtime values: local, cloud, elevenlabs
export const WHISPER_METHODS = [
  { value: 'local', label: 'WhisperX Local' },
  { value: 'cloud', label: 'WhisperX Cloud (302.ai)' },
  { value: 'elevenlabs', label: 'ElevenLabs' },
] as const;

export type WhisperMethod = typeof WHISPER_METHODS[number]['value'];
