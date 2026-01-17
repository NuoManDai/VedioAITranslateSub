/**
 * Polling service for status updates
 */

type PollCallback<T> = (data: T) => void;
type PollErrorCallback = (error: Error) => void;
type ShouldStopCallback<T> = (data: T) => boolean;

interface PollOptions<T> {
  fetchFn: () => Promise<T>;
  onData: PollCallback<T>;
  onError?: PollErrorCallback;
  shouldStop?: ShouldStopCallback<T>;
  interval?: number;
}

/**
 * Create a polling instance that fetches data at regular intervals
 */
export function createPolling<T>(options: PollOptions<T>) {
  const {
    fetchFn,
    onData,
    onError,
    shouldStop,
    interval = 2000,
  } = options;

  let timerId: number | null = null;
  let isRunning = false;

  const poll = async () => {
    if (!isRunning) return;

    try {
      const data = await fetchFn();
      onData(data);

      if (shouldStop?.(data)) {
        stop();
        return;
      }
    } catch (error) {
      onError?.(error instanceof Error ? error : new Error(String(error)));
    }

    if (isRunning) {
      timerId = window.setTimeout(poll, interval);
    }
  };

  const start = () => {
    if (isRunning) return;
    isRunning = true;
    poll();
  };

  const stop = () => {
    isRunning = false;
    if (timerId !== null) {
      clearTimeout(timerId);
      timerId = null;
    }
  };

  const isActive = () => isRunning;

  return {
    start,
    stop,
    isActive,
  };
}

/**
 * Poll with automatic cleanup on unmount (for use with React useEffect)
 */
export function pollWithCleanup<T>(
  options: PollOptions<T>
): () => void {
  const polling = createPolling(options);
  polling.start();
  return () => polling.stop();
}
