import '@/global.css';

import { Platform } from 'react-native';

export const Colors = {
  light: {
    text: '#0B0D12',
    textSecondary: '#5F6673',
    background: '#F4F5F8',
    card: '#FFFFFF',
    cardPressed: '#ECEEF2',
    border: '#E2E5EB',
    accent: '#2F6FED',
    accentText: '#FFFFFF',
    accentSoft: '#E4EDFF',
    danger: '#D93D3D',
    success: '#1F9D57',
    warning: '#C98500',
    chartBand: 'rgba(47,111,237,0.14)',
    grid: '#E6E8EE',
  },
  dark: {
    text: '#F2F4F8',
    textSecondary: '#9AA1AE',
    background: '#0C0E12',
    card: '#171A21',
    cardPressed: '#20242C',
    border: '#272B34',
    accent: '#5B8DFF',
    accentText: '#0C0E12',
    accentSoft: '#1D2840',
    danger: '#FF6B6B',
    success: '#3DD68C',
    warning: '#F5B841',
    chartBand: 'rgba(91,141,255,0.20)',
    grid: '#232731',
  },
} as const;

export type Palette = { [K in keyof typeof Colors.light]: string };
export type ThemeColor = keyof Palette;

export const Fonts = Platform.select({
  ios: { sans: 'system-ui', mono: 'ui-monospace' },
  web: { sans: 'var(--font-display)', mono: 'var(--font-mono)' },
  default: { sans: 'normal', mono: 'monospace' },
});

export const Spacing = { half: 2, one: 4, two: 8, three: 16, four: 24, five: 32, six: 64 } as const;
export const Radius = { sm: 8, md: 14, lg: 20 } as const;
export const MaxContentWidth = 1100;
