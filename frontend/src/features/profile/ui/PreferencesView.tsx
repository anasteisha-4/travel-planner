import { BUDGET_LIMITS, CURRENCIES, TRAVEL_TYPES, TRIP_DURATIONS } from '@/shared/config';
import { Badge, Card, CardContent } from '@/shared/ui';
import { Compass, DollarSign, Globe, Heart, MessageSquare, Plane, Timer } from 'lucide-react';

type PreferencesData = {
  travel_types: string[];
  favorite_destinations: string | null;
  currency: string;
  budget_min: number | null;
  budget_max: number | null;
  trip_duration: string | null;
  departure_city: string | null;
  additional_info: string | null;
};

const getCurrencyLabel = (code: string) => CURRENCIES.find((c) => c.value === code)?.label ?? code;

const getDurationLabel = (id: string) => TRIP_DURATIONS.find((d) => d.id === id)?.label ?? id;

const getTravelTypeLabel = (id: string) => TRAVEL_TYPES.find((t) => t.id === id)?.label ?? id;

const formatBudget = (min: number, max: number, currency: string) => {
  const config = BUDGET_LIMITS[currency] ?? BUDGET_LIMITS.RUB;
  return `${config.format(min)} — ${config.format(max)}`;
};

export const PreferencesView = ({ preferences }: { preferences: PreferencesData }) => {
  const items: { icon: typeof Heart; label: string; value: React.ReactNode }[] = [];

  if (preferences.travel_types.length > 0) {
    items.push({
      icon: Heart,
      label: 'Виды отдыха',
      value: (
        <div className="flex flex-wrap gap-x-1.5 gap-y-2.5">
          {preferences.travel_types.map((id) => (
            <Badge key={id} variant="secondary" className="py-0.5 text-xs">
              {getTravelTypeLabel(id)}
            </Badge>
          ))}
        </div>
      ),
    });
  }

  if (preferences.favorite_destinations) {
    items.push({
      icon: Globe,
      label: 'Направления',
      value: <span className="text-sm">{preferences.favorite_destinations}</span>,
    });
  }

  if (preferences.currency) {
    items.push({
      icon: DollarSign,
      label: 'Валюта',
      value: <span className="text-sm font-medium">{getCurrencyLabel(preferences.currency)}</span>,
    });
  }

  if (preferences.budget_min !== null && preferences.budget_max !== null) {
    items.push({
      icon: Compass,
      label: 'Бюджет',
      value: (
        <span className="text-sm font-medium">
          {formatBudget(preferences.budget_min, preferences.budget_max, preferences.currency)}
        </span>
      ),
    });
  }

  if (preferences.trip_duration) {
    items.push({
      icon: Timer,
      label: 'Длительность',
      value: (
        <span className="text-sm font-medium">{getDurationLabel(preferences.trip_duration)}</span>
      ),
    });
  }

  if (preferences.departure_city) {
    items.push({
      icon: Plane,
      label: 'Город отправления',
      value: <span className="text-sm font-medium">{preferences.departure_city}</span>,
    });
  }

  if (preferences.additional_info) {
    items.push({
      icon: MessageSquare,
      label: 'Дополнительно',
      value: <span className="text-sm">{preferences.additional_info}</span>,
    });
  }

  return (
    <Card>
      <CardContent className="space-y-4">
        {items.map(({ icon: Icon, label, value }) => (
          <div key={label} className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
              <Icon className="h-3.5 w-3.5" />
              {label}
            </div>
            <div className="pl-5.5">{value}</div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};
