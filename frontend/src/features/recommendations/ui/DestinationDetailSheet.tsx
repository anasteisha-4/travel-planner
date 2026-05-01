import {
  Drawer,
  DrawerContent,
  DrawerOverlay,
  DrawerPortal,
} from '@/shared/ui';
import type { UserProfileV2 } from '@/entities/user';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useBudgetPrediction } from '../model/useBudgetPrediction';
import type { BudgetPredictResponse, ScoreBreakdown, ScoredDestination } from '../model/types';

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$', EUR: '€', RUB: '₽', GBP: '£', TRY: '₺',
  THB: '฿', AED: 'AED', KZT: '₸', GEL: '₾', AMD: '֏',
  JPY: '¥', CNY: '¥',
};

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

const DURATION_OPTIONS = [
  { value: 3, label: '3 дня' },
  { value: 5, label: '5 дней' },
  { value: 7, label: '7 ночей' },
  { value: 10, label: '10 дней' },
  { value: 14, label: '2 недели' },
  { value: 21, label: '3 недели' },
];

const TIER_OPTIONS: { value: 'budget' | 'mid' | 'luxury'; label: string }[] = [
  { value: 'budget', label: 'Эконом' },
  { value: 'mid', label: 'Комфорт' },
  { value: 'luxury', label: 'Люкс' },
];

const TYPICAL_DURATION_MAP: Record<string, number> = {
  weekend: 3,
  short: 5,
  standard: 7,
  long: 14,
  extended: 21,
};

const formatDateParam = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const getSuggestedTripDates = (month: number, durationDays: number) => {
  const today = new Date();
  const currentMonth = today.getMonth() + 1;
  const year = month < currentMonth ? today.getFullYear() + 1 : today.getFullYear();
  const start = month === currentMonth ? today : new Date(year, month - 1, 1);
  const end = new Date(start);
  end.setDate(start.getDate() + durationDays - 1);

  return {
    startDate: formatDateParam(start),
    endDate: formatDateParam(end),
  };
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
          <span style={{ fontSize: 13, fontWeight: 600, color: '#1C1917', fontFamily: 'Manrope, sans-serif' }}>
            {label}
          </span>
          <span style={{ fontSize: 12, fontWeight: 800, color: textColor, fontFamily: 'Manrope, sans-serif', minWidth: 32, textAlign: 'right' }}>
            {pct}%
          </span>
        </div>
        <div style={{ height: 4, borderRadius: 2, background: 'rgba(28,25,23,0.07)', overflow: 'hidden' }}>
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

type TripParams = {
  duration_days: number;
  people_count: number;
  accommodation_tier: 'budget' | 'mid' | 'luxury';
};

const TripParamsControls = ({
  params,
  onChange,
}: {
  params: TripParams;
  onChange: (p: TripParams) => void;
}) => {
  const btnBase: React.CSSProperties = {
    height: 30,
    borderRadius: 8,
    border: '1px solid #E7E5E4',
    background: '#F5F5F4',
    color: '#1C1917',
    fontSize: 12,
    fontWeight: 600,
    fontFamily: 'Manrope, sans-serif',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0 10px',
    transition: 'all 0.15s',
    whiteSpace: 'nowrap' as const,
  };
  const btnActive: React.CSSProperties = {
    ...btnBase,
    background: '#2563EB',
    border: '1px solid #2563EB',
    color: '#fff',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Duration */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: '#A8A29E', letterSpacing: '0.05em', fontFamily: 'Manrope, sans-serif', minWidth: 56 }}>
          СРОК
        </span>
        <div style={{ display: 'flex', gap: 5, overflowX: 'auto', scrollbarWidth: 'none' }}>
          {DURATION_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              style={params.duration_days === opt.value ? btnActive : btnBase}
              onClick={() => onChange({ ...params, duration_days: opt.value })}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* People */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: '#A8A29E', letterSpacing: '0.05em', fontFamily: 'Manrope, sans-serif', minWidth: 56 }}>
          ЛЮДЕЙ
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            type="button"
            onClick={() => onChange({ ...params, people_count: Math.max(1, params.people_count - 1) })}
            style={{
              width: 30,
              height: 30,
              borderRadius: 8,
              border: '1px solid #E7E5E4',
              background: '#fff',
              color: '#1C1917',
              fontSize: 16,
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            −
          </button>
          <span style={{ fontSize: 15, fontWeight: 700, color: '#1C1917', fontFamily: 'Manrope, sans-serif', minWidth: 20, textAlign: 'center' }}>
            {params.people_count}
          </span>
          <button
            type="button"
            onClick={() => onChange({ ...params, people_count: Math.min(8, params.people_count + 1) })}
            style={{
              width: 30,
              height: 30,
              borderRadius: 8,
              border: '1px solid #2563EB',
              background: '#2563EB',
              color: '#fff',
              fontSize: 16,
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            +
          </button>
        </div>
      </div>

      {/* Tier */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: '#A8A29E', letterSpacing: '0.05em', fontFamily: 'Manrope, sans-serif', minWidth: 56 }}>
          КЛАСС
        </span>
        <div style={{ display: 'flex', gap: 5 }}>
          {TIER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              style={params.accommodation_tier === opt.value ? btnActive : btnBase}
              onClick={() => onChange({ ...params, accommodation_tier: opt.value })}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

const BudgetBlock = ({
  destination,
  tripParams,
  currency,
  data,
  isLoading,
}: {
  destination: ScoredDestination;
  tripParams: TripParams;
  currency: string;
  data?: BudgetPredictResponse;
  isLoading: boolean;
}) => {
  const currencySymbol = CURRENCY_SYMBOLS[currency] ?? currency;

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
            В ДЕНЬ / ЧЕЛ
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
    { label: 'ОПТИМИСТ', sublabel: 'лучший сценарий', value: data.total_min, color: '#16A34A', bg: 'rgba(22,163,74,0.07)', border: 'rgba(22,163,74,0.18)' },
    { label: 'РЕАЛИСТ', sublabel: 'типичная поездка', value: data.total_mid, color: '#2563EB', bg: 'rgba(37,99,235,0.07)', border: 'rgba(37,99,235,0.18)' },
    { label: 'ПЕССИМИСТ', sublabel: 'с запасом', value: data.total_max, color: '#7C3AED', bg: 'rgba(124,58,237,0.06)', border: 'rgba(124,58,237,0.18)' },
  ];

  const tierLabel = TIER_OPTIONS.find((t) => t.value === tripParams.accommodation_tier)?.label ?? '';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
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
            <p style={{ fontSize: 8, fontWeight: 800, color: t.color, letterSpacing: '0.06em', fontFamily: 'Manrope, sans-serif', textTransform: 'uppercase' as const }}>
              {t.label}
            </p>
            <p style={{ fontSize: 18, fontWeight: 800, color: '#1C1917', fontFamily: 'Manrope, sans-serif', letterSpacing: '-0.02em', lineHeight: 1 }}>
              {currencySymbol}{Math.round(t.value).toLocaleString('ru-RU')}
            </p>
            <p style={{ fontSize: 9, fontWeight: 500, color: '#A8A29E', fontFamily: 'Manrope, sans-serif' }}>
              {t.sublabel}
            </p>
          </div>
        ))}
      </div>
      <p style={{ fontSize: 11, color: '#A8A29E', fontFamily: 'Manrope, sans-serif', textAlign: 'center' }}>
        {tripParams.duration_days} {tripParams.duration_days === 3 ? 'дня' : 'дней'} · {tripParams.people_count} чел · {tierLabel} · {currency}
      </p>
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
  const qc = useQueryClient();

  const profileCached = qc.getQueryData<UserProfileV2>(['profile']);
  const defaultDuration = TYPICAL_DURATION_MAP[profileCached?.typical_duration ?? 'standard'] ?? 7;
  const defaultTier: 'budget' | 'mid' | 'luxury' = (() => {
    const mid = ((profileCached?.budget_min_usd ?? 0) + (profileCached?.budget_max_usd ?? 2000)) / 2;
    if (mid < 800) return 'budget';
    if (mid < 5000) return 'mid';
    return 'luxury';
  })();

  const [tripParams, setTripParams] = useState<TripParams>({
    duration_days: defaultDuration,
    people_count: 2,
    accommodation_tier: defaultTier,
  });
  const currency = profileCached?.preferred_currency ?? 'RUB';
  const budgetPredictionParams = destination
    ? {
        destination_id: destination.destination_id,
        duration_days: tripParams.duration_days,
        people_count: tripParams.people_count,
        travel_month: month,
        accommodation_tier: tripParams.accommodation_tier,
        currency,
      }
    : null;
  const { data: budgetPrediction, isLoading: isBudgetLoading } =
    useBudgetPrediction(budgetPredictionParams);

  const handleCreateTrip = () => {
    if (!destination) return;
    const dates = getSuggestedTripDates(month, tripParams.duration_days);
    const params = new URLSearchParams({
      destination: destination.name,
      destination_id: destination.destination_id,
      people_count: String(tripParams.people_count),
      currency,
      start_date: dates.startDate,
      end_date: dates.endDate,
    });
    if (profileCached?.origin_city_name) {
      params.set('departure_city', profileCached.origin_city_name);
    }
    if (budgetPrediction?.total_mid) {
      params.set('budget', String(Math.round(budgetPrediction.total_mid)));
    }
    onClose();
    navigate(`/trips/new?${params.toString()}`);
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
          <div style={{ padding: '0 20px 18px', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
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
                <p style={{ fontSize: 13, fontWeight: 500, color: '#A8A29E', fontFamily: 'Manrope, sans-serif' }}>
                  {destination.region}
                </p>
              </div>
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
                <p style={{ fontSize: 22, fontWeight: 800, color: matchColor, fontFamily: 'Manrope, sans-serif', lineHeight: 1, marginBottom: 1 }}>
                  {matchPct}
                </p>
                <p style={{ fontSize: 8, fontWeight: 800, color: matchColor, opacity: 0.65, fontFamily: 'Manrope, sans-serif', letterSpacing: '0.06em' }}>
                  %СОВП
                </p>
              </div>
            </div>
          </div>

          <div style={{ height: 1, background: 'rgba(0,0,0,0.05)', margin: '0 20px', flexShrink: 0 }} />

          {/* Scrollable body */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '18px 20px 0' }}>
            {/* Score breakdown */}
            <p style={{ fontSize: 10, fontWeight: 700, color: '#A8A29E', letterSpacing: '0.07em', textTransform: 'uppercase' as const, fontFamily: 'Manrope, sans-serif', marginBottom: 12 }}>
              Совпадение по критериям
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 9, marginBottom: 20 }}>
              {breakdownEntries.map(([key, value]) => {
                const meta = BREAKDOWN_META[key];
                return (
                  <ScoreRow key={key} label={meta.label} icon={meta.icon} value={value} meta={meta} />
                );
              })}
            </div>

            <div style={{ height: 1, background: 'rgba(0,0,0,0.05)', margin: '0 -20px 18px' }} />

            {/* Budget section */}
            <p style={{ fontSize: 10, fontWeight: 700, color: '#A8A29E', letterSpacing: '0.07em', textTransform: 'uppercase' as const, fontFamily: 'Manrope, sans-serif', marginBottom: 12 }}>
              Прогноз бюджета
            </p>

            {/* Trip params controls */}
            <div
              style={{
                marginBottom: 14,
                padding: '12px 14px',
                borderRadius: 14,
                background: '#F5F5F4',
                border: '1px solid #E7E5E4',
              }}
            >
              <TripParamsControls params={tripParams} onChange={setTripParams} />
            </div>

            <div style={{ marginBottom: 20 }}>
              <BudgetBlock
                destination={destination}
                tripParams={tripParams}
                currency={currency}
                data={budgetPrediction}
                isLoading={isBudgetLoading}
              />
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
