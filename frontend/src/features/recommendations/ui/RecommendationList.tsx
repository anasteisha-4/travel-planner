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
      <div className="flex flex-col items-center justify-center px-4 py-16 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-3xl border border-primary/20 bg-primary/10">
          <Compass className="h-8 w-8 text-primary" />
        </div>
        <p className="mt-4 text-[17px] font-extrabold text-foreground">Нет подходящих направлений</p>
        <p className="mt-1 text-[13px] font-semibold text-muted-foreground">Попробуйте изменить фильтры</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
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
