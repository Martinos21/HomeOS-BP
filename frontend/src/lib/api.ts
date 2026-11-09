import type { Device, HistoryPoint, Range, SolarMetric, Source, Stats, SystemInfo } from './types';

export type ApiConfig = { url: string; key: string };

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
  }
}

const RANGE_MS: Record<Exclude<Range, 'all'>, number> = {
  '1h': 3600e3,
  '24h': 24 * 3600e3,
  '7d': 7 * 24 * 3600e3,
  '30d': 30 * 24 * 3600e3,
};

/** ISO cas pro ?since= (stejny format jako v DB: ...Z). */
export function sinceFor(range: Range): string | undefined {
  if (range === 'all') return undefined;
  return new Date(Date.now() - RANGE_MS[range]).toISOString();
}

async function get<T>(cfg: ApiConfig, path: string, params: Record<string, string | number | undefined> = {}): Promise<T> {
  if (!cfg.url) throw new ApiError('Není nastavena adresa serveru (Nastavení → Připojení).');
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&');
  const url = `${cfg.url.replace(/\/+$/, '')}${path}${qs ? `?${qs}` : ''}`;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 10000);
  let res: Response;
  try {
    res = await fetch(url, { headers: { 'X-API-Key': cfg.key }, signal: ctrl.signal });
  } catch {
    throw new ApiError('Server neodpovídá. Zkontroluj adresu a že backend běží.');
  } finally {
    clearTimeout(timer);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(body?.error ?? `Chyba serveru (${res.status})`, res.status);
  return body as T;
}

function sourcePath(s: Source) {
  return s.kind === 'device'
    ? `/api/devices/${encodeURIComponent(s.name)}`
    : `/api/solar/${encodeURIComponent(s.metric)}`;
}

export const api = {
  health: (cfg: ApiConfig) => get<{ ok: boolean; zigbee_online: boolean }>(cfg, '/api/health'),
  system: (cfg: ApiConfig) => get<SystemInfo>(cfg, '/api/system'),
  devices: (cfg: ApiConfig) => get<Device[]>(cfg, '/api/devices'),
  solar: (cfg: ApiConfig) => get<SolarMetric[]>(cfg, '/api/solar'),
  stats: (cfg: ApiConfig, s: Source, range: Range) =>
    get<Stats>(cfg, `${sourcePath(s)}/stats`, { column: s.column, since: sinceFor(range) }),
  history: (cfg: ApiConfig, s: Source, range: Range, points = 300) =>
    get<HistoryPoint[]>(cfg, `${sourcePath(s)}/history`, {
      column: s.column,
      since: sinceFor(range),
      points,
    }),
};
