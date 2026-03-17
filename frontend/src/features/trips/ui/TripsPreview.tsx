import { TripCard } from '@/entities/trip';
import { EmptyState, SectionLabel } from '@/shared/ui';
import { Calendar } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTrips } from '../model/useTrips';

export const TripsPreview = () => {
  const navigate = useNavigate();
  const { activeTrips, loading } = useTrips();

  return (
    <div className="flex flex-col gap-3">
      {activeTrips.length > 0 && (
        <SectionLabel
          action={
            <button
              type="button"
              onClick={() => navigate('/trips')}
              className="text-[13px] font-semibold text-primary"
            >
              Все поездки
            </button>
          }
        >
          Поездки
        </SectionLabel>
      )}

      {loading ? (
        <div className="flex flex-col gap-3">
          {[0, 1].map((i) => (
            <div key={i} className="trip-info-card animate-pulse">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div className="flex flex-col gap-1.5">
                  <div className="h-4 w-36 rounded-lg bg-stone-100 dark:bg-stone-800" />
                  <div className="h-3 w-24 rounded-lg bg-stone-100 dark:bg-stone-800" />
                </div>
                <div className="h-5 w-20 rounded-full bg-stone-100 dark:bg-stone-800" />
              </div>
              <div className="h-3 w-48 rounded-lg bg-stone-100 dark:bg-stone-800" />
            </div>
          ))}
        </div>
      ) : activeTrips.length === 0 ? (
        <EmptyState icon={Calendar} message="Нет активных поездок" />
      ) : (
        <div className="flex flex-col gap-3">
          {activeTrips.map((trip) => (
            <TripCard key={trip.id} trip={trip} onClick={() => navigate(`/trips/${trip.id}`)} />
          ))}
        </div>
      )}
    </div>
  );
};
