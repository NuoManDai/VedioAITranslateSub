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
 */
export function getVideoStreamUrl(filename: string): string {
  return `${API_BASE_URL}/video/stream/${encodeURIComponent(filename)}`;
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
