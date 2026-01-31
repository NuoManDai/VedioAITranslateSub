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
export async function getSubtitles(): Promise<SubtitleDataResponse> {
  return fetchApi<SubtitleDataResponse>('/subtitles');
}

/**
 * Save edited subtitles to all SRT files
 */
export async function saveSubtitles(
  entries: SubtitleEntry[]
): Promise<SaveSubtitlesResponse> {
  return fetchApi<SaveSubtitlesResponse>('/subtitles', {
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
  subtitleType: SubtitleMergeType = 'dual'
): Promise<MergeVideoResponse> {
  return fetchApi<MergeVideoResponse>('/subtitles/merge-video', {
    method: 'POST',
    body: JSON.stringify({ subtitleType }),
  });
}

/**
 * Get audio stream URL for waveform visualization
 */
export function getAudioStreamUrl(): string {
  return `${API_BASE_URL}/subtitles/audio`;
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
export async function backupSubtitles(): Promise<BackupResponse> {
  return fetchApi<BackupResponse>('/subtitles/backup', {
    method: 'POST',
  });
}

/**
 * Check if subtitle backup exists
 */
export async function hasSubtitleBackup(): Promise<HasBackupResponse> {
  return fetchApi<HasBackupResponse>('/subtitles/has-backup');
}

/**
 * Restore subtitles from backup
 */
export async function restoreSubtitles(): Promise<RestoreResponse> {
  return fetchApi<RestoreResponse>('/subtitles/restore', {
    method: 'POST',
  });
}
