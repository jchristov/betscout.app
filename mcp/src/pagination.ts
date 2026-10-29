/**
 * Opaque cursor pagination helpers for `@betscout/mcp-server`.
 * Never leaks "page N of M" to the LLM — returns an opaque base64url cursor
 * with an explicit continuation hint.
 */

export interface PaginatedResult<T> {
  items: T[];
  returned_count: number;
  total_available: number;
  has_more: boolean;
  next_cursor: string | null;
  pagination_hint: string;
}

export function encodeCursor(offset: number): string {
  const cleanOffset = Math.max(0, Math.floor(offset));
  const json = JSON.stringify({ o: cleanOffset });
  return Buffer.from(json, 'utf-8')
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

export function decodeCursor(cursor?: string | null): number {
  if (!cursor || !String(cursor).trim()) return 0;
  const raw = String(cursor).trim();
  const base64 = raw.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
  try {
    const decoded = Buffer.from(padded, 'base64').toString('utf-8');
    const parsed = JSON.parse(decoded) as { o?: number };
    if (typeof parsed.o !== 'number' || !Number.isInteger(parsed.o) || parsed.o < 0) {
      throw new Error('Malformed offset');
    }
    return parsed.o;
  } catch {
    throw new Error(
      `Invalid pagination cursor "${cursor}". Omit \`cursor\` to start from the first batch of results.`,
    );
  }
}

export function paginateItems<T>(
  items: T[],
  options: { cursor?: string | null; limit?: number } = {},
): PaginatedResult<T> {
  const offset = decodeCursor(options.cursor);
  const pageSize = Math.max(1, Math.min(Math.floor(options.limit ?? 15), 50));
  const sliced = items.slice(offset, offset + pageSize);
  const nextOffset = offset + pageSize;
  const hasMore = nextOffset < items.length;
  const nextCursor = hasMore ? encodeCursor(nextOffset) : null;

  return {
    items: sliced,
    returned_count: sliced.length,
    total_available: items.length,
    has_more: hasMore,
    next_cursor: nextCursor,
    pagination_hint: nextCursor
      ? `More results available. Pass \`cursor: "${nextCursor}"\` to retrieve the next batch.`
      : 'All matching results returned.',
  };
}
