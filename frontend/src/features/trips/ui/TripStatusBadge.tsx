import type { TripStatus } from '@/entities/trip';
import { Badge } from '@/shared/ui';

const STATUS_CONFIG: Record<
  TripStatus,
  { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }
> = {
  planned: { label: 'Запланирована', variant: 'secondary' },
  active: { label: 'В пути', variant: 'default' },
  completed: { label: 'Завершена', variant: 'outline' },
  cancelled: { label: 'Отменена', variant: 'destructive' },
};

export const TripStatusBadge = ({ status }: { status: TripStatus }) => {
  const config = STATUS_CONFIG[status];
  return (
    <Badge variant={config.variant} className="text-xs">
      {config.label}
    </Badge>
  );
};
