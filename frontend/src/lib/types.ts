/** Odkud widget bere data: Zigbee ESP (tabulka dev_<name>) nebo solarAPI (tabulka stats). */
export type Source =
  | { kind: 'device'; name: string; column: string }
  | { kind: 'solar'; metric: string; column: 'total' | 'delta' };

export type Stat = 'last' | 'avg' | 'min' | 'max';
export type Range = '1h' | '24h' | '7d' | '30d' | 'all';

export type Widget = {
  id: string;
  title?: string;
  source: Source;
  stat: Stat;
  range: Range;
};

export type Stats = {
  last: number | null;
  last_at: string | null;
  avg: number | null;
  min: number | null;
  max: number | null;
  count: number;
};

export type HistoryPoint = { at: string; avg: number; min: number; max: number };

export type Device = {
  ieee: string;
  name: string;
  table: string;
  manufacturer: string | null;
  model: string | null;
  paired_at: string;
  last_seen: string | null;
  columns: string[];
  latest: ({ at: string } & Record<string, number | null>) | null;
};

export type SolarMetric = {
  metric: string;
  columns: ('total' | 'delta')[];
  latest: { at: string; total: number; delta: number } | null;
};

export type SystemInfo = {
  hostname: string;
  os: string;
  kernel: string;
  arch: string;
  python: string;
  python_impl: string;
  uptime_s: number | null;
  api_uptime_s: number;
  zigbee_online: boolean;
  device_count: number;
  db_path: string;
};
