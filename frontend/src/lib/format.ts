import type { Range, Source, Stat } from './types';

/** Popisky a jednotky znamych hodnot. Neznama hodnota se ukaze tak, jak je v DB. */
const COLUMNS: Record<string, { label: string; unit: string; digits: number; icon: string }> = {
  temperature: { label: 'Teplota', unit: '°C', digits: 1, icon: 'thermometer-outline' },
  humidity: { label: 'Vlhkost', unit: '%', digits: 0, icon: 'water-outline' },
  co2: { label: 'CO₂', unit: 'ppm', digits: 0, icon: 'leaf-outline' },
  motion: { label: 'Pohyb', unit: '', digits: 2, icon: 'walk-outline' },
};

const SOLAR: Record<string, { label: string; unit: string; digits: number; icon: string }> = {
  'em-consumed-graph': { label: 'Odběr ze sítě', unit: 'kWh', digits: 2, icon: 'flash-outline' },
  'em-overflow-graph': { label: 'Přetok do sítě', unit: 'kWh', digits: 2, icon: 'arrow-up-circle-outline' },
  'pl-power-graph': { label: 'Výkon', unit: '', digits: 1, icon: 'speedometer-outline' },
  'pv-battery-soc-graph': { label: 'Baterie', unit: '%', digits: 0, icon: 'battery-half-outline' },
};

export const STAT_LABEL: Record<Stat, string> = {
  last: 'Poslední',
  avg: 'Průměr',
  min: 'Minimum',
  max: 'Maximum',
};

export const RANGE_LABEL: Record<Range, string> = {
  '1h': '1 h',
  '24h': '24 h',
  '7d': '7 dní',
  '30d': '30 dní',
  all: 'Vše',
};

export function prettyName(name: string) {
  const s = name.replace(/[_-]+/g, ' ').trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function columnLabel(column: string) {
  return COLUMNS[column]?.label ?? prettyName(column);
}

export function solarColumnLabel(column: string) {
  return column === 'delta' ? 'Změna za interval' : 'Hodnota';
}

export function describeSource(s: Source) {
  if (s.kind === 'device') {
    const c = COLUMNS[s.column];
    return {
      group: prettyName(s.name),
      label: columnLabel(s.column),
      unit: c?.unit ?? '',
      digits: c?.digits ?? 2,
      icon: c?.icon ?? 'pulse-outline',
    };
  }
  const m = SOLAR[s.metric];
  return {
    group: 'Fotovoltaika',
    label: `${m?.label ?? prettyName(s.metric)}${s.column === 'delta' ? ' (změna)' : ''}`,
    unit: m?.unit ?? '',
    digits: m?.digits ?? 2,
    icon: m?.icon ?? 'sunny-outline',
  };
}

export function formatValue(v: number | null | undefined, digits: number) {
  if (v === null || v === undefined || Number.isNaN(v)) return '–';
  return v.toLocaleString('cs-CZ', { minimumFractionDigits: 0, maximumFractionDigits: digits });
}

export function formatDateTime(iso: string | null | undefined) {
  if (!iso) return '–';
  const d = new Date(iso);
  return d.toLocaleString('cs-CZ', {
    day: 'numeric',
    month: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatAxisTime(ms: number, spanMs: number) {
  const d = new Date(ms);
  if (spanMs <= 36 * 3600e3) {
    return d.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' });
  }
  return d.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'numeric' });
}

export function timeAgo(iso: string | null | undefined) {
  if (!iso) return 'nikdy';
  const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return 'právě teď';
  if (s < 3600) return `před ${Math.floor(s / 60)} min`;
  if (s < 86400) return `před ${Math.floor(s / 3600)} h`;
  return `před ${Math.floor(s / 86400)} d`;
}

export function formatDuration(sec: number | null | undefined) {
  if (sec === null || sec === undefined) return '–';
  const d = Math.floor(sec / 86400);
  const h = Math.floor((sec % 86400) / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (d) return `${d} d ${h} h`;
  if (h) return `${h} h ${m} min`;
  return `${m} min`;
}
