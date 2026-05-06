import type { TripDetailOutletContext } from './TripDetailPage';
import { itineraryQueryKey, useGenerateItinerary, type ItineraryGenerateResponse, type ItineraryPlace } from '@/features/itinerary';
import { localizePoiName } from '@/shared/lib';
import { Button } from '@/shared/ui';
import { useQueryClient } from '@tanstack/react-query';
import { AlertCircle, CalendarDays, Clock3, Loader2, Map, MapPinned, RefreshCw, Route } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useOutletContext } from 'react-router-dom';

const getDurationDays = (startDate: string, endDate: string) => {
  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T00:00:00`);
  const diffMs = end.getTime() - start.getTime();
  if (!Number.isFinite(diffMs) || diffMs < 0) return 1;
  return Math.floor(diffMs / 86_400_000) + 1;
};

const getPlacesCount = (data: ItineraryGenerateResponse) =>
  data.days.reduce((total, day) => total + day.places.length, 0);

const formatDuration = (minutes: number | null) => {
  if (!minutes) return 'Длительность не указана';
  if (minutes < 60) return `${minutes} мин`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest > 0 ? `${hours} ч ${rest} мин` : `${hours} ч`;
};

const getOpeningStatus = (place: ItineraryPlace) => {
  if (!place.opening_hours) {
    return {
      label: 'Часы не указаны',
      className: 'border-stone-200 bg-stone-50 text-stone-500 dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))] dark:text-stone-400',
    };
  }

  if (place.is_open_at_midday) {
    return {
      label: 'Открыто около полудня',
      className: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-300',
    };
  }

  return {
    label: 'Может быть закрыто',
    className: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300',
  };
};

const THEME_LABELS: Record<string, string> = {
  morning: 'Утро',
  afternoon: 'День',
  evening: 'Вечер',
};

const CATEGORY_LABELS: Record<string, string> = {
  culture: 'Культура',
  museum: 'Музей',
  nature: 'Природа',
  food: 'Еда',
  adventure: 'Активность',
  viewpoint: 'Видовая точка',
  shopping: 'Шопинг',
  entertainment: 'Развлечения',
  beach: 'Пляж',
  nightlife: 'Вечер',
};

const getErrorMessage = (error: unknown) => {
  const maybeAxios = error as { response?: { data?: { error?: string; message?: string } } };
  const code = maybeAxios.response?.data?.error;
  const message = maybeAxios.response?.data?.message;
  if (code === 'ITINERARY_UNAVAILABLE') return 'Маршрут временно недоступен';
  return message || 'Маршрут временно недоступен';
};

const ItineraryEmpty = ({
  onGenerate,
  isLoading,
}: {
  onGenerate: () => void;
  isLoading: boolean;
}) => (
  <div className="trip-info-card flex flex-col items-center px-5 py-8 text-center">
    <div className="flex h-16 w-16 items-center justify-center rounded-[20px] bg-blue-50 dark:bg-blue-950/30">
      <Route className="h-7 w-7 text-[#2563EB]" />
    </div>
    <h2 className="mt-4 text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
      Маршрут по дням
    </h2>
    <p className="mt-2 max-w-[320px] text-[14px] leading-relaxed text-stone-400 dark:text-stone-500">
      Triply соберет маршрут из мест, которые подходят датам и длительности поездки
    </p>
    <Button className="mt-5 h-[52px] w-full rounded-2xl text-[15px] font-bold" onClick={onGenerate} disabled={isLoading}>
      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <MapPinned className="h-4 w-4" />}
      Сгенерировать маршрут
    </Button>
  </div>
);

const LegacyTripEmpty = () => (
  <div className="trip-info-card-muted flex flex-col items-center px-5 py-8 text-center">
    <Map className="h-8 w-8 text-stone-400 dark:text-stone-500" />
    <p className="mt-3 text-[14px] font-medium leading-relaxed text-stone-400 dark:text-stone-500">
      Маршрут доступен для поездок, созданных из направления
    </p>
  </div>
);

const Summary = ({ data }: { data: ItineraryGenerateResponse }) => (
  <div className="grid grid-cols-3 gap-2.5">
    <div className="trip-info-card px-3 py-3">
      <CalendarDays className="mb-2 h-4 w-4 text-[#2563EB]" />
      <p className="text-[20px] font-extrabold leading-none text-stone-900 dark:text-white">{data.days.length}</p>
      <p className="mt-1 text-[11px] font-semibold text-stone-400 dark:text-stone-500">дней</p>
    </div>
    <div className="trip-info-card px-3 py-3">
      <MapPinned className="mb-2 h-4 w-4 text-emerald-600 dark:text-emerald-400" />
      <p className="text-[20px] font-extrabold leading-none text-stone-900 dark:text-white">{getPlacesCount(data)}</p>
      <p className="mt-1 text-[11px] font-semibold text-stone-400 dark:text-stone-500">мест</p>
    </div>
    <div className="trip-info-card px-3 py-3">
      <Route className="mb-2 h-4 w-4 text-amber-600 dark:text-amber-400" />
      <p className="text-[20px] font-extrabold leading-none text-stone-900 dark:text-white">План</p>
      <p className="mt-1 text-[11px] font-semibold text-stone-400 dark:text-stone-500">по дням</p>
    </div>
  </div>
);

const PlaceRow = ({ place, index }: { place: ItineraryPlace; index: number }) => {
  const status = getOpeningStatus(place);

  return (
    <div className="flex gap-3 rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] px-3 py-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-stone-100 text-[13px] font-extrabold text-stone-500 dark:bg-[hsl(var(--surface-muted))] dark:text-stone-400">
        {index + 1}
      </div>
      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 text-[15px] font-bold leading-snug text-stone-900 dark:text-white">
          {place.display_name ?? place.name_ru ?? localizePoiName(place.name)}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[11px] font-semibold text-stone-500 dark:bg-[hsl(var(--surface-muted))] dark:text-stone-400">
            {CATEGORY_LABELS[place.category] ?? place.category}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-700 dark:bg-blue-950/30 dark:text-blue-300">
            <Clock3 className="h-3 w-3" />
            {formatDuration(place.visit_duration_minutes)}
          </span>
        </div>
        <div className={`mt-2 inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold ${status.className}`}>
          {status.label}
        </div>
      </div>
    </div>
  );
};

const ItineraryResult = ({
  data,
  onRefresh,
  isLoading,
}: {
  data: ItineraryGenerateResponse;
  onRefresh: () => void;
  isLoading: boolean;
}) => (
  <div className="flex flex-col gap-3">
    <Summary data={data} />
    {!data.has_template && (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-900/50 dark:bg-amber-950/30">
        <p className="text-[14px] font-semibold text-amber-700 dark:text-amber-300">
          Для этого направления пока нет шаблона маршрута
        </p>
      </div>
    )}
    {data.days.map((day) => (
      <section key={day.day} className="trip-info-card flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              День {day.day}
            </p>
            <h2 className="mt-1 text-[18px] font-extrabold text-stone-900 dark:text-white">
              {THEME_LABELS[day.theme] ?? day.theme}
            </h2>
          </div>
          <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-semibold text-stone-500 dark:bg-[hsl(var(--surface-muted))] dark:text-stone-400">
            {day.places.length} мест
          </span>
        </div>
        {day.places.length > 0 ? (
          <div className="flex flex-col gap-2">
            {day.places.map((place, index) => (
              <PlaceRow key={place.id} place={place} index={index} />
            ))}
          </div>
        ) : (
          <p className="rounded-2xl bg-stone-50 px-4 py-3 text-[13px] font-medium text-stone-400 dark:bg-[hsl(var(--surface-muted))]/60 dark:text-stone-500">
            Нет подходящих мест для этого дня
          </p>
        )}
      </section>
    ))}
    <Button
      variant="outline"
      className="h-[52px] rounded-2xl border-stone-200 bg-stone-100 text-[15px] font-bold text-stone-700 dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))] dark:text-stone-200"
      onClick={onRefresh}
      disabled={isLoading}
    >
      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
      Обновить маршрут
    </Button>
  </div>
);

export const TripItineraryTab = () => {
  const { trip } = useOutletContext<TripDetailOutletContext>();
  const queryClient = useQueryClient();
  const mutation = useGenerateItinerary();
  const durationDays = useMemo(() => getDurationDays(trip.start_date, trip.end_date), [trip.end_date, trip.start_date]);
  const cacheKey = trip.destination_id
    ? itineraryQueryKey(trip.id, trip.destination_id, trip.start_date, durationDays)
    : null;
  const cached = cacheKey ? queryClient.getQueryData<ItineraryGenerateResponse>(cacheKey) : undefined;
  const [generated, setGenerated] = useState<ItineraryGenerateResponse | null>(cached ?? null);
  const errorMessage = mutation.isError ? getErrorMessage(mutation.error) : null;

  const handleGenerate = () => {
    if (!trip.destination_id) return;
    mutation.mutate(
      {
        tripId: trip.id,
        params: {
          destination_id: trip.destination_id,
          duration_days: durationDays,
          start_date: trip.start_date,
        },
      },
      {
        onSuccess: setGenerated,
      }
    );
  };

  if (!trip.destination_id) {
    return (
      <div className="flex-1 overflow-y-auto px-5 pb-24 pt-4">
        <LegacyTripEmpty />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-5 pb-24 pt-4">
      <div className="flex flex-col gap-3">
        {errorMessage && (
          <div className="flex items-start gap-2 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 dark:border-red-900/50 dark:bg-red-950/30">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500 dark:text-red-400" />
            <p className="text-[13px] font-semibold text-red-600 dark:text-red-300">{errorMessage}</p>
          </div>
        )}
        {generated ? (
          <ItineraryResult data={generated} onRefresh={handleGenerate} isLoading={mutation.isPending} />
        ) : (
          <ItineraryEmpty onGenerate={handleGenerate} isLoading={mutation.isPending} />
        )}
      </div>
    </div>
  );
};
