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

function splitCanvasKpiVal(rawVal?: string | null): { main: string; sub: string } {
  const s = String(rawVal ?? '').trim();
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

  ctx.fillStyle = '#111827';
  ctx.strokeStyle = '#24344f';
  ctx.lineWidth = 2;
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(18, 18, w - 36, h - 36, 20);
  else ctx.rect(18, 18, w - 36, h - 36);
  ctx.fill();
  ctx.stroke();

  const topGrad = ctx.createLinearGradient(20, 0, w - 20, 0);
  topGrad.addColorStop(0, '#38bdf8');
  topGrad.addColorStop(1, '#22c55e');
  ctx.fillStyle = topGrad;
  ctx.fillRect(20, 20, w - 40, 6);

  ctx.fillStyle = '#f1f5f9';
  ctx.font = '800 27px "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.fillText('⚡ BETSCOUT', 44, 70);
  ctx.fillStyle = '#94a3b8';
  ctx.font = '600 13px "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.fillText('SPORTS EDGE, EXACT-SCORE & PAPER-BETTING INTELLIGENCE', 46, 93);

  const spIcon = getSportEmoji(meta.sport_cat || meta.comp || meta.competition || meta.match || 'soccer');
  const badgeTxt = meta.badge ? String(meta.badge) : 'LIVE AI SIGNAL';
  ctx.fillStyle = '#0d1421';
  ctx.strokeStyle = '#22c55e';
  ctx.lineWidth = 2;
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(w - 264, 46, 220, 40, 20);
  else ctx.rect(w - 264, 46, 220, 40);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = '#22c55e';
  fillFittedCanvasText(ctx, badgeTxt, w - 154, 71, 196, 13.5, 10.5, '700', 'center');

  ctx.strokeStyle = '#223049';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(44, 108);
  ctx.lineTo(w - 44, 108);
  ctx.stroke();

  const compStr = String(meta.comp || meta.competition || meta.sport_cat || 'MULTI-SPORT QUANT SLATE').toUpperCase();
  ctx.font = '700 12px "Plus Jakarta Sans", -apple-system, sans-serif';
  const compW = Math.min(410, Math.max(160, Math.ceil(ctx.measureText(compStr).width) + 28));
  ctx.fillStyle = '#0d1421';
  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 1;
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(44, 118, compW, 34, 9);
  else ctx.rect(44, 118, compW, 34);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = '#38bdf8';
  fillFittedCanvasText(ctx, compStr, 58, 140, compW - 26, 12, 9.5, '700', 'left');

  const timeBits: string[] = [];
  if (meta.announced_at_local) timeBits.push('📣 Pick: ' + compactCanvasTime(meta.announced_at_local));
  timeBits.push('🕒 Start: ' + compactCanvasTime(meta.date_local || 'Today'));
  if (meta.ended_at_local) timeBits.push('🏁 Ended: ' + compactCanvasTime(meta.ended_at_local));
  const koStr = timeBits.join('   |   ');
  const maxKoW = Math.max(260, w - 88 - compW - 16);
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

  const matchTitle = `${spIcon}  ${String(meta.match || 'Daily High-Conviction Picks')}`;
  ctx.fillStyle = '#ffffff';
  fillFittedCanvasText(ctx, matchTitle, 44, 198, w - 88, 32, 18, '800', 'left');

  ctx.fillStyle = '#0d211d';
  ctx.strokeStyle = '#22c55e';
  ctx.lineWidth = 2;
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(44, 224, w - 88, 128, 14);
  else ctx.rect(44, 224, w - 88, 128);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = '#22c55e';
  ctx.fillRect(46, 226, 8, 124);

  ctx.fillStyle = '#86efac';
  ctx.font = '700 13px "Plus Jakarta Sans", -apple-system, sans-serif';
  ctx.fillText('🎯 RECOMMENDED MODEL PICK', 72, 250);

  const rawPick = String(meta.pick || 'Top Calibrated Edge');
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
  ctx.fillStyle = '#22c55e';
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
    { lbl: 'BOOKMAKER ODDS', main: odSplit.main, sub: odSplit.sub || 'Live Market Price', col: '#22c55e' },
    {
      lbl: 'MODEL WIN PROB',
      main: String(meta.win_prob_str || 'High Conf'),
      sub: 'Tier: ' + String(meta.tier || meta.badge || 'TOP EDGE').toUpperCase(),
      col: '#38bdf8',
    },
    { lbl: 'MIN FAIR ODDS', main: String(meta.fair_str || 'Calibrated'), sub: 'Zero-Vig Model Floor', col: '#f1f5f9' },
    { lbl: 'SCORE PROJECTION', main: escSplit.main, sub: escSplit.sub || 'Dixon-Coles / Set Matrix', col: '#f59e0b' },
  ];
  const bw = Math.floor((w - 88 - 36) / 4);
  kpis.forEach((k, idx) => {
    const bx = 44 + idx * (bw + 12);
    ctx.fillStyle = '#0d1421';
    ctx.strokeStyle = '#223049';
    ctx.lineWidth = 1;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(bx, 370, bw, 118, 12);
    else ctx.rect(bx, 370, bw, 118);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = k.col;
    ctx.fillRect(bx + 2, 371, bw - 4, 4);

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
  ctx.fillStyle = '#38bdf8';
  fillFittedCanvasText(ctx, 'BetScout', w - 44, 534, 180, 13.5, 11, '700', 'right');
}
