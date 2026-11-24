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
  /** Vrati adresu a klic na vychozi hodnoty (localhost, bez klice). */
  resetConnection: () => void;
  defaults: { apiUrl: string; apiKey: string };
  isWeb: boolean
};

const KEY = 'homeos.settings';

/**
 * Vychozi pripojeni: backend na stejnem zarizeni. Z localhostu backend klic
 * nevyzaduje, klic se zadava jen pro pristup odjinud (mobil v siti).
 */
export const IS_WEB = Platform.OS === 'web';
export const WEB_API_URL = 'http://192.168.68.102:8080';

const DEFAULTS = { apiUrl: '', apiKey: '' };

const SettingsContext = createContext<Ctx | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const system = useColorScheme();
  const [loaded, setLoaded] = useState(false);
  const [settings, setSettings] = useState<Settings>({ themeMode: 'system', ...DEFAULTS });

  useEffect(() => {
    loadJSON<Settings>(KEY, { themeMode: 'system', ...DEFAULTS }).then((s) => {
      const apiUrl = !IS_WEB && s.apiUrl === WEB_API_URL ? '' : s.apiUrl;
      setSettings({ ...s, apiUrl });
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
      api: IS_WEB
        ? { url: WEB_API_URL, key: settings.apiKey.trim() }
        : { url: settings.apiUrl.trim(), key: settings.apiKey.trim() },
      update,
      isWeb: IS_WEB,
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
