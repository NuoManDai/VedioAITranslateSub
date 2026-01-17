/**
 * Hook for configuration management
 */
import { useState, useEffect, useCallback } from 'react';
import type { Configuration } from '../types';
import { getConfig, updateConfig } from '../services/api';

interface UseConfigResult {
  config: Configuration | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  update: (updates: Partial<Configuration>) => Promise<Configuration>;
}

export function useConfig(): UseConfigResult {
  const [config, setConfig] = useState<Configuration | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getConfig();
      setConfig(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, []);

  const updateConfiguration = useCallback(async (updates: Partial<Configuration>): Promise<Configuration> => {
    try {
      setLoading(true);
      setError(null);
      const updated = await updateConfig(updates);
      setConfig(updated);
      return updated;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  return {
    config,
    loading,
    error,
    refetch: fetchConfig,
    update: updateConfiguration,
  };
}
