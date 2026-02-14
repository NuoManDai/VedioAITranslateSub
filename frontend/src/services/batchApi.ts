/**
 * Batch API service for batch video processing
 */
import type {
  BatchJob,
  BatchFile,
  BatchFileSettingsUpdate,
} from '../types/batch';

const API_BASE_URL = '/api';

/**
 * Custom error class for API errors
 */
class BatchApiError extends Error {
  public statusCode: number;

  constructor(message: string, statusCode: number) {
    super(message);
    this.name = 'BatchApiError';
    this.statusCode = statusCode;
  }
}

/**
 * Base fetch wrapper with error handling
 */
async function fetchBatchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}/batch${endpoint}`;

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

    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorMessage;
    } catch {
      // Use default error message
    }

    throw new BatchApiError(errorMessage, response.status);
  }

  const contentType = response.headers.get('content-type');
  if (contentType?.includes('application/json')) {
    return response.json();
  }

  return {} as T;
}

// ------------
// Batch Management
// ------------

/**
 * Create a new batch job
 */
export async function createBatch(): Promise<{ jobId: string }> {
  return fetchBatchApi<{ jobId: string }>('/', {
    method: 'POST',
  });
}

/**
 * List all batch jobs
 */
export async function listBatches(): Promise<BatchJob[]> {
  return fetchBatchApi<BatchJob[]>('/');
}

/**
 * Get batch job status with all files
 */
export async function getBatchStatus(jobId: string): Promise<BatchJob> {
  return fetchBatchApi<BatchJob>(`/${jobId}/status`);
}

/**
 * Start batch processing
 */
export async function startBatchProcessing(jobId: string): Promise<BatchJob> {
  return fetchBatchApi<BatchJob>(`/${jobId}/start`, {
    method: 'POST',
  });
}

/**
 * Cancel batch job
 */
export async function cancelBatch(jobId: string): Promise<BatchJob> {
  return fetchBatchApi<BatchJob>(`/${jobId}/cancel`, {
    method: 'POST',
  });
}

// ------------
// File Management
// ------------

/**
 * Register a file to a batch job
 */
export async function registerFile(
  jobId: string,
  filename: string,
  settings?: {
    sourceLang?: string;
    targetLang?: string;
    dubbing?: boolean;
  }
): Promise<BatchFile> {
  return fetchBatchApi<BatchFile>(`/${jobId}/files`, {
    method: 'POST',
    body: JSON.stringify({ filename, ...settings }),
  });
}

/**
 * Upload file content with progress tracking
 */
export async function uploadBatchFile(
  jobId: string,
  fileId: string,
  file: File,
  onProgress?: (progress: number) => void
): Promise<BatchFile> {
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
          reject(new BatchApiError('Invalid response', xhr.status));
        }
      } else {
        let errorMessage = `HTTP error ${xhr.status}`;
        try {
          const errorData = JSON.parse(xhr.responseText);
          errorMessage = errorData.detail || errorMessage;
        } catch {
          // Use default error message
        }
        reject(new BatchApiError(errorMessage, xhr.status));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new BatchApiError('Network error', 0));
    });

    xhr.open('PUT', `${API_BASE_URL}/batch/${jobId}/files/${fileId}/upload`);
    xhr.send(formData);
  });
}

/**
 * Update file settings (source language, target language, dubbing)
 */
export async function updateFileSettings(
  jobId: string,
  fileId: string,
  settings: BatchFileSettingsUpdate
): Promise<BatchFile> {
  return fetchBatchApi<BatchFile>(`/${jobId}/files/${fileId}`, {
    method: 'PATCH',
    body: JSON.stringify(settings),
  });
}

/**
 * Remove a file from a batch job
 */
export async function removeFile(
  jobId: string,
  fileId: string
): Promise<{ message: string }> {
  return fetchBatchApi<{ message: string }>(`/${jobId}/files/${fileId}`, {
    method: 'DELETE',
  });
}
