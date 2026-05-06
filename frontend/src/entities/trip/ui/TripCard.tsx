import type { Trip } from '../model/types';
import { localizeDestinationName } from '@/shared/lib';
import { StatusBadge } from '@/shared/ui';
import { Calendar, Users, Wallet } from 'lucide-react';

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
};

export const TripCard = ({ trip, onClick }: { trip: Trip; onClick: () => void }) => (
  <div
    className="trip-info-card cursor-pointer transition-all active:scale-[0.98]"
    onClick={onClick}
  >
    <div className="mb-3 flex items-start justify-between gap-3">
      <div className="min-w-0">
        <h3 className="truncate text-[17px] font-extrabold tracking-tight text-stone-900 dark:text-white">
          {localizeDestinationName(trip.destination)}
        </h3>
        {trip.departure_city && (
          <p className="truncate text-[13px] font-medium text-stone-400 dark:text-stone-500">
            из {trip.departure_city}
          </p>
        )}
      </div>
      <StatusBadge status={trip.status} />
    </div>
    <div className="flex items-center gap-4 text-[12px] font-medium text-stone-400 dark:text-stone-500">
      <span className="flex items-center gap-1.5">
        <Calendar className="h-3.5 w-3.5" />
        {formatDate(trip.start_date)} — {formatDate(trip.end_date)}
      </span>
      <span className="flex items-center gap-1.5">
        <Users className="h-3.5 w-3.5" />
        {trip.people_count}
      </span>
      {trip.budget && (
        <span className="flex items-center gap-1.5">
          <Wallet className="h-3.5 w-3.5" />
          {trip.budget.toLocaleString('ru-RU')} {trip.currency}
        </span>
      )}
    </div>
  </div>
);
