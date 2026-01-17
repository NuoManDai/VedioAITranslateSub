/**
 * Hook for polling processing status
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import type { ProcessingStatus } from '../types';
import { getProcessingStatus } from '../services/api';

interface UseProcessingStatusOptions {
  enabled?: boolean;
  interval?: number;
  onStatusChange?: (status: ProcessingStatus) => void;
}

interface UseProcessingStatusResult {
  status: ProcessingStatus | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

const DEFAULT_INTERVAL = 2000; // 2 seconds

export function useProcessingStatus(
  options: UseProcessingStatusOptions = {}
): UseProcessingStatusResult {
  const {
    enabled = true,
    interval = DEFAULT_INTERVAL,
    onStatusChange,
  } = options;

  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const onStatusChangeRef = useRef(onStatusChange);

  // Keep callback ref updated
  useEffect(() => {
    onStatusChangeRef.current = onStatusChange;
  }, [onStatusChange]);

  const fetchStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const newStatus = await getProcessingStatus();
      setStatus(newStatus);
      onStatusChangeRef.current?.(newStatus);
      return newStatus;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  // Determine if we should poll
  const shouldPoll = useCallback((currentStatus: ProcessingStatus | null): boolean => {
    if (!currentStatus) return false;
    
    const subtitleRunning = currentStatus.subtitleJob?.status === 'running';
    const dubbingRunning = currentStatus.dubbingJob?.status === 'running';
    
    return subtitleRunning || dubbingRunning;
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
        
        // Continue polling if processing is running
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
