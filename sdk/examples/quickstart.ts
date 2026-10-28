/**
 * Quickstart Example for `@betscout/sportradar-gismo-sdk`.
 * Run with: `npm run example`
 */

import { SportradarGismoClient } from '../src/index.js';

async function main() {
  const client = new SportradarGismoClient({
    defaultClientAlias: 'tipico',
    defaultLanguage: 'en',
    defaultTimezone: 'Europe:Berlin',
  });

  // 1. List all 56 sports behind the "All Sports" modal (`config_sports/69/0`)
  const sports = await client.listAllSports(69, 0, 'sportradar');
  console.log(`✅ Loaded ${sports.length} Sportradar sports:`, sports.slice(0, 8));

  // 2. Fetch today's Soccer match index (excluding Simulated Reality League)
  const today = new Date().toISOString().slice(0, 10);
  const matches = await client.getDailyMatchIndex('soccer', today);
  console.log(`⚽ Found ${matches.length} Football matches on ${today}`);

  if (matches.length > 0) {
    const sample = matches[0]!;
    console.log(`🔍 Looking up full Match Intel for: ${sample.home} vs ${sample.away} (${sample.tournament})`);
    const intel = await client.lookupMatchIntel(sample.home, sample.away, 'soccer', today);
    console.log('📊 Match Intelligence Summary:', {
      sr_match_id: intel.sr_match_id,
      tournament: intel.tournament,
      bookmaker: intel.primary_markets?.bookmaker,
      odds_1x2: [
        intel.primary_markets?.odds_home,
        intel.primary_markets?.odds_draw,
        intel.primary_markets?.odds_away,
      ],
      correct_scores_count: Object.keys(intel.primary_markets?.correct_score_odds ?? {}).length,
      home_injuries: intel.home_injuries,
      streaks: intel.streaks,
    });
  }
}

main().catch((err) => {
  console.error('Example error:', err);
  process.exit(1);
});
