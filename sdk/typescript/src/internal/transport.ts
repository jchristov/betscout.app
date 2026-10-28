/**
 * @internal
 * Private upstream transport configuration and channel alias resolution.
 * Never exported from the public SDK entrypoint.
 */

import type { ProviderChannel } from '../types.js';

/** @internal */
export const DEFAULT_UPSTREAM_BASE_URL = 'https://stats.fn.sportradar.com';

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
  token?: string
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
