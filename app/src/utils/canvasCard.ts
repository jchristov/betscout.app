import { getSportEmoji } from './formatters';

export interface PickCardMeta {
  sport_cat?: string;
  comp?: string;
  competition?: string;
  match?: string;
  pick?: string;
  pick_name?: string;
  odds_display?: string;
  win_prob_str?: string;
  fair_str?: string;
  exact_score?: string;
  announced_at_local?: string;
  date_local?: string;
  ended_at_local?: string;
  tier?: string;
  badge?: string;
}

function humanizeCanvasMarketCodes(rawVal?: string | null): string {
  let s = String(rawVal ?? '').trim();
  if (!s) return '';
  const map: Record<string, string> = {
    '(PLUS15_H)': '+1.5 Sets',
    '(PLUS15_A)': '+1.5 Sets',
    PLUS15_H: '+1.5 Sets',
    PLUS15_A: '+1.5 Sets',
    '(SETS20_H)': '2:0 Straight Sets',
    '(SETS20_A)': '0:2 Straight Sets',
    SETS20_H: '2:0 Straight Sets',
    SETS20_A: '0:2 Straight Sets',
    '(DC_1X)': 'or Draw (1X)',
    '(DC_X2)': 'or Draw (X2)',
    DC_1X: 'Double Chance 1X',
    DC_X2: 'Double Chance X2',
    '(DNB_H)': 'Draw No Bet (DNB)',
    '(DNB_A)': 'Draw No Bet (DNB)',
    DNB_H: 'Draw No Bet (DNB)',
    DNB_A: 'Draw No Bet (DNB)',
    '(OVER_2_5)': 'Over 2.5 Goals',
    OVER_2_5: 'Over 2.5 Goals',
    '(OVER_1_5)': 'Over 1.5 Goals',
    OVER_1_5: 'Over 1.5 Goals',
    SET_SHIELD: '+1.5 Sets Shield',
    STRAIGHT_SETS: '2:0 Straight Sets',
    DC_SHIELD: 'Double Chance Shield',
    DNB_SHIELD: 'Draw No Bet Shield',
    TOTALS_OVER: 'Over Total Goals',
    TOTALS_UNDER: 'Under Total Games',
  };
  for (const [k, v] of Object.entries(map)) {
    if (s.includes(k)) s = s.split(k).join(v);
  }
  s = s.replace(/\(?UNDER_GAMES_([0-9.]+)\)?/g, 'Under $1 Games');
  s = s.replace(/\(?OVER_GOALS_([0-9.]+)\)?/g, 'Over $1 Goals');
  return s.replace(/\s+/g, ' ').trim();
}

function splitCanvasKpiVal(rawVal?: string | null): { main: string; sub: string } {
  const s = humanizeCanvasMarketCodes(rawVal);
  if (!s) return { main: '—', sub: '' };
  if (s.includes(' · ')) {
    const idx = s.indexOf(' · ');
    return { main: s.slice(0, idx).trim(), sub: s.slice(idx + 3).trim() };
  }
  if (s.includes(' | ')) {
    const idx = s.indexOf(' | ');
    return { main: s.slice(0, idx).trim(), sub: s.slice(idx + 3).trim() };
  }
  if (s.includes('(') && s.endsWith(')') && !s.startsWith('(') && s.length > 14) {
    const idx = s.indexOf('(');
    return { main: s.slice(0, idx).trim(), sub: s.slice(idx + 1, -1).trim() };
  }
  return { main: s, sub: '' };
}

function compactCanvasTime(tsStr?: string | null): string {
  const s = String(tsStr ?? '').trim();
  if (!s) return '';
  const months: Record<string, string> = {
    '01': 'Jan',
    '02': 'Feb',
    '03': 'Mar',
    '04': 'Apr',
    '05': 'May',
    '06': 'Jun',
    '07': 'Jul',
    '08': 'Aug',
    '09': 'Sep',
    '10': 'Oct',
    '11': 'Nov',
    '12': 'Dec',
  };
  if (s.length >= 10 && s[4] === '-' && s[7] === '-') {
    const m = months[s.slice(5, 7)] || s.slice(5, 7);
    const d = s.slice(8, 10);
    const rest = s.slice(10).trim();
    return rest ? `${m} ${d}, ${rest}` : `${m} ${d}`;
  }
  return s;
}

function fillFittedCanvasText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  startSize: number,
  minSize: number,
  weight = '700',
  align?: CanvasTextAlign,
): void {
  const str = String(text ?? '');
  let sz = startSize;
  while (sz >= minSize) {
    ctx.font = `${weight} ${sz}px "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`;
    if (ctx.measureText(str).width <= maxWidth) break;
    sz -= 2;
  }
  let out = str;
  while (out.length > 4 && ctx.measureText(out).width > maxWidth) {
    out = out.slice(0, -1).trimEnd();
  }
  if (out !== str) out += '...';
  const prevAlign = ctx.textAlign;
  if (align) ctx.textAlign = align;
  ctx.fillText(out, x, y);
  if (align) ctx.textAlign = prevAlign;
}

function fillFittedMatchupCanvasText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  startSize: number,
  minSize: number,
  primaryColor = '#ffffff',
  mutedColor = '#94a3b8',
): void {
  const str = String(text ?? '');
  let sz = startSize;
  const fontFam = '"Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
  while (sz >= minSize) {
    ctx.font = `800 ${sz}px ${fontFam}`;
    if (ctx.measureText(str).width <= maxWidth) break;
    sz -= 2;
  }
  const finalSz = Math.max(minSize, sz);
  ctx.font = `800 ${finalSz}px ${fontFam}`;
  let out = str;
  while (out.length > 4 && ctx.measureText(out).width > maxWidth) {
    out = out.slice(0, -1).trimEnd();
  }
  if (out !== str) out += '...';
  if (!out.includes(' vs ')) {
    ctx.fillStyle = primaryColor;
    ctx.fillText(out, x, y);
    return;
  }
  const parts = out.split(' vs ');
  let curX = x;
  parts.forEach((part, idx) => {
    if (part) {
      ctx.font = `800 ${finalSz}px ${fontFam}`;
      ctx.fillStyle = primaryColor;
      ctx.fillText(part, curX, y);
      curX += ctx.measureText(part).width;
    }
    if (idx < parts.length - 1) {
      const vsStr = ' vs ';
      ctx.font = `500 ${finalSz}px ${fontFam}`;
      ctx.fillStyle = mutedColor;
      ctx.fillText(vsStr, curX, y);
      curX += ctx.measureText(vsStr).width;
    }
  });
}

export function renderCanvasPickCard(cv: HTMLCanvasElement | null, meta: PickCardMeta): void {
  if (!cv || !cv.getContext) return;
  const ctx = cv.getContext('2d');
  if (!ctx) return;
  const w = cv.width;
  const h = cv.height;

  const bgGrad = ctx.createLinearGradient(0, 0, 0, h);
  bgGrad.addColorStop(0, '#090d15');
  bgGrad.addColorStop(1, '#111827');
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, w, h);

  const badgeTxt = meta.badge ? String(meta.badge).toUpperCase() : 'LIVE AI PICK';
  const rawPickProbe = String(meta.pick_name || meta.pick || '').toUpperCase();
  const isLossCard = badgeTxt.includes('LOSS') || rawPickProbe.includes(' (L ');
  const isWinCard =
    !isLossCard &&
    (badgeTxt.includes('WIN') || badgeTxt.includes('SETTLED') || rawPickProbe.includes(' (W ') || Boolean(meta.ended_at_local));

  // Color-coded top border: Cyan (#38bdf8) for Picks, Green (#22c55e) for Resolved Wins, Red/Pink (#f43f5e) for Resolved Losses
  // Drawn as a smooth top-arc border stroke matching CSS `border-top` on `.card-surface`
  const topBorderColor = isLossCard ? '#f43f5e' : isWinCard ? '#22c55e' : '#38bdf8';
  ctx.fillStyle = '#0d1423';
  ctx.strokeStyle = '#2a3b5c';
  ctx.lineWidth = 2;
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(18, 18, w - 36, h - 36, 20);
  else ctx.rect(18, 18, w - 36, h - 36);
  ctx.fill();
  ctx.stroke();

  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, w, 30);
  ctx.clip();
  ctx.strokeStyle = topBorderColor;
  ctx.lineWidth = 3;
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(18, 18, w - 36, h - 36, 20);
  else ctx.rect(18, 18, w - 36, h - 36);
  ctx.stroke();
  ctx.restore();

  // Draw Option 7.3 3D Chiseled Bevel Compass Badge at (44, 42, 46, 46)
  ctx.save();
  ctx.fillStyle = '#0b1324';
  ctx.strokeStyle = '#2dd4bf';
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(44, 42, 46, 46, 11);
  else ctx.rect(44, 42, 46, 46);
  ctx.fill();
  ctx.stroke();
  const lcx = 67;
  const lcy = 65;
  ctx.strokeStyle = 'rgba(56, 189, 248, 0.28)';
  ctx.lineWidth = 1.1;
  ctx.beginPath();
  ctx.arc(lcx, lcy, 13.5, 0, Math.PI * 2);
  ctx.stroke();
  const drawTri = (pts: Array<[number, number]>, col: string) => {
    ctx.fillStyle = col;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    ctx.lineTo(pts[1][0], pts[1][1]);
    ctx.lineTo(pts[2][0], pts[2][1]);
    ctx.closePath();
    ctx.fill();
  };
  drawTri([[lcx, lcy - 17], [lcx, lcy], [lcx - 3.8, lcy - 3.8]], '#fde047');
  drawTri([[lcx, lcy - 17], [lcx + 3.8, lcy - 3.8], [lcx, lcy]], '#10b981');
  drawTri([[lcx, lcy + 17], [lcx, lcy], [lcx + 3.8, lcy + 3.8]], '#34d399');
  drawTri([[lcx, lcy + 17], [lcx - 3.8, lcy + 3.8], [lcx, lcy]], '#047857');
  drawTri([[lcx + 17, lcy], [lcx, lcy], [lcx + 3.8, lcy - 3.8]], '#7dd3fc');
  drawTri([[lcx + 17, lcy], [lcx + 3.8, lcy + 3.8], [lcx, lcy]], '#0284c7');
  drawTri([[lcx - 17, lcy], [lcx, lcy], [lcx - 3.8, lcy + 3.8]], '#38bdf8');
  drawTri([[lcx - 17, lcy], [lcx - 3.8, lcy - 3.8], [lcx, lcy]], '#0369a1');
  ctx.restore();

  // Two-tone "Bet" (white) + "Scout" (emerald) brand text matching App Header
  ctx.font = '800 27px "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.fillStyle = '#ffffff';
  ctx.fillText('Bet', 102, 68);
  const betW = ctx.measureText('Bet').width;
  ctx.fillStyle = '#34d399';
  ctx.fillText('Scout', 102 + betW, 68);

  ctx.fillStyle = '#94a3b8';
  ctx.font = '600 13px "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.fillText('SPORTS EDGE, EXACT-SCORE & PAPER-BETTING INTELLIGENCE', 102, 90);

  const spIcon = getSportEmoji(meta.sport_cat || meta.comp || meta.competition || meta.match || 'soccer');
  const combinedBadge = `${badgeTxt} ${String(meta.tier || '')}`.toUpperCase();
  let bFill = '#161a36';
  let bBorder = '#818cf8';
  let bText = '#c7d2fe';
  if (isLossCard || combinedBadge.includes('LOSS')) {
    bFill = '#2e101c';
    bBorder = '#f43f5e';
    bText = '#fda4af';
  } else if (isWinCard || combinedBadge.includes('SETTLED WIN')) {
    bFill = '#0a261c';
    bBorder = '#34d399';
    bText = '#6ee7b7';
  } else if (combinedBadge.includes('STEAM')) {
    bFill = '#2e160c';
    bBorder = '#fb923c';
    bText = '#fed7aa';
  } else if (
    combinedBadge.includes('MISPRICED') ||
    combinedBadge.includes('EDGE +') ||
    combinedBadge.includes('PROFIT BOOST') ||
    combinedBadge.includes('BOOSTER')
  ) {
    bFill = '#0a261c';
    bBorder = '#34d399';
    bText = '#6ee7b7';
  } else if (combinedBadge.includes('LIVE') || combinedBadge.includes('REBOUND')) {
    bFill = '#2e101c';
    bBorder = '#f43f5e';
    bText = '#fda4af';
  } else if (
    combinedBadge.includes('TOP_8PCT') ||
    combinedBadge.includes('TOP 8%') ||
    combinedBadge.includes('TIER_0')
  ) {
    bFill = '#201438';
    bBorder = '#a78bfa';
    bText = '#ddd6fe';
  } else if (
    combinedBadge.includes('BANKER') ||
    combinedBadge.includes('TIER_1') ||
    combinedBadge.includes('TOP_10PCT') ||
    combinedBadge.includes('70%') ||
    combinedBadge.includes('72%')
  ) {
    bFill = '#2c1e0c';
    bBorder = '#fbbf24';
    bText = '#fde68a';
  } else if (
    combinedBadge.includes('HIGH_CONF') ||
    combinedBadge.includes('HIGH-CONF') ||
    combinedBadge.includes('TOP_15PCT') ||
    combinedBadge.includes('UEFA') ||
    combinedBadge.includes('QUANT EDGE')
  ) {
    bFill = '#0a2230';
    bBorder = '#22d3ee';
    bText = '#a5f3fc';
  }

  ctx.fillStyle = bFill;
  ctx.strokeStyle = bBorder;
  ctx.lineWidth = 2;
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(w - 264, 46, 220, 40, 20);
  else ctx.rect(w - 264, 46, 220, 40);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = bText;
  fillFittedCanvasText(ctx, badgeTxt, w - 154, 71, 196, 13.5, 10.5, '700', 'center');

  ctx.strokeStyle = '#223049';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(44, 108);
  ctx.lineTo(w - 44, 108);
  ctx.stroke();

  const compStr = String(meta.comp || meta.competition || meta.sport_cat || 'MULTI-SPORT QUANT SLATE').toUpperCase();
  const spLow = String(meta.sport_cat || compStr).toLowerCase();
  let cFill = '#0a241c';
  let cBorder = '#34d399';
  let cText = '#6ee7b7';
  if (spLow.includes('table_tennis') || spLow.includes('table tennis') || spLow.includes('wtt')) {
    cFill = '#2a102e';
    cBorder = '#e879f9';
    cText = '#f5d0fe';
  } else if (spLow.includes('tennis') || spLow.includes('atp') || spLow.includes('wta')) {
    cFill = '#18260e';
    cBorder = '#a3e635';
    cText = '#d9f99d';
  } else if (spLow.includes('basketball') || spLow.includes('nba')) {
    cFill = '#2c160c';
    cBorder = '#fb923c';
    cText = '#fdba74';
  } else if (spLow.includes('hockey') || spLow.includes('nhl')) {
    cFill = '#0a222e';
    cBorder = '#22d3ee';
    cText = '#a5f3fc';
  } else if (spLow.includes('nfl') || (spLow.includes('football') && !spLow.includes('soccer'))) {
    cFill = '#2c1e0c';
    cBorder = '#fbbf24';
    cText = '#fde68a';
  }
  ctx.font = '700 12px "Plus Jakarta Sans", -apple-system, sans-serif';
  const compW = Math.min(410, Math.max(160, Math.ceil(ctx.measureText(compStr).width) + 28));
  ctx.fillStyle = cFill;
  ctx.strokeStyle = cBorder;
  ctx.lineWidth = 1;
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(44, 118, compW, 34, 9);
  else ctx.rect(44, 118, compW, 34);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = cText;
  fillFittedCanvasText(ctx, compStr, 58, 140, compW - 26, 12, 9.5, '700', 'left');

  const maxKoW = Math.max(260, w - 88 - compW - 16);
  if (meta.ended_at_local) {
    const pickLine = '📣 Pick: ' + compactCanvasTime(meta.announced_at_local || meta.date_local || 'Today');
    const spanLine =
      '🕒 Start: ' +
      compactCanvasTime(meta.date_local || 'Today') +
      '   |   🏁 Ended: ' +
      compactCanvasTime(meta.ended_at_local);
    ctx.font = '700 11px "Plus Jakarta Sans", -apple-system, sans-serif';
    const w1 = Math.ceil(ctx.measureText(pickLine).width);
    const w2 = Math.ceil(ctx.measureText(spanLine).width);
    const koBoxW = Math.min(maxKoW, Math.max(210, Math.max(w1, w2) + 28));
    ctx.fillStyle = '#0d1421';
    ctx.strokeStyle = '#2d3e5c';
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(w - 44 - koBoxW, 114, koBoxW, 44, 9);
    else ctx.rect(w - 44 - koBoxW, 114, koBoxW, 44);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#94a3b8';
    fillFittedCanvasText(ctx, pickLine, w - 56, 131, koBoxW - 22, 11, 9, '600', 'right');
    ctx.fillStyle = '#e2e8f0';
    fillFittedCanvasText(ctx, spanLine, w - 56, 148, koBoxW - 22, 11, 9, '700', 'right');
  } else {
    const timeBits: string[] = [];
    if (meta.announced_at_local) timeBits.push('📣 Pick: ' + compactCanvasTime(meta.announced_at_local));
    timeBits.push('🕒 Start: ' + compactCanvasTime(meta.date_local || 'Today'));
    const koStr = timeBits.join('   |   ');
    ctx.font = '700 12px "Plus Jakarta Sans", -apple-system, sans-serif';
    const koBoxW = Math.min(maxKoW, Math.max(190, Math.ceil(ctx.measureText(koStr).width) + 28));
    ctx.fillStyle = '#0d1421';
    ctx.strokeStyle = '#2d3e5c';
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(w - 44 - koBoxW, 118, koBoxW, 34, 9);
    else ctx.rect(w - 44 - koBoxW, 118, koBoxW, 34);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#cbd5e1';
    fillFittedCanvasText(ctx, koStr, w - 56, 140, koBoxW - 22, 12, 9, '700', 'right');
  }

  const matchTitle = `${spIcon}  ${String(meta.match || 'Daily High-Conviction Picks')}`;
  fillFittedMatchupCanvasText(ctx, matchTitle, 44, 198, w - 88, 32, 18, '#ffffff', '#94a3b8');

  const pickBoxFill = isLossCard ? '#26101a' : '#0d211d';
  const pickBoxBorder = isLossCard ? '#f43f5e' : '#22c55e';
  ctx.save();
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(44, 224, w - 88, 128, 14);
  else ctx.rect(44, 224, w - 88, 128);
  ctx.fillStyle = pickBoxFill;
  ctx.fill();
  ctx.clip();
  ctx.fillStyle = pickBoxBorder;
  ctx.fillRect(44, 224, 9, 128);
  ctx.restore();
  ctx.strokeStyle = pickBoxBorder;
  ctx.lineWidth = 2;
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(44, 224, w - 88, 128, 14);
  else ctx.rect(44, 224, w - 88, 128);
  ctx.stroke();

  ctx.fillStyle = isLossCard ? '#fda4af' : '#86efac';
  ctx.font = '700 13px "Plus Jakarta Sans", -apple-system, sans-serif';
  ctx.fillText(
    isLossCard
      ? 'RESOLVED PAPER-BET RESULT (LOSS)'
      : isWinCard
        ? 'RESOLVED PAPER-BET RESULT (WIN)'
        : 'RECOMMENDED MODEL PICK',
    72,
    250,
  );

  const rawPick = humanizeCanvasMarketCodes(meta.pick || meta.pick_name || 'Top Calibrated Edge');
  let mainPick = rawPick;
  let subPick = '';
  if (rawPick.includes(' · ')) {
    const pts = rawPick.split(' · ');
    mainPick = pts[0];
    subPick = pts.slice(1).join(' · ');
  } else if (rawPick.includes(' | ')) {
    const pts = rawPick.split(' | ');
    mainPick = pts[0];
    subPick = pts.slice(1).join(' | ');
  }
  ctx.fillStyle = pickBoxBorder;
  fillFittedCanvasText(ctx, mainPick, 72, 290, w - 144, 28, 16, '800', 'left');

  const subLine =
    subPick ||
    (meta.exact_score && meta.exact_score !== 'Moneyline Edge'
      ? `Score / Set Target: ${meta.exact_score}`
      : 'Verified Out-of-Sample Quantitative Signal');
  ctx.fillStyle = '#cbd5e1';
  fillFittedCanvasText(ctx, subLine, 72, 328, w - 144, 15, 11, '600', 'left');

  const odSplit = splitCanvasKpiVal(meta.odds_display || '—');
  const escSplit = splitCanvasKpiVal(meta.exact_score || 'Moneyline Edge');
  const kpis = [
    { lbl: 'BOOKMAKER ODDS', main: odSplit.main, sub: odSplit.sub || 'Live Market Price', col: '#fbbf24' },
    {
      lbl: 'MODEL WIN PROB',
      main: String(meta.win_prob_str || 'High Conf'),
      sub: 'Tier: ' + String(meta.tier || meta.badge || 'TOP EDGE').toUpperCase(),
      col: '#34d399',
    },
    { lbl: 'MIN FAIR ODDS', main: String(meta.fair_str || 'Calibrated'), sub: 'Zero-Vig Model Floor', col: '#38bdf8' },
    { lbl: 'SCORE PROJECTION', main: escSplit.main, sub: escSplit.sub || 'Dixon-Coles / Set Matrix', col: '#e879f9' },
  ];
  const bw = Math.floor((w - 88 - 36) / 4);
  kpis.forEach((k, idx) => {
    const bx = 44 + idx * (bw + 12);
    ctx.fillStyle = '#0a101d';
    ctx.strokeStyle = '#263654';
    ctx.lineWidth = 1;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(bx, 370, bw, 118, 12);
    else ctx.rect(bx, 370, bw, 118);
    ctx.fill();
    ctx.stroke();

    ctx.save();
    ctx.beginPath();
    ctx.rect(bx, 368, bw, 10);
    ctx.clip();
    ctx.strokeStyle = k.col;
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(bx, 370, bw, 118, 12);
    else ctx.rect(bx, 370, bw, 118);
    ctx.stroke();
    ctx.restore();

    ctx.fillStyle = '#94a3b8';
    ctx.font = '700 11px "Plus Jakarta Sans", -apple-system, sans-serif';
    ctx.fillText(k.lbl, bx + 16, 396);
    ctx.fillStyle = k.col;
    fillFittedCanvasText(ctx, k.main, bx + 16, 434, bw - 28, 24, 14, '800', 'left');
    if (k.sub) {
      ctx.fillStyle = '#94a3b8';
      fillFittedCanvasText(ctx, k.sub, bx + 16, 466, bw - 28, 12, 9.5, '600', 'left');
    }
  });

  ctx.strokeStyle = '#223049';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(44, 508);
  ctx.lineTo(w - 44, 508);
  ctx.stroke();
  ctx.fillStyle = '#94a3b8';
  ctx.font = '500 13px "Plus Jakarta Sans", -apple-system, sans-serif';
  ctx.fillText('Out-of-Sample Walk-Forward Validated  ·  Dixon-Coles Score Matrix  ·  ¼-Kelly Risk Sizing', 44, 534);

  ctx.font = '700 13.5px "Plus Jakarta Sans", -apple-system, sans-serif';
  const fBetW = ctx.measureText('Bet').width;
  const fScoutW = ctx.measureText('Scout').width;
  const fxStart = w - 44 - (fBetW + fScoutW);
  ctx.fillStyle = '#ffffff';
  ctx.fillText('Bet', fxStart, 534);
  ctx.fillStyle = '#34d399';
  ctx.fillText('Scout', fxStart + fBetW, 534);
}
