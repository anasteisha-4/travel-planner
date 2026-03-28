import type { TripDetailOutletContext } from './TripDetailPage';
import { PlaceDiary } from '@/features/places';
import { useOutletContext } from 'react-router-dom';

export const TripDiaryTab = () => {
  const { trip } = useOutletContext<TripDetailOutletContext>();

  return (
    <div className="min-h-0 flex-1">
      <PlaceDiary trip={trip} />
    </div>
  );
};
