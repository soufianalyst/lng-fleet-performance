import { useState, useEffect, useCallback, useRef } from 'react';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  autoFetch = true
): UseApiState<T> & { refresh: () => Promise<void> } {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: autoFetch,
    error: null,
  });
  const mountedRef = useRef(true);

  const fetch = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await fetcher();
      if (mountedRef.current) {
        setState({ data, loading: false, error: null });
      }
    } catch (err: unknown) {
      if (mountedRef.current) {
        setState({
          data: null,
          loading: false,
          error: err instanceof Error ? err.message : 'An error occurred',
        });
      }
    }
  }, deps);

  useEffect(() => {
    mountedRef.current = true;
    if (autoFetch) fetch();
    return () => {
      mountedRef.current = false;
    };
  }, [fetch, autoFetch]);

  return { ...state, refresh: fetch };
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs = 30000,
  deps: unknown[] = []
): UseApiState<T> & { refresh: () => Promise<void> } {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: true,
    error: null,
  });
  const intervalRef = useRef<ReturnType<typeof setInterval>>();
  const mountedRef = useRef(true);

  const fetch = useCallback(async () => {
    try {
      const data = await fetcher();
      if (mountedRef.current) {
        setState({ data, loading: false, error: null });
      }
    } catch (err: unknown) {
      if (mountedRef.current) {
        setState({
          data: null,
          loading: false,
          error: err instanceof Error ? err.message : 'An error occurred',
        });
      }
    }
  }, deps);

  useEffect(() => {
    mountedRef.current = true;
    fetch();
    intervalRef.current = setInterval(fetch, intervalMs);
    return () => {
      mountedRef.current = false;
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetch, intervalMs]);

  return { ...state, refresh: fetch };
}
