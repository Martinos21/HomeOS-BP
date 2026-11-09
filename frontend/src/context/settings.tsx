import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Platform, useColorScheme } from 'react-native';

import { Colors, type Palette } from '@/constants/theme';
import type { ApiConfig } from '@/lib/api';
import { loadJSON, saveJSON } from '@/lib/storage';

export type ThemeMode = 'system' | 'light' | 'dark';

type Settings = { themeMode: ThemeMode; apiUrl: string; apiKey: string };

type Ctx = Settings & {
  loaded: boolean;
  scheme: 'light' | 'dark';
  colors: Palette;
  api: ApiConfig;
  update: (patch: Partial<Settings>) => void;
};

const KEY = 'homeos.settings';

/** Na webu je frontend typicky servirovany ze stejneho Pi -> API na stejnem hostu, port 8080. */
function defaultUrl() {
  if (Platform.OS === 'web' && typeof window !== 'undefined' && window.location?.hostname) {
    return `${window.location.protocol}//${window.location.hostname}:8080`;
  }
  return '';
}

const SettingsContext = createContext<Ctx | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const system = useColorScheme();
  const [loaded, setLoaded] = useState(false);
  const [settings, setSettings] = useState<Settings>({ themeMode: 'system', apiUrl: '', apiKey: '' });

  useEffect(() => {
    loadJSON<Settings>(KEY, { themeMode: 'system', apiUrl: defaultUrl(), apiKey: '' }).then((s) => {
      setSettings(s);
      setLoaded(true);
    });
  }, []);

  const update = useCallback((patch: Partial<Settings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      saveJSON(KEY, next);
      return next;
    });
  }, []);

  const value = useMemo<Ctx>(() => {
    const scheme = settings.themeMode === 'system' ? (system === 'dark' ? 'dark' : 'light') : settings.themeMode;
    return {
      ...settings,
      loaded,
      scheme,
      colors: Colors[scheme],
      api: { url: settings.apiUrl.trim(), key: settings.apiKey.trim() },
      update,
    };
  }, [settings, loaded, system, update]);

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('useSettings mimo SettingsProvider');
  return ctx;
}

export function useColors() {
  return useSettings().colors;
}
