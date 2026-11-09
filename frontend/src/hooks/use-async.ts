import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Jednoduche nacitani dat: { data, error, loading, reload }.
 * `refreshMs` = automaticke obnovovani (dashboard), 0 = vypnuto.
 */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[], refreshMs = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps);

  const reload = useCallback(async () => {
    const id = ++seq.current;
    setLoading(true);
    try {
      const res = await run();
      if (id === seq.current) {
        setData(res);
        setError(null);
      }
    } catch (e) {
      if (id === seq.current) setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (id === seq.current) setLoading(false);
    }
  }, [run]);

  useEffect(() => {
    reload();
    if (!refreshMs) return;
    const t = setInterval(reload, refreshMs);
    return () => clearInterval(t);
  }, [reload, refreshMs]);

  return { data, error, loading, reload };
}
