import { useRef } from 'react';

const MONTHS = [
  { num: 1, short: 'Янв', season: 'winter' },
  { num: 2, short: 'Фев', season: 'winter' },
  { num: 3, short: 'Мар', season: 'spring' },
  { num: 4, short: 'Апр', season: 'spring' },
  { num: 5, short: 'Май', season: 'spring' },
  { num: 6, short: 'Июн', season: 'summer' },
  { num: 7, short: 'Июл', season: 'summer' },
  { num: 8, short: 'Авг', season: 'summer' },
  { num: 9, short: 'Сен', season: 'autumn' },
  { num: 10, short: 'Окт', season: 'autumn' },
  { num: 11, short: 'Ноя', season: 'autumn' },
  { num: 12, short: 'Дек', season: 'winter' },
] as const;

const SEASON_COLOR: Record<string, string> = {
  winter: '#2563EB',
  spring: '#16A34A',
  summer: '#F59E0B',
  autumn: '#B45309',
};

const REGIONS = [
  { key: null, label: 'Все' },
  { key: 'Europe', label: 'Европа' },
  { key: 'Asia', label: 'Азия' },
  { key: 'Middle East', label: 'Ближний Восток' },
  { key: 'Africa', label: 'Африка' },
  { key: 'Americas', label: 'Америка' },
  { key: 'Oceania', label: 'Океания' },
] as const;

type RecommendationFiltersProps = {
  month: number;
  region: string | null;
  onMonthChange: (month: number) => void;
  onRegionChange: (region: string | null) => void;
};

export const RecommendationFilters = ({
  month,
  region,
  onMonthChange,
  onRegionChange,
}: RecommendationFiltersProps) => {
  const monthScrollRef = useRef<HTMLDivElement>(null);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Month selector */}
      <div
        ref={monthScrollRef}
        style={{
          display: 'flex',
          gap: 6,
          overflowX: 'auto',
          paddingBottom: 4,
          scrollbarWidth: 'none',
          msOverflowStyle: 'none',
        }}
        className="hide-scrollbar"
      >
        {MONTHS.map((m) => {
          const isActive = m.num === month;
          const accentColor = SEASON_COLOR[m.season];
          return (
            <button
              key={m.num}
              type="button"
              onClick={() => onMonthChange(m.num)}
              style={{
                flexShrink: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 4,
                padding: '8px 10px',
                borderRadius: 14,
                border: isActive ? `1.5px solid ${accentColor}` : '1.5px solid rgba(0,0,0,0.06)',
                background: isActive ? `${accentColor}14` : '#fff',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                minWidth: 44,
              }}
            >
              <span
                style={{
                  fontSize: 13,
                  fontWeight: isActive ? 800 : 500,
                  color: isActive ? accentColor : '#A8A29E',
                  fontFamily: 'Manrope, sans-serif',
                  lineHeight: 1,
                }}
              >
                {m.short}
              </span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color: isActive ? accentColor : '#C7C3BD',
                  fontFamily: 'Manrope, sans-serif',
                  lineHeight: 1,
                }}
              >
                {m.num}
              </span>
            </button>
          );
        })}
      </div>

      {/* Region pills */}
      <div
        style={{
          display: 'flex',
          gap: 6,
          overflowX: 'auto',
          paddingBottom: 4,
          scrollbarWidth: 'none',
          msOverflowStyle: 'none',
        }}
        className="hide-scrollbar"
      >
        {REGIONS.map((r) => {
          const isActive = region === r.key;
          return (
            <button
              key={String(r.key)}
              type="button"
              onClick={() => onRegionChange(r.key)}
              style={{
                flexShrink: 0,
                padding: '7px 14px',
                borderRadius: 20,
                border: isActive ? '1.5px solid #2563EB' : '1.5px solid rgba(0,0,0,0.06)',
                background: isActive ? 'rgba(37,99,235,0.08)' : '#fff',
                fontSize: 12,
                fontWeight: isActive ? 700 : 500,
                color: isActive ? '#2563EB' : '#A8A29E',
                fontFamily: 'Manrope, sans-serif',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                whiteSpace: 'nowrap',
              }}
            >
              {r.label}
            </button>
          );
        })}
      </div>
    </div>
  );
};
