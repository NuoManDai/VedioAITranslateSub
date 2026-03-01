/**
 * Hook for polling transcode status
 */
import { useState, useEffect, useCallback } from 'react';
import type { TranscodeStatus } from '../types';
import { getTranscodeStatus } from '../services/api';

interface UseTranscodeStatusOptions {
  videoId: string;
  enabled?: boolean;
  interval?: number;
}

interface UseTranscodeStatusResult {
  status: TranscodeStatus | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

const DEFAULT_INTERVAL = 3000; // 3 seconds

export function useTranscodeStatus(
  options: UseTranscodeStatusOptions
): UseTranscodeStatusResult {
  const {
    videoId,
    enabled = true,
    interval = DEFAULT_INTERVAL,
  } = options;

  const [status, setStatus] = useState<TranscodeStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const newStatus = await getTranscodeStatus(videoId);
      setStatus(newStatus);
      return newStatus;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [videoId]);

  // Determine if we should continue polling
  const shouldPoll = useCallback((currentStatus: TranscodeStatus | null): boolean => {
    if (!currentStatus) return false;
    return currentStatus.status === 'pending' || currentStatus.status === 'transcoding';
  }, []);

  // Polling effect
  useEffect(() => {
    if (!enabled) return;

    let timeoutId: number | null = null;
    let mounted = true;

    const poll = async () => {
      if (!mounted) return;

      try {
        const newStatus = await fetchStatus();
        
        // Continue polling if transcode is running
        if (mounted && shouldPoll(newStatus)) {
          timeoutId = window.setTimeout(poll, interval);
        }
      } catch {
        // Retry on error after interval
        if (mounted) {
          timeoutId = window.setTimeout(poll, interval);
        }
      }
    };

    // Initial fetch
    poll();

    return () => {
      mounted = false;
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
    };
  }, [enabled, interval, fetchStatus, shouldPoll]);

  const refetch = useCallback(async () => {
    await fetchStatus();
  }, [fetchStatus]);

  return {
    status,
    loading,
    error,
    refetch,
  };
}
