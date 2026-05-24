import {
  useAddItineraryItem,
  useApproveItinerary,
  useGenerateItinerary,
  useItineraryState,
  useMoveItineraryItem,
  useRegenerateItinerary,
  useRemoveItineraryItem,
  useUnvisitItineraryItem,
  useUpdateItineraryItem,
  useVisitItineraryItem,
  type Itinerary,
  type ItineraryDay,
  type ItineraryItem,
} from '@/features/itinerary';
import { useMapSearch } from '@/features/places';
import { sendEvent } from '@/shared/api';
import {
  ensurePushNotifications,
  useGeocode,
  useReverseGeocode,
  useYandexMaps,
  type LngLat,
  type LngLatBounds,
  type YMapChild,
  type YMapInstance,
} from '@/shared/lib';
import type { LLMQualityReview } from '@/shared/model';
import { AdaptiveSheet, Button, Input, useTheme } from '@/shared/ui';
import {
  closestCenter,
  DndContext,
  PointerSensor,
  TouchSensor,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
} from '@dnd-kit/core';
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import cn from 'classnames';
import {
  Check,
  Eye,
  GripVertical,
  Info,
  Loader2,
  Map,
  MapPin,
  MapPinned,
  Pin,
  Plus,
  RefreshCw,
  Route,
  Search,
  Trash2,
  X,
} from 'lucide-react';
import type React from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import type { TripDetailOutletContext } from './TripDetailPage';

const formatDays = (count: number): string => {
  const lastDigit = Math.abs(count) % 10;
  const lastTwoDigits = Math.abs(count) % 100;

  if (lastTwoDigits >= 11 && lastTwoDigits <= 14) {
    return 'дней';
  }

  if (lastDigit === 1) {
    return 'день';
  }

  if (lastDigit >= 2 && lastDigit <= 4) {
    return 'дня';
  }

  return 'дней';
};

const formatPlaces = (count: number): string => {
  const lastDigit = count % 10;
  const lastTwoDigits = count % 100;

  if (lastTwoDigits >= 11 && lastTwoDigits <= 14) {
    return 'мест';
  }
  if (lastDigit === 1) {
    return 'место';
  }
  if (lastDigit >= 2 && lastDigit <= 4) {
    return 'места';
  }
  return 'мест';
};

const getVisibleItems = (day: ItineraryDay) => day.items.filter((item) => !item.is_removed);
const getOrderedVisibleItems = (day: ItineraryDay) =>
  getVisibleItems(day).sort((a, b) => a.order - b.order);
const isRestDay = (day: ItineraryDay) => getVisibleItems(day).length === 0;
const getDayTimeRange = (day: ItineraryDay) => {
  const items = getOrderedVisibleItems(day);
  if (items.length === 0) return null;
  const first = items[0];
  const last = items[items.length - 1];
  return {
    start: first.arrival_time ?? day.start_time,
    end: last.departure_time ?? day.end_time,
  };
};

const getPlacesCount = (itinerary: Itinerary) =>
  itinerary.days.reduce((total, day) => total + getVisibleItems(day).length, 0);

const findItemDay = (itinerary: Itinerary | null, itemId: string) => {
  if (!itinerary) return null;
  return (
    itinerary.days.find((day) =>
      day.items.some((item) => item.id === itemId && !item.is_removed)
    ) ?? null
  );
};

const getMoveTarget = (itinerary: Itinerary | null, overId: string) => {
  if (!itinerary) return null;
  const overDay = itinerary.days.find((day) => day.id === overId);
  if (overDay) {
    return { dayId: overDay.id, order: getVisibleItems(overDay).length };
  }
  for (const day of itinerary.days) {
    const items = getVisibleItems(day);
    const overIndex = items.findIndex((item) => item.id === overId);
    if (overIndex >= 0) {
      return { dayId: day.id, order: overIndex };
    }
  }
  return null;
};

type DayMapPoint = {
  item: ItineraryItem;
  coords: LngLat;
};

const formatTime = (value: string | null) => (value ? value.slice(0, 5) : '--:--');
const inputTimeValue = (value: string | null) => (value ? value.slice(0, 5) : '');

const addMinutesToTime = (value: string | null, minutes: number): string | null => {
  if (!value) return null;
  const [hours, mins] = value.slice(0, 5).split(':').map(Number);
  if (!Number.isFinite(hours) || !Number.isFinite(mins)) return null;
  const total = hours * 60 + mins + minutes;
  if (total < 0 || total >= 24 * 60) return null;
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
};

const getNextItemTime = (day: ItineraryDay) => {
  const items = getOrderedVisibleItems(day);
  const last = items.length > 0 ? items[items.length - 1] : null;
  const arrival = addMinutesToTime(last?.departure_time ?? day.start_time, last ? 30 : 0);
  const departure = addMinutesToTime(arrival, 90);
  return { arrival_time: arrival ?? undefined, departure_time: departure ?? undefined };
};

const getDayMapPoints = (day: ItineraryDay): DayMapPoint[] =>
  getVisibleItems(day).flatMap((item) => {
    const lat = Number(item.latitude);
    const lng = Number(item.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return [];
    return [{ item, coords: [lng, lat] }];
  });

const computeMapBounds = (points: DayMapPoint[]): LngLatBounds => {
  const lons = points.map((point) => point.coords[0]);
  const lats = points.map((point) => point.coords[1]);
  const pad = 0.018;
  return [
    [Math.min(...lons) - pad, Math.min(...lats) - pad],
    [Math.max(...lons) + pad, Math.max(...lats) + pad],
  ];
};

const computeMapCenter = (points: DayMapPoint[]): LngLat => {
  const lons = points.map((point) => point.coords[0]);
  const lats = points.map((point) => point.coords[1]);
  return [(Math.min(...lons) + Math.max(...lons)) / 2, (Math.min(...lats) + Math.max(...lats)) / 2];
};

const createRouteMarkerEl = (index: number, isSelected: boolean): HTMLButtonElement => {
  const el = document.createElement('button');
  el.type = 'button';
  el.style.cssText = [
    'width:30px;height:30px;border-radius:999px;border:2px solid white;',
    `background:${isSelected ? '#0f172a' : '#2563EB'};`,
    'color:white;display:flex;align-items:center;justify-content:center;',
    'font-size:12px;font-weight:800;line-height:1;cursor:pointer;',
    'box-shadow:0 8px 22px rgba(15,23,42,0.28);',
    `transform:${isSelected ? 'scale(1.18)' : 'scale(1)'};`,
    'transition:transform 0.15s ease,background 0.15s ease;',
  ].join('');
  el.textContent = String(index + 1);
  return el;
};

const formatDuration = (minutes: number | null) => {
  if (!minutes) return;
  if (minutes < 60) return `${minutes} мин`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest > 0 ? `${hours} ч ${rest} мин` : `${hours} ч`;
};

const categoryLabel = (category: string | null) => {
  const labels: Record<string, string> = {
    culture: 'Культура',
    museum: 'Музей',
    nature: 'Природа',
    food: 'Еда',
    nightlife: 'Вечер',
    shopping: 'Шопинг',
    beach: 'Пляж',
    adventure: 'Активность',
    viewpoint: 'Красивые виды',
  };
  return category ? (labels[category] ?? category) : 'Место';
};

const openingLabel = (status: string | null) => {
  if (status === 'open') return 'Открыто';
  if (status === 'closed') return 'Риск закрытия';
  return null;
};

const scoreNumber = (summary: Record<string, unknown> | null, key: string) => {
  const value = summary?.[key];
  return typeof value === 'number' ? value : 0;
};

const getTravelMinutes = (itinerary: Itinerary) => {
  const summaryValue = scoreNumber(itinerary.score_summary, 'travel_overhead_minutes');
  if (summaryValue > 0) return summaryValue;
  return itinerary.days.reduce(
    (total, day) =>
      total +
      getVisibleItems(day).reduce(
        (dayTotal, item) => dayTotal + Math.max(0, item.travel_from_previous_minutes ?? 0),
        0
      ),
    0
  );
};

const scoreMaybeNumber = (summary: Record<string, unknown> | null, key: string) => {
  const value = summary?.[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
};

const scoreBoolean = (summary: Record<string, unknown> | null, key: string) =>
  summary?.[key] === true;

const formatUsd = (amount: number) =>
  new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);

const routeNeedsRegeneration = (review?: LLMQualityReview | null) =>
  review?.status === 'reject' &&
  review.suggested_adjustments.some(
    (adjustment) =>
      adjustment.action === 'regenerate' || adjustment.action === 'generate_external_route'
  );

const itineraryErrorMessage = (error: unknown) => {
  const maybeAxios = error as { response?: { data?: { error?: string; message?: string } } };
  if (maybeAxios.response?.data?.error === 'ITINERARY_NO_FEASIBLE_ROUTE') {
    return 'Не получилось собрать подходящий маршрут. Поменяйте параметры или направление поездки.';
  }
  return (
    maybeAxios.response?.data?.message ||
    'Не получилось собрать маршрут. Поменяйте параметры или направление поездки.'
  );
};

const EmptyState = ({ onGenerate, isLoading }: { onGenerate: () => void; isLoading: boolean }) => (
  <div className="trip-info-card flex flex-col items-center px-5 py-8 text-center">
    <div className="flex h-16 w-16 items-center justify-center rounded-[20px] bg-blue-50 dark:bg-blue-950/30">
      <Route className="h-7 w-7 text-[#2563EB]" />
    </div>
    <h2 className="mt-4 text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
      Маршрут по дням
    </h2>
    <p className="mt-2 max-w-[330px] text-[14px] leading-relaxed text-stone-400 dark:text-stone-500">
      Triply соберет несколько вариантов с учетом времени, темпа, интересов и часов работы
    </p>
    <Button
      className="mt-5 h-[52px] w-full rounded-2xl text-[15px] font-bold"
      onClick={onGenerate}
      disabled={isLoading}
    >
      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <MapPinned className="h-4 w-4" />}
      Сгенерировать варианты
    </Button>
  </div>
);

const ItineraryGenerationLoader = ({
  mode,
  messageIndex,
}: {
  mode: 'generate' | 'regenerate';
  messageIndex: number;
}) => {
  const steps =
    mode === 'generate'
      ? ['Подбираю места', 'Проверяю логику дня', 'Собираю маршрут']
      : ['Ищу другой порядок', 'Обновляю точки', 'Проверяю маршрут'];

  return (
    <div className="trip-info-card overflow-hidden p-4">
      <div className="absolute inset-x-0 top-0 h-1" />
      <div className="flex items-start gap-3">
        <div className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-50 dark:bg-blue-950/30">
          <Route className="h-5 w-5 text-[#2563EB]" />
          <span className="absolute -right-1 -top-1 h-4 w-4 rounded-full bg-emerald-400 shadow-[0_0_18px_rgba(52,211,153,0.85)]" />
        </div>
        <div className="my-2 min-w-0 flex-1">
          <p className="text-[15px] font-extrabold text-stone-900 dark:text-white">
            {mode === 'generate' ? 'Собираю маршрут' : 'Собираю новый вариант'}
          </p>
          <p className="mt-1 text-[12px] font-semibold leading-relaxed text-stone-500 dark:text-stone-400">
            Генерация может занять время. Мы пришлем уведомление, когда маршрут будет готов
          </p>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {[0, 1, 2].map((index) => (
              <div
                key={index}
                className="h-1 overflow-hidden rounded-full bg-stone-100 dark:bg-[hsl(var(--surface-muted))]"
              >
                <div
                  className="h-full w-full origin-left animate-[pulse_1.4s_ease-in-out_infinite] rounded-full bg-[#2563EB]"
                  style={{ animationDelay: `${index * 180}ms` }}
                />
              </div>
            ))}
          </div>
          <p
            className="mt-3 min-h-5 text-[13px] font-bold text-muted-foreground transition-opacity"
            style={{ animationDelay: `180ms` }}
          >
            {steps[messageIndex % steps.length]}
          </p>
        </div>
      </div>
    </div>
  );
};

const ItineraryGenerationStickyLayer = ({
  mode,
  messageIndex,
}: {
  mode: 'generate' | 'regenerate';
  messageIndex: number;
}) => (
  <div className="sticky top-0 z-50 h-0 px-4 pt-4">
    <ItineraryGenerationLoader mode={mode} messageIndex={messageIndex} />
  </div>
);

const ItineraryRegenerationOverlay = ({ messageIndex }: { messageIndex: number }) => (
  <div className="sticky top-0 z-40 h-0">
    <div className="bg-white/68 dark:bg-black/52 min-h-[100dvh] px-4 pt-4 backdrop-blur-[2px]">
      <ItineraryGenerationLoader mode="regenerate" messageIndex={messageIndex} />
    </div>
  </div>
);
const DraftPreviewItem = ({ item }: { item: ItineraryItem }) => (
  <div className="flex gap-2 rounded-xl bg-stone-50 px-2.5 py-2 dark:bg-[hsl(var(--surface-muted))]/60">
    <div className="w-[48px] shrink-0 text-[11px] font-extrabold leading-5 text-stone-500 dark:text-stone-400">
      {formatTime(item.arrival_time)}
    </div>
    <div className="min-w-0 flex-1">
      <p className="line-clamp-1 text-[13px] font-bold text-stone-800 dark:text-stone-100">
        {item.name}
      </p>
      <div className="mt-1 flex flex-wrap gap-1">
        <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-stone-500 dark:bg-[hsl(var(--surface))] dark:text-stone-400">
          {categoryLabel(item.category)}
        </span>
        {formatDuration(item.duration_minutes) && (
          <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-blue-700 dark:bg-blue-950/30 dark:text-blue-300">
            {formatDuration(item.duration_minutes)}
          </span>
        )}

        {openingLabel(item.opening_status) && (
          <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
            {openingLabel(item.opening_status)}
          </span>
        )}
      </div>
    </div>
  </div>
);

const DraftDayPreview = ({ day, isExpanded }: { day: ItineraryDay; isExpanded: boolean }) => {
  const items = getVisibleItems(day);
  const restDay = isRestDay(day);
  const timeRange = getDayTimeRange(day);
  const visibleItems = isExpanded ? items : items.slice(0, 3);
  const hiddenCount = items.length - visibleItems.length;

  return (
    <div className="rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] px-3 py-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            День {day.day_number}
          </p>
          <p className="mt-0.5 text-[13px] font-bold text-stone-800 dark:text-stone-100">
            {restDay
              ? 'День отдыха'
              : `${formatTime(timeRange?.start ?? null)} - ${formatTime(timeRange?.end ?? null)}`}
          </p>
        </div>
        <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[11px] font-semibold text-stone-500 dark:bg-[hsl(var(--surface-muted))] dark:text-stone-400">
          {restDay ? 'Без активностей' : `${items.length} ${formatPlaces(items.length)}`}
        </span>
      </div>
      <div className="flex flex-col gap-1.5">
        {restDay && (
          <p className="rounded-xl bg-blue-50 px-3 py-2 text-[12px] font-semibold text-blue-700 dark:bg-blue-950/30 dark:text-blue-300">
            Для свободного планирования
          </p>
        )}
        {visibleItems.map((item) => (
          <DraftPreviewItem key={item.id} item={item} />
        ))}
        {hiddenCount > 0 && (
          <p className="px-2 py-1 text-[11px] font-semibold text-stone-400 dark:text-stone-500">
            Еще {hiddenCount} {formatPlaces(hiddenCount)} в этот день
          </p>
        )}
      </div>
    </div>
  );
};

const VariantCard = ({
  itinerary,
  onApprove,
  isLoading,
}: {
  itinerary: Itinerary;
  onApprove: (id: string) => void;
  isLoading: boolean;
}) => {
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const needsRegeneration = routeNeedsRegeneration(itinerary.quality_review);
  const approveAndClose = () => {
    onApprove(itinerary.id);
    setIsPreviewOpen(false);
  };

  return (
    <div className="trip-info-card flex flex-col gap-3">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-[11px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Вариант {itinerary.variant_index + 1}
          </p>
        </div>
        <h2 className="mt-1 text-[18px] font-extrabold text-stone-900 dark:text-white">
          {getPlacesCount(itinerary)} {formatPlaces(getPlacesCount(itinerary))},{' '}
          {itinerary.days.length} {formatDays(itinerary.days.length)}
        </h2>
      </div>
      {needsRegeneration && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[12px] font-semibold leading-snug text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-200">
          Этот вариант лучше пересобрать: проверка нашла критичные проблемы.
        </div>
      )}
      <div className="flex flex-wrap gap-1.5">
        {itinerary.days.map((day) => (
          <span
            key={day.id}
            className="rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-semibold text-stone-500 dark:bg-[hsl(var(--surface-muted))] dark:text-stone-400"
          >
            День {day.day_number}:{' '}
            {isRestDay(day)
              ? 'отдых'
              : `${getVisibleItems(day).length} ${formatPlaces(getVisibleItems(day).length)}`}
          </span>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Button
          variant="outline"
          className="h-11 rounded-2xl border-stone-200 bg-stone-100 text-[13px] font-bold text-stone-700 dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))] dark:text-stone-200"
          onClick={() => setIsPreviewOpen(true)}
        >
          <Eye className="h-4 w-4" />
          Посмотреть
        </Button>
        <Button
          className="h-11 rounded-2xl text-[14px] font-bold"
          onClick={() => onApprove(itinerary.id)}
          disabled={isLoading}
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          Утвердить
        </Button>
      </div>
      <ItineraryPreviewSheet
        itinerary={itinerary}
        open={isPreviewOpen}
        onOpenChange={setIsPreviewOpen}
        onApprove={approveAndClose}
        isApproving={isLoading}
      />
    </div>
  );
};

const ItineraryPreviewSheet = ({
  itinerary,
  open,
  onOpenChange,
  onApprove,
  isApproving,
}: {
  itinerary: Itinerary;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onApprove: () => void;
  isApproving: boolean;
}) => (
  <AdaptiveSheet
    open={open}
    onOpenChange={onOpenChange}
    title={`Вариант ${itinerary.variant_index + 1}`}
    description={`${getPlacesCount(itinerary)} ${formatPlaces(getPlacesCount(itinerary))}, ${getTravelMinutes(itinerary)} мин в пути`}
    className="max-h-[92dvh]"
    bodyClassName="pb-4"
    footer={
      <div className="flex flex-col gap-2">
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="outline"
            className="h-11 rounded-2xl border-stone-200 bg-stone-100 text-[13px] font-bold text-stone-700 dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))] dark:text-stone-200"
            onClick={() => onOpenChange(false)}
          >
            Закрыть
          </Button>
          <Button
            className="h-11 rounded-2xl text-[14px] font-bold"
            onClick={onApprove}
            disabled={isApproving}
          >
            {isApproving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Check className="h-4 w-4" />
            )}
            Утвердить
          </Button>
        </div>
      </div>
    }
  >
    <div className="flex flex-col gap-3">
      {itinerary.days.map((day) => (
        <DraftDayPreview key={day.id} day={day} isExpanded />
      ))}
    </div>
  </AdaptiveSheet>
);

const DayRouteMap = ({ points }: { points: DayMapPoint[] }) => {
  const { isReady } = useYandexMaps();
  const { resolvedTheme } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<YMapInstance | null>(null);
  const markersRef = useRef<YMapChild[]>([]);
  const routeRef = useRef<YMapChild | null>(null);
  const hasFittedRef = useRef(false);
  const [selectedId, setSelectedId] = useState(points[0]?.item.id ?? null);
  const activeSelectedId = points.some((point) => point.item.id === selectedId)
    ? selectedId
    : (points[0]?.item.id ?? null);

  useEffect(() => {
    if (!isReady || !window.ymaps3 || !containerRef.current || points.length === 0) return;
    const ymaps3 = window.ymaps3;
    const mapCenter = computeMapCenter(points);

    if (!mapRef.current) {
      const { YMap, YMapDefaultFeaturesLayer, YMapDefaultSchemeLayer } = ymaps3;
      const map = new YMap(containerRef.current, {
        location: { center: mapCenter, zoom: points.length > 1 ? 13 : 15 },
        theme: resolvedTheme,
      });
      map.addChild(new YMapDefaultSchemeLayer());
      map.addChild(new YMapDefaultFeaturesLayer());
      mapRef.current = map;
    }

    const map = mapRef.current;
    map.update({ theme: resolvedTheme });
    markersRef.current.forEach((marker) => map.removeChild(marker));
    markersRef.current = [];
    if (routeRef.current) {
      map.removeChild(routeRef.current);
      routeRef.current = null;
    }

    if (points.length > 1) {
      const route = new ymaps3.YMapFeature({
        geometry: { type: 'LineString', coordinates: points.map((point) => point.coords) },
        style: { stroke: [{ color: '#2563EB', width: 4, opacity: 0.62 }] },
      });
      map.addChild(route);
      routeRef.current = route;
    }

    points.forEach((point, index) => {
      const markerEl = createRouteMarkerEl(index, point.item.id === activeSelectedId);
      markerEl.addEventListener('click', () => {
        setSelectedId(point.item.id);
        map.update({ location: { center: point.coords, zoom: 15 } });
      });
      const marker = new ymaps3.YMapMarker({ coordinates: point.coords }, markerEl);
      map.addChild(marker);
      markersRef.current.push(marker);
    });

    if (!hasFittedRef.current) {
      hasFittedRef.current = true;
      map.update({
        location:
          points.length > 1
            ? { bounds: computeMapBounds(points) }
            : { center: points[0].coords, zoom: 15 },
      });
    }
  }, [activeSelectedId, isReady, points, resolvedTheme]);

  useEffect(
    () => () => {
      mapRef.current?.destroy();
      mapRef.current = null;
    },
    []
  );

  const selectedPoint =
    points.find((point) => point.item.id === activeSelectedId) ?? points[0] ?? null;

  return (
    <div className="flex flex-col gap-3">
      <div className="relative h-[360px] overflow-hidden rounded-[22px] border border-[hsl(var(--surface-border))] bg-stone-100 dark:bg-[hsl(var(--surface-muted))]">
        <div ref={containerRef} className="h-full w-full" />
        {selectedPoint && (
          <div className="bg-white/92 dark:bg-stone-950/88 absolute left-3 right-3 top-3 rounded-2xl px-3 py-2.5 shadow-[0_16px_38px_rgba(15,23,42,0.22)] backdrop-blur">
            <p className="line-clamp-1 text-[13px] font-extrabold text-stone-900 dark:text-white">
              {selectedPoint.item.name}
            </p>
            <p className="mt-0.5 text-[11px] font-semibold text-stone-500 dark:text-stone-400">
              {formatTime(selectedPoint.item.arrival_time)} -{' '}
              {formatTime(selectedPoint.item.departure_time)}
            </p>
          </div>
        )}
        {!isReady && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-stone-100 text-stone-400 dark:bg-[hsl(var(--surface-muted))] dark:text-stone-500">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="text-[12px] font-bold">Загружаю карту</span>
          </div>
        )}
      </div>
      <div className="flex flex-col gap-2">
        {points.map((point, index) => (
          <button
            key={point.item.id}
            type="button"
            onClick={() => setSelectedId(point.item.id)}
            className={`flex min-h-12 items-center gap-3 rounded-2xl border px-3 py-2 text-left transition-colors ${
              point.item.id === activeSelectedId
                ? 'border-blue-200 bg-blue-50 dark:border-blue-900/50 dark:bg-blue-950/30'
                : 'border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))]'
            }`}
          >
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#2563EB] text-[12px] font-extrabold text-white">
              {index + 1}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[13px] font-bold text-stone-900 dark:text-white">
                {point.item.name}
              </span>
              <span className="mt-0.5 block text-[11px] font-semibold text-stone-500 dark:text-stone-400">
                {formatTime(point.item.arrival_time)} - {formatTime(point.item.departure_time)}
              </span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};

const DayRouteMapButton = ({ day }: { day: ItineraryDay }) => {
  const [open, setOpen] = useState(false);
  const points = useMemo(() => getDayMapPoints(day), [day]);

  if (getVisibleItems(day).length === 0) return null;

  return (
    <>
      <Button
        variant="outline"
        className="h-11 rounded-2xl border-stone-200 bg-stone-100 text-[13px] font-bold text-stone-700 dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))] dark:text-stone-200"
        onClick={() => setOpen(true)}
        disabled={points.length === 0}
      >
        <Map className="h-4 w-4" />
        Карта дня
      </Button>
      <AdaptiveSheet
        open={open}
        onOpenChange={setOpen}
        title={`День ${day.day_number} на карте`}
        description={points.length === 0 ? 'Места этого дня не найдены на карте' : ''}
        className="max-h-[92dvh]"
        bodyClassName="pb-4"
      >
        {points.length > 0 ? (
          <DayRouteMap points={points} />
        ) : (
          <div className="rounded-2xl bg-stone-100 px-4 py-5 text-center text-[13px] font-semibold text-stone-500 dark:bg-[hsl(var(--surface-muted))] dark:text-stone-400">
            Для этих мест нет координат, поэтому карту построить нельзя
          </div>
        )}
      </AdaptiveSheet>
    </>
  );
};

type ItineraryPlaceCandidate = {
  name: string | null;
  fullAddress: string | null;
  coords: LngLat;
};

const createCandidateMarkerEl = (): HTMLDivElement => {
  const el = document.createElement('div');
  el.style.cssText = [
    'width:34px;height:34px;border-radius:999px;border:3px solid white;',
    'background:#16A34A;color:white;display:flex;align-items:center;justify-content:center;',
    'box-shadow:0 10px 28px rgba(22,163,74,0.34);',
  ].join('');
  el.innerHTML =
    '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M5 12h14"/></svg>';
  return el;
};

const ItineraryPlacePickerMap = ({
  points,
  destination,
  candidate,
  onSelectCandidate,
}: {
  points: DayMapPoint[];
  destination: string;
  candidate: ItineraryPlaceCandidate | null;
  onSelectCandidate: (candidate: ItineraryPlaceCandidate) => void;
}) => {
  const { isReady } = useYandexMaps();
  const { resolvedTheme } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<YMapInstance | null>(null);
  const markersRef = useRef<YMapChild[]>([]);
  const routeRef = useRef<YMapChild | null>(null);
  const candidateRef = useRef<YMapChild | null>(null);
  const hasFittedRef = useRef(false);
  const onSelectRef = useRef(onSelectCandidate);
  const pointsCenter = points.length > 0 ? computeMapCenter(points) : null;
  const { result: destinationGeocode, isLoading: isGeocoding } = useGeocode(
    !pointsCenter ? destination : ''
  );
  const fallbackCenter: LngLat | null = destinationGeocode
    ? [destinationGeocode.lon, destinationGeocode.lat]
    : !isGeocoding && !pointsCenter
      ? [37.618, 55.751]
      : null;
  const mapCenter = candidate?.coords ?? pointsCenter ?? fallbackCenter;

  useEffect(() => {
    onSelectRef.current = onSelectCandidate;
  }, [onSelectCandidate]);

  useEffect(() => {
    if (!isReady || !window.ymaps3 || !containerRef.current || !mapCenter) return;
    const ymaps3 = window.ymaps3;

    if (!mapRef.current) {
      const { YMap, YMapDefaultFeaturesLayer, YMapDefaultSchemeLayer, YMapListener } = ymaps3;
      const map = new YMap(containerRef.current, {
        location: { center: mapCenter, zoom: points.length > 0 ? 13 : 11 },
        theme: resolvedTheme,
      });
      map.addChild(new YMapDefaultSchemeLayer());
      map.addChild(new YMapDefaultFeaturesLayer());
      map.addChild(
        new YMapListener({
          layer: 'any',
          onClick: (_object: object | null, event: { coordinates: LngLat }) => {
            onSelectRef.current({
              name: null,
              fullAddress: null,
              coords: event.coordinates,
            });
          },
        })
      );
      mapRef.current = map;
    }

    const map = mapRef.current;
    map.update({ theme: resolvedTheme });
    markersRef.current.forEach((marker) => map.removeChild(marker));
    markersRef.current = [];
    if (routeRef.current) {
      map.removeChild(routeRef.current);
      routeRef.current = null;
    }
    if (candidateRef.current) {
      map.removeChild(candidateRef.current);
      candidateRef.current = null;
    }

    if (points.length > 1) {
      const route = new ymaps3.YMapFeature({
        geometry: { type: 'LineString', coordinates: points.map((point) => point.coords) },
        style: { stroke: [{ color: '#2563EB', width: 3, opacity: 0.42 }] },
      });
      map.addChild(route);
      routeRef.current = route;
    }

    points.forEach((point, index) => {
      const marker = new ymaps3.YMapMarker(
        { coordinates: point.coords },
        createRouteMarkerEl(index, false)
      );
      map.addChild(marker);
      markersRef.current.push(marker);
    });

    if (candidate) {
      const marker = new ymaps3.YMapMarker(
        { coordinates: candidate.coords },
        createCandidateMarkerEl()
      );
      map.addChild(marker);
      candidateRef.current = marker;
      map.update({ location: { center: candidate.coords, zoom: 15 } });
      return;
    }

    if (!hasFittedRef.current) {
      hasFittedRef.current = true;
      map.update({
        location:
          points.length > 1
            ? { bounds: computeMapBounds(points) }
            : { center: mapCenter, zoom: points.length === 1 ? 15 : 11 },
      });
    }
  }, [candidate, isReady, mapCenter, points, resolvedTheme]);

  useEffect(
    () => () => {
      mapRef.current?.destroy();
      mapRef.current = null;
    },
    []
  );

  return (
    <div className="relative h-[360px] overflow-hidden rounded-[22px] border border-[hsl(var(--surface-border))] bg-stone-100 dark:bg-[hsl(var(--surface-muted))]">
      <div ref={containerRef} className="h-full w-full" />
      {!isReady && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-stone-100 text-stone-400 dark:bg-[hsl(var(--surface-muted))] dark:text-stone-500">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span className="text-[12px] font-bold">Загружаю карту...</span>
        </div>
      )}
    </div>
  );
};

const AddPlaceToItinerarySheet = ({
  day,
  destination,
  open,
  onOpenChange,
  onAdd,
  isLoading,
}: {
  day: ItineraryDay;
  destination: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd: (dayId: string, name: string, coords: LngLat) => void;
  isLoading: boolean;
}) => {
  const points = useMemo(() => getDayMapPoints(day), [day]);
  const [candidate, setCandidate] = useState<ItineraryPlaceCandidate | null>(null);
  const biasCenter = candidate?.coords ?? (points.length > 0 ? computeMapCenter(points) : null);
  const reverseName = useReverseGeocode(candidate?.name ? null : (candidate?.coords ?? null));
  const { searchQuery, setSearchQuery, suggestions, isSearching, showSuggestions, clearSearch } =
    useMapSearch(biasCenter);
  const candidateName = candidate?.name ?? reverseName ?? '';

  const handleSubmit = () => {
    if (!candidate) return;
    onAdd(day.id, candidateName.trim() || 'Выбранная точка', candidate.coords);
    setCandidate(null);
    clearSearch();
    onOpenChange(false);
  };

  return (
    <AdaptiveSheet
      open={open}
      onOpenChange={(nextOpen) => {
        onOpenChange(nextOpen);
        if (!nextOpen) {
          setCandidate(null);
          clearSearch();
        }
      }}
      title={`Добавить место в день ${day.day_number}`}
      description=""
      className="max-h-[92dvh]"
      bodyClassName="pb-4"
      footer={
        <Button
          className="h-12 w-full rounded-2xl text-[14px] font-bold"
          onClick={handleSubmit}
          disabled={!candidate || isLoading}
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          Добавить в маршрут
        </Button>
      }
    >
      <div className="flex flex-col gap-3">
        <div className="relative">
          <div className="flex items-center gap-2 rounded-2xl bg-stone-100 px-3 dark:bg-[hsl(var(--surface-muted))]">
            {isSearching ? (
              <Loader2 className="h-4 w-4 shrink-0 animate-spin text-stone-400" />
            ) : (
              <Search className="h-4 w-4 shrink-0 text-stone-400" />
            )}
            <input
              className="h-12 flex-1 bg-transparent text-[14px] font-semibold text-stone-900 outline-none placeholder:text-stone-400 dark:text-white"
              placeholder="Поиск места на карте"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={clearSearch}
                className="flex h-8 w-8 items-center justify-center"
              >
                <X className="h-4 w-4 text-stone-400" />
              </button>
            )}
          </div>
          {showSuggestions && (
            <div className="absolute left-0 right-0 top-[54px] z-20 overflow-hidden rounded-2xl border border-[hsl(var(--surface-border))] bg-white shadow-xl dark:bg-[hsl(var(--surface-elevated))]">
              {suggestions.map((suggestion) => (
                <button
                  key={`${suggestion.name}-${suggestion.lat}-${suggestion.lon}`}
                  type="button"
                  onClick={() => {
                    setCandidate({
                      name: suggestion.name,
                      fullAddress: suggestion.fullAddress,
                      coords: [suggestion.lon, suggestion.lat],
                    });
                    clearSearch();
                  }}
                  className="w-full px-4 py-3 text-left text-[13px] text-stone-800 first:pt-3.5 last:pb-3.5 hover:bg-stone-50 dark:text-stone-200 dark:hover:bg-stone-800"
                >
                  <span className="block font-bold">{suggestion.name}</span>
                  <span className="mt-0.5 block truncate text-[11px] font-semibold text-stone-400">
                    {suggestion.fullAddress}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
        <ItineraryPlacePickerMap
          points={points}
          destination={destination}
          candidate={candidate}
          onSelectCandidate={setCandidate}
        />
        <div className="rounded-2xl bg-stone-100 px-4 py-3 dark:bg-[hsl(var(--surface-muted))]">
          {candidate ? (
            <div className="flex items-start gap-3">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-[14px] font-extrabold text-stone-900 dark:text-white">
                  {candidateName || 'Определяю место'}
                </p>
                <p className="mt-1 text-[11px] font-semibold leading-snug text-stone-500 dark:text-stone-400">
                  {candidate.fullAddress ??
                    `${candidate.coords[1].toFixed(5)}, ${candidate.coords[0].toFixed(5)}`}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-[13px] font-semibold text-stone-500 dark:text-stone-400">
              Выберите место через поиск или клик по карте
            </p>
          )}
        </div>
      </div>
    </AdaptiveSheet>
  );
};

const ItemRow = ({
  item,
  index,
  isActiveTrip,
  onPin,
  onRemove,
  onVisit,
  onUnvisit,
  onTimeChange,
  isBusy,
}: {
  item: ItineraryItem;
  index: number;
  isActiveTrip: boolean;
  onPin: (item: ItineraryItem) => void;
  onRemove: (item: ItineraryItem) => void;
  onVisit: (item: ItineraryItem) => void;
  onUnvisit: (item: ItineraryItem) => void;
  onTimeChange: (
    item: ItineraryItem,
    field: 'arrival_time' | 'departure_time',
    value: string
  ) => void;
  isBusy: boolean;
}) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: item.id,
    data: { type: 'itinerary-item', dayId: item.day_id },
    disabled: isBusy,
  });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
  };
  const isExternalCandidate =
    item.source === 'external_candidate' || Boolean(item.external_candidate_source);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn('flex w-full min-w-0 items-start', isDragging && 'opacity-40')}
    >
      <button
        type="button"
        {...listeners}
        {...attributes}
        className="flex h-12 w-8 shrink-0 touch-none items-center justify-start text-stone-300 disabled:opacity-100 dark:text-stone-600"
        disabled={isBusy}
        aria-label="Перетащить место"
      >
        <GripVertical className="h-4 w-4" />
      </button>

      <div
        className={cn(
          'min-w-0 flex-1 rounded-2xl px-3 py-3 text-left',
          'border border-white/20 bg-white/60 shadow-sm backdrop-blur-sm',
          'dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-elevated))]/60',
          'transition-transform active:scale-[0.98]'
        )}
      >
        <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#2563EB] text-[13px] font-bold text-white shadow-sm">
            {index + 1}
          </div>
          <div className="min-w-0 flex-1">
            <p className="line-clamp-2 text-[14px] font-bold leading-snug text-stone-900 dark:text-white">
              {item.name}
            </p>
            <div className="mt-1.5 flex min-w-0 items-center gap-1 overflow-hidden">
              <span className="shrink-0 rounded-full bg-stone-100 px-2 py-0.5 text-[11px] font-semibold text-stone-500 dark:bg-[hsl(var(--surface-muted))] dark:text-stone-400">
                {categoryLabel(item.category)}
              </span>
              {item.visited_place_id && (
                <span className="shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-bold text-green-700 dark:bg-green-950/40 dark:text-green-300">
                  Посещено
                </span>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            <Button
              variant="outline"
              className="h-8 rounded-xl px-2 text-[12px] disabled:opacity-100"
              onClick={() => onPin(item)}
              disabled={isBusy}
            >
              <Pin
                className={cn(
                  'h-3.5 w-3.5',
                  item.is_pinned && 'shrink-0 fill-amber-500 text-amber-500'
                )}
              />
            </Button>
            <Button
              variant="outline"
              className="h-8 rounded-xl px-2 text-[12px] text-red-600 disabled:opacity-100"
              onClick={() => onRemove(item)}
              disabled={isBusy}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-[1fr_30px_1fr] items-center">
          <div className="inline-flex h-9 shrink-0 items-center rounded-xl border border-stone-200 bg-stone-50 px-2 shadow-inner dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))]/70">
            <Input
              type="time"
              aria-label="Время прибытия"
              value={inputTimeValue(item.arrival_time)}
              onChange={(event) => onTimeChange(item, 'arrival_time', event.target.value)}
              disabled={isBusy}
              className="h-7 w-[55px] border-0 bg-transparent px-0 text-center text-[13px] font-extrabold text-stone-900 shadow-none [font-variant-numeric:tabular-nums] focus-visible:ring-0 disabled:cursor-default disabled:text-stone-900 disabled:opacity-100 disabled:[-webkit-text-fill-color:#1c1917] dark:text-white dark:disabled:text-white dark:disabled:[-webkit-text-fill-color:#ffffff] [&::-webkit-calendar-picker-indicator]:hidden [&::-webkit-calendar-picker-indicator]:appearance-none"
            />
          </div>
          <span
            className="px-1.5 text-center text-[12px] font-bold text-stone-300 dark:text-stone-600"
            aria-hidden="true"
          >
            →
          </span>
          <div className="inline-flex h-9 shrink-0 items-center rounded-xl border border-stone-200 bg-stone-50 px-2 shadow-inner dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))]/70">
            <Input
              type="time"
              aria-label="Время ухода"
              value={inputTimeValue(item.departure_time)}
              onChange={(event) => onTimeChange(item, 'departure_time', event.target.value)}
              disabled={isBusy}
              className="h-7 w-[55px] border-0 bg-transparent px-0 text-center text-[13px] font-extrabold text-stone-900 shadow-none [font-variant-numeric:tabular-nums] focus-visible:ring-0 disabled:cursor-default disabled:text-stone-900 disabled:opacity-100 disabled:[-webkit-text-fill-color:#1c1917] dark:text-white dark:disabled:text-white dark:disabled:[-webkit-text-fill-color:#ffffff] [&::-webkit-calendar-picker-indicator]:hidden [&::-webkit-calendar-picker-indicator]:appearance-none"
            />
          </div>
        </div>

        {isActiveTrip && !isExternalCandidate && (
          <Button
            className="mt-2 h-10 w-full rounded-xl text-[13px] font-bold disabled:opacity-100"
            variant={item.visited_place_id ? 'outline' : 'default'}
            onClick={() => (item.visited_place_id ? onUnvisit(item) : onVisit(item))}
            disabled={isBusy}
          >
            <Check className="h-4 w-4" />
            {item.visited_place_id ? 'Снять отметку' : 'Отметить посещенным'}
          </Button>
        )}
      </div>
    </div>
  );
};

const DayDropArea = ({ day, children }: { day: ItineraryDay; children: React.ReactNode }) => {
  const { isOver, setNodeRef } = useDroppable({
    id: day.id,
    data: { type: 'itinerary-day', dayId: day.id },
  });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'flex flex-col gap-2 rounded-2xl transition-colors',
        isOver && 'bg-blue-50/40 dark:bg-blue-950/10'
      )}
    >
      {children}
    </div>
  );
};

const AddPlaceInline = ({
  day,
  destination,
  onAdd,
  isLoading,
}: {
  day: ItineraryDay;
  destination: string;
  onAdd: (day: ItineraryDay, name: string, coords: LngLat) => void;
  isLoading: boolean;
}) => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        variant="outline"
        className="h-11 rounded-2xl border-stone-200 bg-stone-100 text-[13px] font-bold text-stone-700 dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))] dark:text-stone-200"
        onClick={() => setOpen(true)}
        disabled={isLoading}
      >
        <Plus className="h-4 w-4" />
        Добавить место
      </Button>
      <AddPlaceToItinerarySheet
        day={day}
        destination={destination}
        open={open}
        onOpenChange={setOpen}
        onAdd={(_dayId, name, coords) => onAdd(day, name, coords)}
        isLoading={isLoading}
      />
    </>
  );
};

const ApprovedItinerary = ({
  itinerary,
  onRegenerate,
  isRegenerating,
  dropTargetDayId,
  children,
}: {
  itinerary: Itinerary;
  onRegenerate: () => void;
  isRegenerating: boolean;
  dropTargetDayId: string | null;
  children: (day: ItineraryDay) => React.ReactNode;
}) => {
  const estimatedPaidTotal = scoreMaybeNumber(itinerary.score_summary, 'estimated_paid_poi_total');
  const evidenceBackedCount = scoreNumber(
    itinerary.score_summary,
    'evidence_backed_paid_poi_count'
  );
  const candidatePriceCount = scoreNumber(itinerary.score_summary, 'candidate_poi_price_count');
  const priceEstimationUsed = scoreBoolean(itinerary.score_summary, 'price_estimation_used');
  const needsRegeneration = routeNeedsRegeneration(itinerary.quality_review);

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-3 gap-2.5">
        <div className="trip-info-card px-3 py-3">
          <Map className="mb-2 h-4 w-4 text-[#2563EB]" />
          <p className="text-[20px] font-extrabold leading-none text-stone-900 dark:text-white">
            {itinerary.days.length}
          </p>
          <p className="mt-1 text-[11px] font-semibold text-stone-400 dark:text-stone-500">
            {formatDays(itinerary.days.length)}
          </p>
        </div>
        <div className="trip-info-card px-3 py-3">
          <MapPinned className="mb-2 h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          <p className="text-[20px] font-extrabold leading-none text-stone-900 dark:text-white">
            {getPlacesCount(itinerary)}
          </p>
          <p className="mt-1 text-[11px] font-semibold text-stone-400 dark:text-stone-500">
            {formatPlaces(getPlacesCount(itinerary))}
          </p>
        </div>
        <div className="trip-info-card px-3 py-3">
          <Route className="mb-2 h-4 w-4 text-amber-600 dark:text-amber-400" />
          <p className="text-[20px] font-extrabold leading-none text-stone-900 dark:text-white">
            {getTravelMinutes(itinerary)}
          </p>
          <p className="mt-1 text-[11px] font-semibold text-stone-400 dark:text-stone-500">
            мин пути
          </p>
        </div>
      </div>
      {priceEstimationUsed && estimatedPaidTotal !== null && estimatedPaidTotal > 0 && (
        <div className="trip-info-card flex items-start gap-3 px-3.5 py-3">
          <Info className="mt-0.5 h-4 w-4 flex-none text-emerald-600 dark:text-emerald-400" />
          <div className="min-w-0">
            <p className="text-[13px] font-extrabold text-stone-900 dark:text-white">
              Платные входы примерно {formatUsd(estimatedPaidTotal)}
            </p>
            <p className="mt-1 text-[11px] font-semibold leading-snug text-stone-500 dark:text-stone-400">
              {evidenceBackedCount > 0
                ? `Есть подтверждение источниками: ${evidenceBackedCount}`
                : 'Использованы цены из каталога'}
              {candidatePriceCount > 0 ? `, включая кандидатов ИИ: ${candidatePriceCount}` : ''}
            </p>
          </div>
        </div>
      )}
      <Button
        variant="outline"
        className={cn(
          'h-[48px] rounded-2xl border-stone-200 bg-stone-100 text-[14px] font-bold text-stone-700 dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))] dark:text-stone-200',
          needsRegeneration &&
            'border-red-300 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200'
        )}
        onClick={onRegenerate}
        disabled={isRegenerating}
      >
        {isRegenerating ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        {needsRegeneration ? 'Пересобрать маршрут' : 'Собрать другой вариант'}
      </Button>
      {itinerary.days.map((day) => {
        const restDay = isRestDay(day);
        const timeRange = getDayTimeRange(day);
        const placesCount = getVisibleItems(day).length;

        return (
          <section
            key={day.id}
            className={cn(
              'trip-info-card flex flex-col gap-3 transition-colors duration-150',
              dropTargetDayId === day.id &&
                'bg-blue-50/70 ring-2 ring-blue-500/15 dark:bg-blue-950/20'
            )}
          >
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                  День {day.day_number}
                </p>
                <h2 className="mt-1 text-[18px] font-extrabold text-stone-900 dark:text-white">
                  {restDay
                    ? 'День отдыха'
                    : `${formatTime(timeRange?.start ?? null)} - ${formatTime(timeRange?.end ?? null)}`}
                </h2>
              </div>
              <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-semibold text-stone-500 dark:bg-[hsl(var(--surface-muted))] dark:text-stone-400">
                {restDay ? 'Без активностей' : `${placesCount} ${formatPlaces(placesCount)}`}
              </span>
            </div>
            {children(day)}
          </section>
        );
      })}
    </div>
  );
};

export const TripItineraryTab = () => {
  const { trip } = useOutletContext<TripDetailOutletContext>();
  const stateQuery = useItineraryState(trip.id);
  const generateMutation = useGenerateItinerary(trip.id);
  const regenerateMutation = useRegenerateItinerary(trip.id);
  const approveMutation = useApproveItinerary(trip.id);
  const updateMutation = useUpdateItineraryItem(trip.id);
  const moveMutation = useMoveItineraryItem(trip.id);
  const removeMutation = useRemoveItineraryItem(trip.id);
  const addMutation = useAddItineraryItem(trip.id);
  const visitMutation = useVisitItineraryItem(trip.id);
  const unvisitMutation = useUnvisitItineraryItem(trip.id);
  const approved = stateQuery.data?.approved ?? null;
  const drafts = stateQuery.data?.drafts ?? [];
  const generationJob = stateQuery.data?.generation_job ?? null;
  const current = approved ?? drafts[0] ?? null;
  const [dropTargetDayId, setDropTargetDayId] = useState<string | null>(null);
  const trackedViewedKeys = useRef<Set<string>>(new Set());
  const durationDays = useMemo(() => {
    const start = new Date(`${trip.start_date}T00:00:00`);
    const end = new Date(`${trip.end_date}T00:00:00`);
    if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime())) return 1;
    return Math.max(1, Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1);
  }, [trip.end_date, trip.start_date]);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 160, tolerance: 8 } })
  );
  const isGenerationActive =
    generationJob?.status === 'queued' || generationJob?.status === 'running';
  const generationMode = isGenerationActive
    ? generationJob.mode === 'regenerate'
      ? 'regenerate'
      : 'generate'
    : generateMutation.isPending
      ? 'generate'
      : regenerateMutation.isPending
        ? 'regenerate'
        : null;
  const generationError = generationMode
    ? null
    : generationJob?.status === 'failed'
      ? itineraryErrorMessage({
          response: {
            data: { error: generationJob.error_code, message: generationJob.error_message },
          },
        })
      : generateMutation.isError || regenerateMutation.isError
        ? itineraryErrorMessage(generateMutation.error ?? regenerateMutation.error)
        : null;
  const isBusy =
    isGenerationActive ||
    generateMutation.isPending ||
    regenerateMutation.isPending ||
    approveMutation.isPending ||
    updateMutation.isPending ||
    moveMutation.isPending ||
    removeMutation.isPending ||
    addMutation.isPending ||
    visitMutation.isPending ||
    unvisitMutation.isPending;
  const isRegenerationLocked = generationMode === 'regenerate' && Boolean(current);

  const itinerarySummary = useMemo(
    () => ({
      generated_days_count: current?.days.length ?? 0,
      remaining_poi_count: current ? getPlacesCount(current) : 0,
    }),
    [current]
  );

  useEffect(() => {
    const key = `${trip.id}:${current?.id ?? 'empty'}:${current ? getPlacesCount(current) : 0}`;
    if (trackedViewedKeys.current.has(key)) return;
    trackedViewedKeys.current.add(key);
    sendEvent(
      'itinerary_viewed',
      {
        trip_id: trip.id,
        destination_id: trip.destination_id,
        duration_days: durationDays,
        has_generated_itinerary: Boolean(current),
      },
      'trip',
      trip.id
    );
  }, [current, durationDays, trip.destination_id, trip.id]);

  const handleGenerate = () => {
    void ensurePushNotifications().catch(() => false);
    const variantCount = trip.destination_id ? 3 : 1;
    generateMutation.mutate(
      { variant_count: variantCount, pace: 'standard', allow_external_route: true },
      {
        onSuccess: (job) => {
          sendEvent(
            'itinerary_generated',
            {
              trip_id: trip.id,
              job_id: job.id,
              destination_id: trip.destination_id,
              duration_days: durationDays,
              mode: job.mode,
            },
            'trip',
            trip.id
          );
        },
      }
    );
  };

  const handleRegenerate = () => {
    void ensurePushNotifications().catch(() => false);
    const variantCount = approved || !trip.destination_id ? 1 : 3;
    regenerateMutation.mutate(
      {
        variant_count: variantCount,
        pace: 'standard',
        exclude_signature: current?.route_signature,
        allow_external_route: true,
      },
      {
        onSuccess: (job) => {
          sendEvent(
            'itinerary_regenerated',
            {
              trip_id: trip.id,
              job_id: job.id,
              destination_id: trip.destination_id,
              duration_days: durationDays,
            },
            'trip',
            trip.id
          );
        },
      }
    );
  };

  const handleApprove = (itineraryId: string) => {
    approveMutation.mutate(itineraryId, {
      onSuccess: (itinerary) => {
        sendEvent(
          'itinerary_approved',
          {
            trip_id: trip.id,
            destination_id: trip.destination_id,
            itinerary_id: itinerary.id,
            days_count: itinerary.days.length,
            places_count: getPlacesCount(itinerary),
          },
          'trip',
          trip.id
        );
      },
    });
  };

  const handlePin = (item: ItineraryItem) => {
    updateMutation.mutate(
      { itemId: item.id, params: { is_pinned: !item.is_pinned } },
      {
        onSuccess: () => {
          sendEvent(
            'itinerary_poi_pinned',
            { trip_id: trip.id, item_id: item.id },
            'trip',
            trip.id
          );
        },
      }
    );
  };

  const [loadingMessageIndex, setLoadingMessageIndex] = useState(0);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setLoadingMessageIndex((current) => current + 1);
    }, 2200);
    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    if (!('serviceWorker' in navigator)) return;
    const handlePushMessage = (event: MessageEvent<{ type?: string; payload?: { url?: string; tag?: string } }>) => {
      if (event.data?.type !== 'triply-push') return;
      const payload = event.data.payload;
      const isCurrentTripItinerary =
        payload?.url?.includes(`/trips/${trip.id}/itinerary`) ||
        payload?.tag === `itinerary-${trip.id}`;
      if (isCurrentTripItinerary) {
        void stateQuery.refetch();
      }
    };
    navigator.serviceWorker.addEventListener('message', handlePushMessage);
    return () => navigator.serviceWorker.removeEventListener('message', handlePushMessage);
  }, [stateQuery, trip.id]);

  const handleDragOver = (event: DragOverEvent) => {
    const activeId = String(event.active.id);
    const overId = event.over ? String(event.over.id) : null;
    if (!approved || !overId) {
      setDropTargetDayId(null);
      return;
    }

    const sourceDay = findItemDay(approved, activeId);
    const target = getMoveTarget(approved, overId);
    setDropTargetDayId(sourceDay && target && sourceDay.id !== target.dayId ? target.dayId : null);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setDropTargetDayId(null);
    const activeId = String(event.active.id);
    const overId = event.over ? String(event.over.id) : null;
    if (!approved || !overId || activeId === overId) {
      return;
    }

    const sourceDay = findItemDay(approved, activeId);
    const target = getMoveTarget(approved, overId);
    if (!sourceDay || !target) {
      return;
    }

    const sourceIndex = getVisibleItems(sourceDay).findIndex((item) => item.id === activeId);
    if (sourceDay.id === target.dayId && sourceIndex === target.order) {
      return;
    }

    moveMutation.mutate(
      { itemId: activeId, params: { target_day_id: target.dayId, target_order: target.order } },
      {
        onSuccess: () => {
          sendEvent(
            'itinerary_poi_reordered',
            {
              trip_id: trip.id,
              source_item_id: activeId,
              target_day_id: target.dayId,
              target_order: target.order,
            },
            'trip',
            trip.id
          );
          if (sourceDay.id !== target.dayId) {
            sendEvent(
              'itinerary_poi_moved',
              {
                trip_id: trip.id,
                item_id: activeId,
                from_day: sourceDay.id,
                to_day: target.dayId,
                to_order: target.order,
              },
              'trip',
              trip.id
            );
          }
        },
      }
    );
  };

  const handleTimeChange = (
    item: ItineraryItem,
    field: 'arrival_time' | 'departure_time',
    value: string
  ) => {
    if (!value) return;
    updateMutation.mutate({
      itemId: item.id,
      params: { [field]: value },
    });
  };

  const handleRemove = (item: ItineraryItem) => {
    removeMutation.mutate(item.id, {
      onSuccess: () => {
        sendEvent('itinerary_poi_removed', { trip_id: trip.id, item_id: item.id }, 'trip', trip.id);
      },
    });
  };

  const handleVisit = (item: ItineraryItem) => {
    visitMutation.mutate(item.id, {
      onSuccess: (updatedItem) => {
        sendEvent('itinerary_poi_visited', { trip_id: trip.id, item_id: item.id }, 'trip', trip.id);
        if (updatedItem.visited_place_id) {
          sendEvent(
            'place_visit_marked_visited',
            {
              trip_id: trip.id,
              place_id: updatedItem.visited_place_id,
              source: 'itinerary',
            },
            'trip',
            trip.id
          );
        }
      },
    });
  };

  const handleUnvisit = (item: ItineraryItem) => {
    unvisitMutation.mutate(item.id);
  };

  const handleAdd = (day: ItineraryDay, name: string, coords: LngLat) => {
    const { arrival_time, departure_time } = getNextItemTime(day);
    addMutation.mutate(
      {
        day_id: day.id,
        name,
        latitude: String(coords[1]),
        longitude: String(coords[0]),
        arrival_time,
        departure_time,
        duration_minutes: 90,
      },
      {
        onSuccess: () => {
          sendEvent('itinerary_poi_added', { trip_id: trip.id, name }, 'trip', trip.id);
        },
      }
    );
  };

  return (
    <div
      className={cn(
        'no-scrollbar relative flex-1 pb-24 pt-4',
        isRegenerationLocked ? 'overflow-hidden' : 'overflow-y-auto'
      )}
    >
      {isRegenerationLocked && <ItineraryRegenerationOverlay messageIndex={loadingMessageIndex} />}

      {generationMode && !isRegenerationLocked && (
        <ItineraryGenerationStickyLayer mode={generationMode} messageIndex={loadingMessageIndex} />
      )}
      <div className="relative flex flex-col gap-3">
        <div
          className={cn(
            'flex flex-col gap-3',
            isRegenerationLocked && 'pointer-events-none select-none opacity-35'
          )}
        >
          {stateQuery.isPending && (
            <div className="trip-info-card flex items-center gap-3 px-4 py-4">
              <Loader2 className="h-4 w-4 animate-spin text-[#2563EB]" />
              <p className="text-[14px] font-semibold text-stone-500 dark:text-stone-400">
                Загружаю маршрут...
              </p>
            </div>
          )}
          {generationError && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-900/50 dark:bg-amber-950/30">
              <p className="text-[14px] font-bold text-amber-800 dark:text-amber-200">
                Поменяйте параметры или направление поездки
              </p>
              <p className="mt-1 text-[12px] font-semibold leading-relaxed text-amber-700 dark:text-amber-300">
                {generationError}
              </p>
            </div>
          )}
          {!generationMode && !stateQuery.isPending && !approved && drafts.length === 0 && (
            <EmptyState
              onGenerate={handleGenerate}
              isLoading={generateMutation.isPending || isGenerationActive}
            />
          )}
          {!approved && drafts.length > 0 && (
            <div className="flex flex-col gap-3 px-4 py-3">
              <div className="trip-info-card-muted flex gap-3 text-[11px] font-semibold text-stone-400 dark:text-stone-500">
                <Info className="h-3.5 w-3.5" />
                Выбранный маршрут можно отредактировать после утверждения
              </div>
              {drafts.map((itinerary) => (
                <VariantCard
                  key={itinerary.id}
                  itinerary={itinerary}
                  onApprove={handleApprove}
                  isLoading={approveMutation.isPending}
                />
              ))}
              <Button
                variant="outline"
                className="h-[48px] rounded-2xl text-[14px] font-bold"
                onClick={handleRegenerate}
                disabled={isBusy}
              >
                {regenerateMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                Собрать другие варианты
              </Button>
            </div>
          )}
          {approved && (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragOver={handleDragOver}
              onDragEnd={handleDragEnd}
              onDragCancel={() => setDropTargetDayId(null)}
            >
              <ApprovedItinerary
                itinerary={approved}
                onRegenerate={handleRegenerate}
                isRegenerating={regenerateMutation.isPending}
                dropTargetDayId={dropTargetDayId}
              >
                {(day) => (
                  <div className="flex flex-col gap-2">
                    <DayRouteMapButton day={day} />
                    <DayDropArea day={day}>
                      <SortableContext
                        items={getVisibleItems(day).map((item) => item.id)}
                        strategy={verticalListSortingStrategy}
                      >
                        {getVisibleItems(day).length > 0 &&
                          getVisibleItems(day).map((item, index) => (
                            <ItemRow
                              key={item.id}
                              item={item}
                              index={index}
                              isActiveTrip={trip.status === 'active'}
                              onPin={handlePin}
                              onRemove={handleRemove}
                              onVisit={handleVisit}
                              onUnvisit={handleUnvisit}
                              onTimeChange={handleTimeChange}
                              isBusy={isBusy}
                            />
                          ))}
                      </SortableContext>
                    </DayDropArea>
                    <AddPlaceInline
                      day={day}
                      destination={trip.destination}
                      onAdd={handleAdd}
                      isLoading={addMutation.isPending}
                    />
                  </div>
                )}
              </ApprovedItinerary>
            </DndContext>
          )}
          {current && (
            <div className="sr-only">
              {itinerarySummary.generated_days_count} {itinerarySummary.remaining_poi_count}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
