import { Compass } from 'lucide-react';
import type { ScoredDestination } from '../model/types';
import { RecommendationCard } from './RecommendationCard';

type RecommendationListProps = {
  destinations: ScoredDestination[];
  onSelect: (destination: ScoredDestination) => void;
};

export const RecommendationList = ({ destinations, onSelect }: RecommendationListProps) => {
  if (destinations.length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          paddingTop: 64,
          paddingBottom: 64,
          gap: 16,
        }}
      >
        <div
          style={{
            width: 72,
            height: 72,
            borderRadius: 24,
            background: 'rgba(37,99,235,0.07)',
            border: '1px solid rgba(37,99,235,0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Compass style={{ width: 32, height: 32, color: '#2563EB', opacity: 0.7 }} />
        </div>
        <div style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 16, fontWeight: 700, color: '#1C1917', marginBottom: 4, fontFamily: 'Manrope, sans-serif' }}>
            Нет подходящих направлений
          </p>
          <p style={{ fontSize: 13, fontWeight: 500, color: '#A8A29E', fontFamily: 'Manrope, sans-serif' }}>
            Попробуйте изменить фильтры
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {destinations.map((dest) => (
        <RecommendationCard
          key={dest.destination_id}
          destination={dest}
          onClick={() => onSelect(dest)}
        />
      ))}
    </div>
  );
};
