/**
 * API service for communicating with the backend
 */
import type {
  Video,
  ProcessingStatus,
  ProcessingJob,
  Configuration,
  YouTubeDownloadRequest,
  ApiValidateRequest,
  ApiValidateResponse,
  ApiError,
  MessageResponse,
} from '../types';

const API_BASE_URL = '/api';

/**
 * Custom error class for API errors
 */
export class ApiRequestError extends Error {
  public statusCode: number;
  public errorCode?: string;

  constructor(message: string, statusCode: number, errorCode?: string) {
    super(message);
    this.name = 'ApiRequestError';
    this.statusCode = statusCode;
    this.errorCode = errorCode;
  }
}

/**
 * Base fetch wrapper with error handling
 */
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  };

  // Don't set Content-Type for FormData
  if (options.body instanceof FormData) {
    delete (defaultHeaders as Record<string, string>)['Content-Type'];
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorMessage = `HTTP error ${response.status}`;
    let errorCode: string | undefined;

    try {
      const errorData: ApiError = await response.json();
      errorMessage = errorData.detail || errorMessage;
      errorCode = errorData.code;
    } catch {
      // Use default error message
    }

    throw new ApiRequestError(errorMessage, response.status, errorCode);
  }

  // Handle empty responses
  const contentType = response.headers.get('content-type');
  if (contentType?.includes('application/json')) {
    return response.json();
  }

  return {} as T;
}

// ============ Video API ============

/**
 * Upload a video file
 */
export async function uploadVideo(
  file: File,
  onProgress?: (progress: number) => void
): Promise<Video> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', file);

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        const progress = Math.round((event.loaded / event.total) * 100);
        onProgress(progress);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          resolve(response);
        } catch {
          reject(new ApiRequestError('Invalid response', xhr.status));
        }
      } else {
        let errorMessage = `HTTP error ${xhr.status}`;
        try {
          const errorData = JSON.parse(xhr.responseText);
          errorMessage = errorData.detail || errorMessage;
        } catch {
          // Use default error message
        }
        reject(new ApiRequestError(errorMessage, xhr.status));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new ApiRequestError('Network error', 0));
    });

    xhr.open('POST', `${API_BASE_URL}/video/upload`);
    xhr.send(formData);
  });
}

/**
 * Download video from YouTube
 */
export async function downloadYouTube(
  request: YouTubeDownloadRequest
): Promise<Video> {
  return fetchApi<Video>('/video/youtube', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Get current video information
 */
export async function getCurrentVideo(): Promise<Video | null> {
  try {
    return await fetchApi<Video>('/video/current');
  } catch (error) {
    if (error instanceof ApiRequestError && error.statusCode === 404) {
      return null;
    }
    throw error;
  }
}

/**
 * Delete current video
 */
export async function deleteCurrentVideo(): Promise<MessageResponse> {
  return fetchApi<MessageResponse>('/video/current', {
    method: 'DELETE',
  });
}

/**
 * Get video stream URL
 * @param filename - Video filename
 * @param withSubtitle - Whether to get the subtitled version if available
 */
export function getVideoStreamUrl(filename: string, withSubtitle: boolean = false): string {
  const url = `${API_BASE_URL}/video/stream/${encodeURIComponent(filename)}`;
  return withSubtitle ? `${url}?with_subtitle=true` : url;
}

// ============ Processing API ============

/**
 * Start subtitle processing
 */
export async function startSubtitleProcessing(): Promise<ProcessingJob> {
  return fetchApi<ProcessingJob>('/processing/subtitle/start', {
    method: 'POST',
  });
}

/**
 * Start dubbing processing
 */
export async function startDubbingProcessing(): Promise<ProcessingJob> {
  return fetchApi<ProcessingJob>('/processing/dubbing/start', {
    method: 'POST',
  });
}

/**
 * Get current processing status
 */
export async function getProcessingStatus(): Promise<ProcessingStatus> {
  return fetchApi<ProcessingStatus>('/processing/status');
}

/**
 * Cancel current processing
 */
export async function cancelProcessing(): Promise<MessageResponse> {
  return fetchApi<MessageResponse>('/processing/cancel', {
    method: 'POST',
  });
}

/**
 * Get SRT download URL
 */
export function getSrtDownloadUrl(): string {
  return `${API_BASE_URL}/processing/download/srt`;
}

// ============ Config API ============

/**
 * Get current configuration
 */
export async function getConfig(): Promise<Configuration> {
  return fetchApi<Configuration>('/config');
}

/**
 * Update configuration
 */
export async function updateConfig(
  config: Partial<Configuration>
): Promise<Configuration> {
  return fetchApi<Configuration>('/config', {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

/**
 * Validate API key
 */
export async function validateApiKey(
  request: ApiValidateRequest
): Promise<ApiValidateResponse> {
  return fetchApi<ApiValidateResponse>('/config/validate-api', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// ============ TTS Config API ============

import type { TTSConfigResponse, TTSConfigUpdate, AzureVoiceListResponse } from '../types';

/**
 * Get TTS configuration (API keys are masked)
 */
export async function getTTSConfig(): Promise<TTSConfigResponse> {
  return fetchApi<TTSConfigResponse>('/config/tts');
}

/**
 * Update TTS configuration
 */
export async function updateTTSConfig(update: TTSConfigUpdate): Promise<TTSConfigResponse> {
  return fetchApi<TTSConfigResponse>('/config/tts', {
    method: 'PUT',
    body: JSON.stringify(update),
  });
}

/**
 * Get Azure TTS preset voice list
 * No API key required - returns curated list of common voices
 */
export async function getAzureVoices(): Promise<AzureVoiceListResponse> {
  return fetchApi<AzureVoiceListResponse>('/config/tts/azure/voices');
}

// ============ Cleanup API ============

import type { CleanupResult } from '../types';

/**
 * Cleanup subtitle processing files
 */
export async function cleanupSubtitleFiles(): Promise<CleanupResult> {
  return fetchApi<CleanupResult>('/processing/cleanup/subtitle', {
    method: 'POST',
  });
}

/**
 * Cleanup dubbing processing files
 */
export async function cleanupDubbingFiles(): Promise<CleanupResult> {
  return fetchApi<CleanupResult>('/processing/cleanup/dubbing', {
    method: 'POST',
  });
}

/**
 * Cleanup ALL processing files and restart from beginning
 */
export async function cleanupAllFiles(): Promise<CleanupResult> {
  return fetchApi<CleanupResult>('/processing/cleanup/all', {
    method: 'POST',
  });
}

// ============ Logs API ============

import type { LogQueryResponse, LogLevel } from '../types';

export interface LogQueryParams {
  lastId?: number;
  limit?: number;
  level?: LogLevel;
  source?: string;
}

/**
 * Get logs with optional filtering
 */
export async function getLogs(params: LogQueryParams = {}): Promise<LogQueryResponse> {
  const searchParams = new URLSearchParams();
  if (params.lastId !== undefined) searchParams.append('last_id', params.lastId.toString());
  if (params.limit !== undefined) searchParams.append('limit', params.limit.toString());
  if (params.level) searchParams.append('level', params.level);
  if (params.source) searchParams.append('source', params.source);
  
  const query = searchParams.toString();
  return fetchApi<LogQueryResponse>(`/logs${query ? `?${query}` : ''}`);
}

/**
 * Clear all logs
 */
export async function clearLogs(): Promise<void> {
  await fetchApi<void>('/logs', { method: 'DELETE' });
}

// ============ Files API ============

export interface StageOutputFile {
  name: string;
  path: string;
  type: string;
  description: string;
  exists: boolean;
  size: number | null;
}

export interface StageFilesResponse {
  stage: string;
  files: StageOutputFile[];
}

export interface FilePreviewResponse {
  name: string;
  path: string;
  type: string;
  content: string | null;
  size: number;
  previewAvailable: boolean;
  error: string | null;
}

export interface FolderFile {
  name: string;
  path: string;
  type: string;
  isDir: boolean;
  size: number;
}

export interface FolderListResponse {
  folder: string;
  files: FolderFile[];
}

/**
 * Get output files for a processing stage
 */
export async function getStageFiles(stageName: string): Promise<StageFilesResponse> {
  return fetchApi<StageFilesResponse>(`/files/stage/${stageName}`);
}

/**
 * Preview a file's content
 */
export async function previewFile(path: string, maxLines: number = 500): Promise<FilePreviewResponse> {
  const params = new URLSearchParams({ path, max_lines: maxLines.toString() });
  return fetchApi<FilePreviewResponse>(`/files/preview?${params}`);
}

/**
 * Get file download URL
 */
export function getFileDownloadUrl(path: string): string {
  return `${API_BASE_URL}/files/download?path=${encodeURIComponent(path)}`;
}

/**
 * List folder contents
 */
export async function listFolder(path: string): Promise<FolderListResponse> {
  const params = new URLSearchParams({ path });
  return fetchApi<FolderListResponse>(`/files/folder?${params}`);
}
