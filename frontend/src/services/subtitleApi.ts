/**
 * Subtitle API Service - Subtitle editing endpoints
 */
import type {
  SubtitleEntry,
  SubtitleDataResponse,
  SaveSubtitlesResponse,
  MergeVideoResponse,
} from '../types';

const API_BASE_URL = '/api';

/**
 * Custom error class for API errors
 */
class ApiRequestError extends Error {
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
      const errorData = await response.json();
      errorMessage = errorData.detail || errorMessage;
      errorCode = errorData.code;
    } catch {
      // Use default error message
    }

    throw new ApiRequestError(errorMessage, response.status, errorCode);
  }

  const contentType = response.headers.get('content-type');
  if (contentType?.includes('application/json')) {
    return response.json();
  }

  return {} as T;
}

// ============ Subtitle API ============

/**
 * Get all subtitles for editing
 */
export async function getSubtitles(videoId?: string): Promise<SubtitleDataResponse> {
  const params = videoId ? `?video_id=${videoId}` : '';
  return fetchApi<SubtitleDataResponse>(`/subtitles${params}`);
}

/**
 * Save edited subtitles to all SRT files
 */
export async function saveSubtitles(
  entries: SubtitleEntry[],
  videoId?: string
): Promise<SaveSubtitlesResponse> {
  const params = videoId ? `?video_id=${videoId}` : '';
  return fetchApi<SaveSubtitlesResponse>(`/subtitles${params}`, {
    method: 'PUT',
    body: JSON.stringify({ entries }),
  });
}

/**
 * Subtitle type options for merging video
 */
export type SubtitleMergeType = 'dual' | 'trans_only' | 'src_only' | 'trans_src' | 'src_trans';

/**
 * Merge subtitles into video
 */
export async function mergeSubtitlesToVideo(
  subtitleType: SubtitleMergeType = 'dual',
  videoId?: string
): Promise<MergeVideoResponse> {
  const params = videoId ? `?video_id=${videoId}` : '';
  return fetchApi<MergeVideoResponse>(`/subtitles/merge-video${params}`, {
    method: 'POST',
    body: JSON.stringify({ subtitleType }),
  });
}

/**
 * Get audio stream URL for waveform visualization
 */
export function getAudioStreamUrl(videoId?: string): string {
  const params = videoId ? `?video_id=${videoId}` : '';
  return `${API_BASE_URL}/subtitles/audio${params}`;
}

// ============ Backup & Restore API ============

export interface BackupResponse {
  success: boolean;
  backedUp: string[];
  skipped: string[];
  backupDir?: string;
}

export interface RestoreResponse {
  success: boolean;
  restored: string[];
  message?: string;
  error?: string;
}

export interface HasBackupResponse {
  hasBackup: boolean;
}

/**
 * Backup current subtitles (before user edits)
 */
export async function backupSubtitles(videoId?: string): Promise<BackupResponse> {
  const params = videoId ? `?video_id=${videoId}` : '';
  return fetchApi<BackupResponse>(`/subtitles/backup${params}`, {
    method: 'POST',
  });
}

/**
 * Check if subtitle backup exists
 */
export async function hasSubtitleBackup(videoId?: string): Promise<HasBackupResponse> {
  const params = videoId ? `?video_id=${videoId}` : '';
  return fetchApi<HasBackupResponse>(`/subtitles/has-backup${params}`);
}

/**
 * Restore subtitles from backup
 */
export async function restoreSubtitles(videoId?: string): Promise<RestoreResponse> {
  const params = videoId ? `?video_id=${videoId}` : '';
  return fetchApi<RestoreResponse>(`/subtitles/restore${params}`, {
    method: 'POST',
  });
}
