import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { loadArray, saveJSON } from '@/lib/storage';
import type { Widget } from '@/lib/types';

/** Widgety dashboardu. Zatim se ukladaji lokalne v zarizeni (AsyncStorage / localStorage). */
type Ctx = {
  widgets: Widget[];
  loaded: boolean;
  add: (w: Omit<Widget, 'id'>) => void;
  update: (id: string, patch: Partial<Omit<Widget, 'id'>>) => void;
  remove: (id: string) => void;
  move: (id: string, dir: -1 | 1) => void;
};

const KEY = 'homeos.widgets';
const WidgetsContext = createContext<Ctx | null>(null);

function newId() {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`;
}

export function WidgetsProvider({ children }: { children: ReactNode }) {
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    loadArray<Widget>(KEY).then((w) => {
      setWidgets(w);
      setLoaded(true);
    });
  }, []);

  const commit = useCallback((fn: (prev: Widget[]) => Widget[]) => {
    setWidgets((prev) => {
      const next = fn(prev);
      saveJSON(KEY, next);
      return next;
    });
  }, []);

  const value = useMemo<Ctx>(
    () => ({
      widgets,
      loaded,
      add: (w) => commit((prev) => [...prev, { ...w, id: newId() }]),
      update: (id, patch) => commit((prev) => prev.map((w) => (w.id === id ? { ...w, ...patch } : w))),
      remove: (id) => commit((prev) => prev.filter((w) => w.id !== id)),
      move: (id, dir) =>
        commit((prev) => {
          const i = prev.findIndex((w) => w.id === id);
          const j = i + dir;
          if (i < 0 || j < 0 || j >= prev.length) return prev;
          const next = [...prev];
          [next[i], next[j]] = [next[j], next[i]];
          return next;
        }),
    }),
    [widgets, loaded, commit],
  );

  return <WidgetsContext.Provider value={value}>{children}</WidgetsContext.Provider>;
}

export function useWidgets() {
  const ctx = useContext(WidgetsContext);
  if (!ctx) throw new Error('useWidgets mimo WidgetsProvider');
  return ctx;
}
