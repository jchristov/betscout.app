/**
 * @internal
 * Private upstream transport configuration, image CDN URL builders, and channel alias resolution.
 * Never exported from the public SDK entrypoint.
 */

import type { CountryFlagOptions, ProviderChannel, TeamLogoOptions } from '../types.js';

/** @internal */
export const DEFAULT_UPSTREAM_BASE_URL = 'https://stats.fn.sportradar.com';

/** @internal */
export const DEFAULT_UPSTREAM_IMAGE_BASE_URL = 'https://img.sportradar.com';

/** @internal */
export const DEFAULT_UPSTREAM_PROTOCOL = 'gismo';

/** @internal */
const CHANNEL_MAP: Readonly<Record<string, string>> = {
  global: 'sportradar',
  'eu-retail': 'tipico',
  neutral: 'common',
  common: 'common',
  sportradar: 'sportradar',
  tipico: 'tipico',
};

/** @internal */
const UK_HOME_NATION_SVG_MAP: Readonly<Record<string, string>> = {
  en: 'gb-eng',
  s: 'gb-sct',
  n: 'gb-nir',
  w: 'gb-wls',
};

/** @internal */
export function resolveUpstreamChannel(channel?: ProviderChannel | string): string {
  if (!channel) return 'sportradar';
  const normalized = String(channel).trim().toLowerCase();
  return CHANNEL_MAP[normalized] || normalized;
}

/** @internal */
export function buildUpstreamFeedUrl(
  baseUrl: string,
  channel: ProviderChannel | string,
  language: string,
  timezone: string,
  endpoint: string,
  params?: string | number | Array<string | number | undefined | null>,
  token?: string,
): string {
  const cleanBase = baseUrl.replace(/\/+$/, '');
  const cleanEndpoint = endpoint.replace(/^\/+|\/+$/g, '');
  const resolvedChannel = resolveUpstreamChannel(channel);

  let paramPath = '';
  if (Array.isArray(params)) {
    paramPath = params
      .filter((p): p is string | number => p !== undefined && p !== null && String(p).length > 0)
      .map((p) => String(p).replace(/^\/+|\/+$/g, ''))
      .join('/');
  } else if (params !== undefined && params !== null && String(params).length > 0) {
    paramPath = String(params).replace(/^\/+|\/+$/g, '');
  }

  const suffix = paramPath ? `${cleanEndpoint}/${paramPath}` : cleanEndpoint;
  const url = `${cleanBase}/${resolvedChannel}/${language}/${timezone}/${DEFAULT_UPSTREAM_PROTOCOL}/${suffix}`;
  if (token) {
    return `${url}?T=${encodeURIComponent(token)}`;
  }
  return url;
}

/** @internal */
export function buildUpstreamTeamLogoUrl(
  teamId: number | string,
  options: TeamLogoOptions = {},
): string {
  const base = (options.imageBaseUrl ?? DEFAULT_UPSTREAM_IMAGE_BASE_URL).replace(/\/+$/, '');
  if (options.ncaa) {
    const ncaaSize = options.ncaaSize ?? 'ap250x188ut';
    return `${base}/ls/teams/${ncaaSize}/${teamId}.png`;
  }
  const size = options.size ?? 'big';
  return `${base}/ls/crest/${size}/${teamId}.png`;
}

/** @internal */
export function buildUpstreamCountryFlagUrl(
  countryIso2: string,
  options: CountryFlagOptions = {},
): string {
  const base = (options.imageBaseUrl ?? DEFAULT_UPSTREAM_IMAGE_BASE_URL).replace(/\/+$/, '');
  const cleanIso = String(countryIso2 || 'int')
    .trim()
    .toLowerCase();
  if (cleanIso === 'int') {
    const size = options.size ?? 'medium';
    return `${base}/ls/crest/${size}/int.png`;
  }
  const format = options.format ?? 'svg';
  if (format === 'svg') {
    const ratio = options.ratio ?? '4x3';
    const mappedCode = UK_HOME_NATION_SVG_MAP[cleanIso] ?? cleanIso;
    return `${base}/ls/crest/${ratio}/${mappedCode}.svg`;
  }
  const size = options.size ?? 'medium';
  return `${base}/ls/crest/${size}/${cleanIso}.png`;
}
