import { cn } from '@/shared/lib/utils';
import type { ScoredDestination } from '../model/types';

const COUNTRY_FLAGS: Record<string, string> = {
  AF: '🇦🇫', AL: '🇦🇱', DZ: '🇩🇿', AD: '🇦🇩', AO: '🇦🇴', AG: '🇦🇬', AR: '🇦🇷', AM: '🇦🇲',
  AU: '🇦🇺', AT: '🇦🇹', AZ: '🇦🇿', BS: '🇧🇸', BH: '🇧🇭', BD: '🇧🇩', BB: '🇧🇧', BY: '🇧🇾',
  BE: '🇧🇪', BZ: '🇧🇿', BJ: '🇧🇯', BT: '🇧🇹', BO: '🇧🇴', BA: '🇧🇦', BW: '🇧🇼', BR: '🇧🇷',
  BN: '🇧🇳', BG: '🇧🇬', BF: '🇧🇫', BI: '🇧🇮', CV: '🇨🇻', KH: '🇰🇭', CM: '🇨🇲', CA: '🇨🇦',
  CF: '🇨🇫', TD: '🇹🇩', CL: '🇨🇱', CN: '🇨🇳', CO: '🇨🇴', KM: '🇰🇲', CG: '🇨🇬', CR: '🇨🇷',
  HR: '🇭🇷', CU: '🇨🇺', CY: '🇨🇾', CZ: '🇨🇿', DK: '🇩🇰', DJ: '🇩🇯', DM: '🇩🇲', DO: '🇩🇴',
  EC: '🇪🇨', EG: '🇪🇬', SV: '🇸🇻', GQ: '🇬🇶', ER: '🇪🇷', EE: '🇪🇪', SZ: '🇸🇿', ET: '🇪🇹',
  FJ: '🇫🇯', FI: '🇫🇮', FR: '🇫🇷', GA: '🇬🇦', GM: '🇬🇲', GE: '🇬🇪', DE: '🇩🇪', GH: '🇬🇭',
  GR: '🇬🇷', GD: '🇬🇩', GT: '🇬🇹', GN: '🇬🇳', GW: '🇬🇼', GY: '🇬🇾', HT: '🇭🇹', HN: '🇭🇳',
  HU: '🇭🇺', IS: '🇮🇸', IN: '🇮🇳', ID: '🇮🇩', IR: '🇮🇷', IQ: '🇮🇶', IE: '🇮🇪', IL: '🇮🇱',
  IT: '🇮🇹', JM: '🇯🇲', JP: '🇯🇵', JO: '🇯🇴', KZ: '🇰🇿', KE: '🇰🇪', KI: '🇰🇮', KP: '🇰🇵',
  KR: '🇰🇷', KW: '🇰🇼', KG: '🇰🇬', LA: '🇱🇦', LV: '🇱🇻', LB: '🇱🇧', LS: '🇱🇸', LR: '🇱🇷',
  LY: '🇱🇾', LI: '🇱🇮', LT: '🇱🇹', LU: '🇱🇺', MG: '🇲🇬', MW: '🇲🇼', MY: '🇲🇾', MV: '🇲🇻',
  ML: '🇲🇱', MT: '🇲🇹', MH: '🇲🇭', MR: '🇲🇷', MU: '🇲🇺', MX: '🇲🇽', FM: '🇫🇲', MD: '🇲🇩',
  MC: '🇲🇨', MN: '🇲🇳', ME: '🇲🇪', MA: '🇲🇦', MZ: '🇲🇿', MM: '🇲🇲', NA: '🇳🇦', NR: '🇳🇷',
  NP: '🇳🇵', NL: '🇳🇱', NZ: '🇳🇿', NI: '🇳🇮', NE: '🇳🇪', NG: '🇳🇬', NO: '🇳🇴', OM: '🇴🇲',
  PK: '🇵🇰', PW: '🇵🇼', PA: '🇵🇦', PG: '🇵🇬', PY: '🇵🇾', PE: '🇵🇪', PH: '🇵🇭', PL: '🇵🇱',
  PT: '🇵🇹', QA: '🇶🇦', RO: '🇷🇴', RU: '🇷🇺', RW: '🇷🇼', KN: '🇰🇳', LC: '🇱🇨', VC: '🇻🇨',
  WS: '🇼🇸', SM: '🇸🇲', ST: '🇸🇹', SA: '🇸🇦', SN: '🇸🇳', RS: '🇷🇸', SC: '🇸🇨', SL: '🇸🇱',
  SG: '🇸🇬', SK: '🇸🇰', SI: '🇸🇮', SB: '🇸🇧', SO: '🇸🇴', ZA: '🇿🇦', SS: '🇸🇸', ES: '🇪🇸',
  LK: '🇱🇰', SD: '🇸🇩', SR: '🇸🇷', SE: '🇸🇪', CH: '🇨🇭', SY: '🇸🇾', TW: '🇹🇼', TJ: '🇹🇯',
  TZ: '🇹🇿', TH: '🇹🇭', TL: '🇹🇱', TG: '🇹🇬', TO: '🇹🇴', TT: '🇹🇹', TN: '🇹🇳', TR: '🇹🇷',
  TM: '🇹🇲', TV: '🇹🇻', UG: '🇺🇬', UA: '🇺🇦', AE: '🇦🇪', GB: '🇬🇧', US: '🇺🇸', UY: '🇺🇾',
  UZ: '🇺🇿', VU: '🇻🇺', VE: '🇻🇪', VN: '🇻🇳', YE: '🇾🇪', ZM: '🇿🇲', ZW: '🇿🇼',
};

const TAG_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  beach: { label: 'Пляж', color: '#0369A1', bg: 'rgba(3,105,161,0.08)' },
  culture: { label: 'Культура', color: '#7C3AED', bg: 'rgba(124,58,237,0.08)' },
  nature: { label: 'Природа', color: '#15803D', bg: 'rgba(21,128,61,0.08)' },
  adventure: { label: 'Активный', color: '#B45309', bg: 'rgba(180,83,9,0.08)' },
  food: { label: 'Гастро', color: '#DC2626', bg: 'rgba(220,38,38,0.08)' },
  nightlife: { label: 'Ночная жизнь', color: '#9333EA', bg: 'rgba(147,51,234,0.08)' },
  wellness: { label: 'Велнес', color: '#0891B2', bg: 'rgba(8,145,178,0.08)' },
  shopping: { label: 'Шопинг', color: '#B45309', bg: 'rgba(180,83,9,0.08)' },
  family: { label: 'Семейный', color: '#2563EB', bg: 'rgba(37,99,235,0.08)' },
  urban: { label: 'Городской', color: '#475569', bg: 'rgba(71,85,105,0.08)' },
  affordable: { label: 'Доступно', color: '#15803D', bg: 'rgba(21,128,61,0.08)' },
  visa_free: { label: 'Без визы', color: '#15803D', bg: 'rgba(21,128,61,0.08)' },
  safe: { label: 'Безопасно', color: '#15803D', bg: 'rgba(21,128,61,0.08)' },
  popular: { label: 'Популярно', color: '#2563EB', bg: 'rgba(37,99,235,0.08)' },
  hot_season: { label: 'Лучший сезон', color: '#B45309', bg: 'rgba(180,83,9,0.08)' },
  good_season: { label: 'Хороший сезон', color: '#15803D', bg: 'rgba(21,128,61,0.08)' },
};

const getSeasonMeta = (score: number): { label: string; color: string; dotColor: string } => {
  if (score >= 0.8) return { label: 'Лучший сезон', color: '#15803D', dotColor: '#22C55E' };
  if (score >= 0.6) return { label: 'Хороший сезон', color: '#B45309', dotColor: '#F59E0B' };
  return { label: 'Не сезон', color: '#A8A29E', dotColor: '#D6D3D1' };
};

const getMatchColor = (score: number) => {
  if (score >= 0.8) return { text: '#15803D', bg: 'rgba(21,128,61,0.08)', ring: 'rgba(21,128,61,0.2)' };
  if (score >= 0.6) return { text: '#2563EB', bg: 'rgba(37,99,235,0.08)', ring: 'rgba(37,99,235,0.2)' };
  return { text: '#B45309', bg: 'rgba(245,158,11,0.1)', ring: 'rgba(245,158,11,0.25)' };
};

const MatchRing = ({ score }: { score: number }) => {
  const pct = Math.round(score * 100);
  const { text, bg, ring } = getMatchColor(score);
  const r = 18;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;

  return (
    <div
      className="relative flex shrink-0 items-center justify-center"
      style={{ width: 48, height: 48 }}
    >
      <svg width={48} height={48} style={{ position: 'absolute', top: 0, left: 0, transform: 'rotate(-90deg)' }}>
        <circle cx={24} cy={24} r={r} fill="none" stroke={ring} strokeWidth={4} />
        <circle
          cx={24} cy={24} r={r}
          fill="none"
          stroke={text}
          strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeDashoffset={0}
        />
      </svg>
      <div
        className="relative flex flex-col items-center justify-center rounded-full"
        style={{ width: 36, height: 36, background: bg }}
      >
        <span style={{ fontSize: 11, fontWeight: 800, color: text, lineHeight: 1 }}>{pct}</span>
        <span style={{ fontSize: 7, fontWeight: 700, color: text, opacity: 0.7, lineHeight: 1 }}>%</span>
      </div>
    </div>
  );
};

type RecommendationCardProps = {
  destination: ScoredDestination;
  onClick?: () => void;
  className?: string;
};

export const RecommendationCard = ({ destination, onClick, className }: RecommendationCardProps) => {
  const flag = COUNTRY_FLAGS[destination.country_code] ?? '🌍';
  const season = getSeasonMeta(destination.season_score ?? 0);
  const topTags = destination.explanation_tags.slice(0, 3);

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full text-left transition-all active:scale-[0.98]',
        className
      )}
      style={{
        background: '#fff',
        border: '1px solid rgba(0,0,0,0.06)',
        borderRadius: 20,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      {/* Top row: flag + name + match ring */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 14,
              background: 'rgba(28,25,23,0.04)',
              border: '1px solid rgba(0,0,0,0.06)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 24,
              flexShrink: 0,
            }}
          >
            {flag}
          </div>
          <div style={{ minWidth: 0 }}>
            <p
              style={{
                fontSize: 17,
                fontWeight: 800,
                color: '#1C1917',
                letterSpacing: '-0.01em',
                lineHeight: 1.2,
                marginBottom: 2,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {destination.name}
            </p>
            <p style={{ fontSize: 13, fontWeight: 500, color: '#A8A29E', lineHeight: 1 }}>
              {destination.region}
            </p>
          </div>
        </div>
        <MatchRing score={destination.score} />
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'rgba(0,0,0,0.04)', margin: '0 -16px' }} />

      {/* Bottom row: season + cost + tags */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        {/* Left: season indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: season.dotColor,
              flexShrink: 0,
              display: 'inline-block',
            }}
          />
          <span style={{ fontSize: 12, fontWeight: 600, color: season.color }}>
            {season.label}
          </span>
        </div>

        {/* Right: daily cost */}
        {destination.avg_daily_cost_usd !== null && (
          <span style={{ fontSize: 12, fontWeight: 600, color: '#A8A29E', flexShrink: 0 }}>
            ~${Math.round(destination.avg_daily_cost_usd)}/день
          </span>
        )}
      </div>

      {/* Tags */}
      {topTags.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {topTags.map((tag) => {
            const cfg = TAG_CONFIG[tag];
            if (!cfg) return null;
            return (
              <span
                key={tag}
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: cfg.color,
                  background: cfg.bg,
                  borderRadius: 8,
                  padding: '4px 8px',
                  letterSpacing: '0.01em',
                }}
              >
                {cfg.label}
              </span>
            );
          })}
        </div>
      )}
    </button>
  );
};
