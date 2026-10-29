/**
 * BetScout MCP API & SDK Client (`BetScoutMcpBackendClient`).
 * Combines the BetScout Quant API (`/api/snapshot`, `/api/analyze-live`, `/api/matchup`)
 * with `@betscout/sdk` (`BetScoutClient`) and an in-memory TTL cache to minimize remote lookups.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { BetScoutClient } from '@betscout/sdk';
import { BetScoutMcpError } from './errors.js';

export interface McpBackendOptions {
  apiUrl?: string;
  apiKey?: string;
  timeoutMs?: number;
  ttlSec?: number;
  fetchFn?: typeof fetch;
  dataDir?: string;
}

interface ApiCacheEntry<T = any> {
  expiresAtMs: number;
  value: T;
}

export class BetScoutMcpBackendClient {
  public readonly apiUrl: string;
  public readonly apiKey: string;
  public readonly timeoutMs: number;
  public readonly ttlSec: number;
  public readonly sdk: BetScoutClient;
  private readonly fetchFn: typeof fetch;
  private readonly dataDir: string;
  private readonly apiCache = new Map<string, ApiCacheEntry>();
  private apiCacheHits = 0;
  private apiCacheMisses = 0;

  constructor(options: McpBackendOptions = {}) {
    this.apiUrl = (
      options.apiUrl ??
      process.env.BETSCOUT_API_URL ??
      'http://127.0.0.1:8090'
    ).replace(/\/+$/, '');
    this.apiKey = options.apiKey ?? process.env.BETSCOUT_API_KEY ?? '';
    this.timeoutMs = options.timeoutMs ?? 12000;
    this.ttlSec = options.ttlSec ?? 180;
    this.fetchFn = options.fetchFn ?? globalThis.fetch.bind(globalThis);
    const here = path.dirname(fileURLToPath(import.meta.url));
    this.dataDir = options.dataDir ?? path.resolve(here, '..', '..', 'data');
    this.sdk = new BetScoutClient({
      fetchFn: this.fetchFn,
      defaultTtlSec: 600,
      negativeTtlSec: 120,
      timeoutMs: this.timeoutMs,
    });
  }

  public getCacheTelemetry() {
    return {
      api_cache_entries: this.apiCache.size,
      api_cache_hits: this.apiCacheHits,
      api_cache_misses: this.apiCacheMisses,
      sdk_cache: this.sdk.getCacheStats(),
    };
  }

  public clearCache(): void {
    this.apiCache.clear();
    this.sdk.clearCache();
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
    };
    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }
    return headers;
  }

  public async fetchApiJson<T = any>(
    endpointPath: string,
    ttlSec = this.ttlSec,
  ): Promise<T> {
    const cacheKey = endpointPath;
    const now = Date.now();
    const hit = this.apiCache.get(cacheKey);
    if (hit && hit.expiresAtMs > now) {
      this.apiCacheHits += 1;
      return hit.value as T;
    }

    this.apiCacheMisses += 1;
    const url = `${this.apiUrl}${endpointPath}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const resp = await this.fetchFn(url, {
        headers: this.getHeaders(),
        signal: controller.signal,
      });
      if (!resp.ok) {
        throw new BetScoutMcpError(
          `BetScout API returned HTTP ${resp.status} for ${endpointPath}.`,
          resp.status === 401 || resp.status === 403
            ? 'Provide a valid `BETSCOUT_API_KEY` environment variable.'
            : 'Verify the endpoint parameters or check if the BetScout API server is running.',
          resp.status,
        );
      }
      const data = (await resp.json()) as T;
      this.apiCache.set(cacheKey, {
        expiresAtMs: now + ttlSec * 1000,
        value: data,
      });
      return data;
    } finally {
      clearTimeout(timer);
    }
  }

  public async getSnapshot(minOdds = 1.05, sport = 'all'): Promise<any> {
    const qs = new URLSearchParams({
      min_odds: String(minOdds),
      sport: String(sport),
    });
    try {
      return await this.fetchApiJson(`/api/snapshot?${qs.toString()}`, 120);
    } catch (err) {
      // Fallback to local data/recommendations.json when offline
      const recFile = path.join(this.dataDir, 'recommendations.json');
      if (fs.existsSync(recFile)) {
        const raw = JSON.parse(fs.readFileSync(recFile, 'utf-8'));
        return {
          ok: true,
          generated_at: raw.generated_at,
          best_bets: raw.best_bets ?? [],
          qualifying_picks: raw.qualifying_picks ?? [],
          tennis_picks: raw.tennis_picks ?? [],
          other_sport_picks: raw.other_sport_picks ?? [],
          recommended_doubles: raw.recommended_doubles ?? [],
          paper_ledger: raw.paper_ledger ?? {},
        };
      }
      throw err;
    }
  }

  public async analyzeMatchup(query: string): Promise<any> {
    const qs = new URLSearchParams({ q: query });
    return await this.fetchApiJson(`/api/analyze-live?${qs.toString()}`, 180);
  }

  public async getMatchupDetail(home: string, away: string, league = ''): Promise<any> {
    const qs = new URLSearchParams({ home, away, league });
    return await this.fetchApiJson(`/api/matchup?${qs.toString()}`, 180);
  }
}
