import { Badge, Card, CardContent } from '@/shared/ui';
import { Calendar, Users, Wallet } from 'lucide-react';
import type { Trip } from '../model/types';

const STATUS_CONFIG: Record<
  string,
  { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }
> = {
  planned: { label: 'Запланирована', variant: 'secondary' },
  active: { label: 'В пути', variant: 'default' },
  completed: { label: 'Завершена', variant: 'outline' },
  cancelled: { label: 'Отменена', variant: 'destructive' },
};

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
};

export const TripCard = ({ trip, onClick }: { trip: Trip; onClick: () => void }) => {
  const statusInfo = STATUS_CONFIG[trip.status] ?? STATUS_CONFIG.planned;

  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md active:scale-[0.98]"
      onClick={onClick}
    >
      <CardContent className="space-y-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 space-y-0.5">
            <h3 className="truncate text-lg font-bold tracking-tight">{trip.destination}</h3>
            {trip.departure_city && (
              <p className="flex items-center gap-1 text-sm text-muted-foreground">
                <span className="truncate">из {trip.departure_city}</span>
              </p>
            )}
          </div>
          <Badge variant={statusInfo.variant} className="shrink-0 text-xs">
            {statusInfo.label}
          </Badge>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            {formatDate(trip.start_date)} — {formatDate(trip.end_date)}
          </span>
          <span className="flex items-center gap-1">
            <Users className="h-3.5 w-3.5" />
            {trip.people_count}
          </span>
          {trip.budget && (
            <span className="flex items-center gap-1">
              <Wallet className="h-3.5 w-3.5" />
              {trip.budget.toLocaleString('ru-RU')} {trip.currency}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
