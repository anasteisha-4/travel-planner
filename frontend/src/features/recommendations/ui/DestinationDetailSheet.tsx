import {
  Drawer,
  DrawerContent,
  DrawerOverlay,
  DrawerPortal,
} from '@/shared/ui';
import { useNavigate } from 'react-router-dom';
import { useBudgetPrediction } from '../model/useBudgetPrediction';
import type { ScoreBreakdown, ScoredDestination } from '../model/types';

const COUNTRY_FLAGS: Record<string, string> = {
  AF: '🇦🇫', AL: '🇦🇱', DZ: '🇩🇿', AD: '🇦🇩', AO: '🇦🇴', AR: '🇦🇷', AM: '🇦🇲',
  AU: '🇦🇺', AT: '🇦🇹', AZ: '🇦🇿', BY: '🇧🇾', BE: '🇧🇪', BR: '🇧🇷', BG: '🇧🇬',
  CA: '🇨🇦', CL: '🇨🇱', CN: '🇨🇳', CO: '🇨🇴', HR: '🇭🇷', CU: '🇨🇺', CY: '🇨🇾',
  CZ: '🇨🇿', DK: '🇩🇰', EG: '🇪🇬', EE: '🇪🇪', FI: '🇫🇮', FR: '🇫🇷', GE: '🇬🇪',
  DE: '🇩🇪', GR: '🇬🇷', HU: '🇭🇺', IS: '🇮🇸', IN: '🇮🇳', ID: '🇮🇩', IR: '🇮🇷',
  IE: '🇮🇪', IL: '🇮🇱', IT: '🇮🇹', JP: '🇯🇵', JO: '🇯🇴', KZ: '🇰🇿', KE: '🇰🇪',
  KR: '🇰🇷', KW: '🇰🇼', KG: '🇰🇬', LV: '🇱🇻', LB: '🇱🇧', LT: '🇱🇹', LU: '🇱🇺',
  MY: '🇲🇾', MV: '🇲🇻', MT: '🇲🇹', MX: '🇲🇽', MD: '🇲🇩', MC: '🇲🇨', MN: '🇲🇳',
  ME: '🇲🇪', MA: '🇲🇦', MM: '🇲🇲', NP: '🇳🇵', NL: '🇳🇱', NZ: '🇳🇿', NG: '🇳🇬',
  NO: '🇳🇴', OM: '🇴🇲', PK: '🇵🇰', PA: '🇵🇦', PY: '🇵🇾', PE: '🇵🇪', PH: '🇵🇭',
  PL: '🇵🇱', PT: '🇵🇹', QA: '🇶🇦', RO: '🇷🇴', RU: '🇷🇺', SA: '🇸🇦', SN: '🇸🇳',
  RS: '🇷🇸', SG: '🇸🇬', SK: '🇸🇰', SI: '🇸🇮', ZA: '🇿🇦', ES: '🇪🇸', LK: '🇱🇰',
  SE: '🇸🇪', CH: '🇨🇭', TW: '🇹🇼', TJ: '🇹🇯', TZ: '🇹🇿', TH: '🇹🇭', TN: '🇹🇳',
  TR: '🇹🇷', TM: '🇹🇲', UA: '🇺🇦', AE: '🇦🇪', GB: '🇬🇧', US: '🇺🇸', UY: '🇺🇾',
  UZ: '🇺🇿', VN: '🇻🇳', YE: '🇾🇪', ZM: '🇿🇲', ZW: '🇿🇼',
};

const BREAKDOWN_META: Record<
  keyof ScoreBreakdown,
  { label: string; icon: string; highColor: string; highBg: string; midColor: string; midBg: string }
> = {
  activity_match: { label: 'Активности', icon: '🎯', highColor: '#2563EB', highBg: 'rgba(37,99,235,0.1)', midColor: '#2563EB', midBg: 'rgba(37,99,235,0.06)' },
  budget_fit:     { label: 'Бюджет',      icon: '💰', highColor: '#16A34A', highBg: 'rgba(22,163,74,0.1)',  midColor: '#B45309', midBg: 'rgba(180,83,9,0.07)'  },
  season:         { label: 'Сезон',       icon: '🌤', highColor: '#16A34A', highBg: 'rgba(22,163,74,0.1)',  midColor: '#B45309', midBg: 'rgba(180,83,9,0.07)'  },
  safety:         { label: 'Безопасность',icon: '🛡', highColor: '#16A34A', highBg: 'rgba(22,163,74,0.1)',  midColor: '#B45309', midBg: 'rgba(180,83,9,0.07)'  },
  visa:           { label: 'Виза',        icon: '🛂', highColor: '#16A34A', highBg: 'rgba(22,163,74,0.1)',  midColor: '#B45309', midBg: 'rgba(180,83,9,0.07)'  },
  language:       { label: 'Язык',        icon: '💬', highColor: '#2563EB', highBg: 'rgba(37,99,235,0.1)', midColor: '#2563EB', midBg: 'rgba(37,99,235,0.06)' },
  crowd:          { label: 'Людность',    icon: '👥', highColor: '#2563EB', highBg: 'rgba(37,99,235,0.1)', midColor: '#2563EB', midBg: 'rgba(37,99,235,0.06)' },
  climate:        { label: 'Климат',      icon: '🌡', highColor: '#16A34A', highBg: 'rgba(22,163,74,0.1)',  midColor: '#B45309', midBg: 'rgba(180,83,9,0.07)'  },
  connectivity:   { label: 'Доступность', icon: '✈️', highColor: '#2563EB', highBg: 'rgba(37,99,235,0.1)', midColor: '#2563EB', midBg: 'rgba(37,99,235,0.06)' },
};

const ScoreRow = ({
  label,
  icon,
  value,
  meta,
}: {
  label: string;
  icon: string;
  value: number;
  meta: (typeof BREAKDOWN_META)[keyof ScoreBreakdown];
}) => {
  const pct = Math.round(value * 100);
  const isHigh = value >= 0.65;
  const barColor = value >= 0.65 ? meta.highColor : value >= 0.35 ? meta.midColor : '#D6D3D1';
  const textColor = value >= 0.65 ? meta.highColor : value >= 0.35 ? meta.midColor : '#A8A29E';
  const tileBg = value >= 0.65 ? meta.highBg : value >= 0.35 ? meta.midBg : 'rgba(28,25,23,0.04)';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
      <div
        style={{
          width: 34,
          height: 34,
          borderRadius: 10,
          background: tileBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 16,
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
          <span
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: '#1C1917',
              fontFamily: 'Manrope, sans-serif',
            }}
          >
            {label}
          </span>
          <span
            style={{
              fontSize: 12,
              fontWeight: 800,
              color: textColor,
              fontFamily: 'Manrope, sans-serif',
              minWidth: 32,
              textAlign: 'right',
            }}
          >
            {pct}%
          </span>
        </div>
        <div
          style={{
            height: 4,
            borderRadius: 2,
            background: 'rgba(28,25,23,0.07)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${pct}%`,
              borderRadius: 2,
              background: barColor,
              transition: 'width 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)',
            }}
          />
        </div>
      </div>
      {isHigh && (
        <span style={{ fontSize: 11, color: meta.highColor, flexShrink: 0 }}>✓</span>
      )}
    </div>
  );
};

const BudgetBlock = ({
  destination,
  month,
}: {
  destination: ScoredDestination;
  month: number;
}) => {
  const { data, isLoading } = useBudgetPrediction({
    destination_id: destination.destination_id,
    duration_days: 7,
    people_count: 2,
    travel_month: month,
  });

  if (isLoading) {
    return (
      <div style={{ display: 'flex', gap: 8 }}>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: 78,
              borderRadius: 16,
              background: 'rgba(28,25,23,0.04)',
              animation: 'pulse 1.5s ease-in-out infinite',
            }}
          />
        ))}
      </div>
    );
  }

  if (!data) {
    return destination.avg_daily_cost_usd !== null ? (
      <div
        style={{
          padding: '16px',
          borderRadius: 16,
          background: 'rgba(37,99,235,0.05)',
          border: '1px solid rgba(37,99,235,0.12)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <p style={{ fontSize: 11, fontWeight: 700, color: '#A8A29E', letterSpacing: '0.05em', fontFamily: 'Manrope, sans-serif', marginBottom: 2 }}>
            В ДЕНЬ
          </p>
          <p style={{ fontSize: 26, fontWeight: 800, color: '#1C1917', fontFamily: 'Manrope, sans-serif', letterSpacing: '-0.02em' }}>
            ~${Math.round(destination.avg_daily_cost_usd)}
          </p>
        </div>
        <span style={{ fontSize: 32 }}>💳</span>
      </div>
    ) : (
      <div
        style={{
          padding: '14px',
          borderRadius: 16,
          background: 'rgba(28,25,23,0.03)',
          border: '1px solid rgba(0,0,0,0.06)',
          textAlign: 'center',
        }}
      >
        <p style={{ fontSize: 13, color: '#A8A29E', fontFamily: 'Manrope, sans-serif' }}>
          Данные недоступны
        </p>
      </div>
    );
  }

  const tiers = [
    { label: 'ЭКОНОМ', value: data.total_min, color: '#16A34A', bg: 'rgba(22,163,74,0.07)', border: 'rgba(22,163,74,0.18)' },
    { label: 'КОМФОРТ', value: data.total_mid, color: '#2563EB', bg: 'rgba(37,99,235,0.07)', border: 'rgba(37,99,235,0.18)' },
    { label: 'ПРЕМИУМ', value: data.total_max, color: '#7C3AED', bg: 'rgba(124,58,237,0.06)', border: 'rgba(124,58,237,0.18)' },
  ];

  return (
    <div style={{ display: 'flex', gap: 8 }}>
      {tiers.map((t) => (
        <div
          key={t.label}
          style={{
            flex: 1,
            padding: '12px 8px 10px',
            borderRadius: 16,
            background: t.bg,
            border: `1px solid ${t.border}`,
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            gap: 3,
          }}
        >
          <p
            style={{
              fontSize: 9,
              fontWeight: 800,
              color: t.color,
              letterSpacing: '0.06em',
              fontFamily: 'Manrope, sans-serif',
            }}
          >
            {t.label}
          </p>
          <p
            style={{
              fontSize: 18,
              fontWeight: 800,
              color: '#1C1917',
              fontFamily: 'Manrope, sans-serif',
              letterSpacing: '-0.02em',
              lineHeight: 1,
            }}
          >
            ${Math.round(t.value)}
          </p>
          <p
            style={{
              fontSize: 10,
              fontWeight: 500,
              color: '#A8A29E',
              fontFamily: 'Manrope, sans-serif',
            }}
          >
            7н · 2 чел
          </p>
        </div>
      ))}
    </div>
  );
};

type DestinationDetailSheetProps = {
  destination: ScoredDestination | null;
  month: number;
  open: boolean;
  onClose: () => void;
};

export const DestinationDetailSheet = ({
  destination,
  month,
  open,
  onClose,
}: DestinationDetailSheetProps) => {
  const navigate = useNavigate();

  const handleCreateTrip = () => {
    if (!destination) return;
    onClose();
    navigate(
      `/trips/new?destination=${encodeURIComponent(destination.name)}&destination_id=${destination.destination_id}`
    );
  };

  if (!destination) return null;

  const flag = COUNTRY_FLAGS[destination.country_code] ?? '🌍';
  const matchPct = Math.round(destination.score * 100);
  const matchColor =
    destination.score >= 0.8 ? '#16A34A' : destination.score >= 0.6 ? '#2563EB' : '#B45309';
  const matchBg =
    destination.score >= 0.8
      ? 'rgba(22,163,74,0.08)'
      : destination.score >= 0.6
        ? 'rgba(37,99,235,0.08)'
        : 'rgba(245,158,11,0.08)';
  const matchBorder =
    destination.score >= 0.8
      ? 'rgba(22,163,74,0.25)'
      : destination.score >= 0.6
        ? 'rgba(37,99,235,0.25)'
        : 'rgba(245,158,11,0.35)';

  const breakdownEntries = (Object.entries(destination.score_breakdown) as [string, number][])
    .filter(([key]) => key in BREAKDOWN_META)
    .sort((a, b) => b[1] - a[1]) as [keyof typeof BREAKDOWN_META, number][];

  return (
    <Drawer open={open} onOpenChange={(v) => !v && onClose()}>
      <DrawerPortal>
        <DrawerOverlay />
        <DrawerContent
          style={{
            maxHeight: '92dvh',
            display: 'flex',
            flexDirection: 'column',
            padding: 0,
          }}
        >
          {/* Hero header */}
          <div
            style={{
              padding: '0 20px 18px',
              flexShrink: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              {/* Flag block */}
              <div
                style={{
                  width: 68,
                  height: 68,
                  borderRadius: 22,
                  background: 'rgba(28,25,23,0.04)',
                  border: '1px solid rgba(0,0,0,0.06)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 40,
                  flexShrink: 0,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                }}
              >
                {flag}
              </div>

              {/* Name + region */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <p
                  style={{
                    fontSize: 24,
                    fontWeight: 800,
                    color: '#1C1917',
                    letterSpacing: '-0.025em',
                    lineHeight: 1.15,
                    fontFamily: 'Manrope, sans-serif',
                    marginBottom: 4,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {destination.name}
                </p>
                <p
                  style={{
                    fontSize: 13,
                    fontWeight: 500,
                    color: '#A8A29E',
                    fontFamily: 'Manrope, sans-serif',
                  }}
                >
                  {destination.region}
                </p>
              </div>

              {/* Match badge */}
              <div
                style={{
                  flexShrink: 0,
                  padding: '10px 13px',
                  borderRadius: 18,
                  background: matchBg,
                  border: `1.5px solid ${matchBorder}`,
                  textAlign: 'center',
                  minWidth: 56,
                }}
              >
                <p
                  style={{
                    fontSize: 22,
                    fontWeight: 800,
                    color: matchColor,
                    fontFamily: 'Manrope, sans-serif',
                    lineHeight: 1,
                    marginBottom: 1,
                  }}
                >
                  {matchPct}
                </p>
                <p
                  style={{
                    fontSize: 8,
                    fontWeight: 800,
                    color: matchColor,
                    opacity: 0.65,
                    fontFamily: 'Manrope, sans-serif',
                    letterSpacing: '0.06em',
                  }}
                >
                  %СОВП
                </p>
              </div>
            </div>
          </div>

          {/* Divider */}
          <div style={{ height: 1, background: 'rgba(0,0,0,0.05)', margin: '0 20px', flexShrink: 0 }} />

          {/* Scrollable body */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '18px 20px 0',
            }}
          >
            {/* Score breakdown section */}
            <p
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: '#A8A29E',
                letterSpacing: '0.07em',
                textTransform: 'uppercase' as const,
                fontFamily: 'Manrope, sans-serif',
                marginBottom: 12,
              }}
            >
              Совпадение по критериям
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 9, marginBottom: 20 }}>
              {breakdownEntries.map(([key, value]) => {
                const meta = BREAKDOWN_META[key];
                return (
                  <ScoreRow
                    key={key}
                    label={meta.label}
                    icon={meta.icon}
                    value={value}
                    meta={meta}
                  />
                );
              })}
            </div>

            {/* Divider */}
            <div style={{ height: 1, background: 'rgba(0,0,0,0.05)', margin: '0 -20px 18px' }} />

            {/* Budget section */}
            <p
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: '#A8A29E',
                letterSpacing: '0.07em',
                textTransform: 'uppercase' as const,
                fontFamily: 'Manrope, sans-serif',
                marginBottom: 12,
              }}
            >
              Прогноз бюджета
            </p>
            <div style={{ marginBottom: 20 }}>
              <BudgetBlock destination={destination} month={month} />
            </div>
          </div>

          {/* Sticky CTA footer */}
          <div
            style={{
              flexShrink: 0,
              padding: '12px 20px',
              paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 12px)',
              background: '#fff',
              borderTop: '1px solid rgba(0,0,0,0.05)',
            }}
          >
            <button
              type="button"
              onClick={handleCreateTrip}
              style={{
                width: '100%',
                height: 54,
                borderRadius: 16,
                background: '#2563EB',
                border: 'none',
                color: '#fff',
                fontSize: 15,
                fontWeight: 700,
                fontFamily: 'Manrope, sans-serif',
                cursor: 'pointer',
                boxShadow: '0 4px 16px rgba(37,99,235,0.28)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                letterSpacing: '-0.01em',
              }}
            >
              <span>✈️</span>
              Создать поездку
            </button>
          </div>
        </DrawerContent>
      </DrawerPortal>
    </Drawer>
  );
};
