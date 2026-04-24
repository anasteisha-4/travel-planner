import { CATEGORY_META } from '@/entities/expense';
import { PostTripFeedbackSheet, useFeedback } from '@/features/feedback';
import { useTripAnalytics } from '@/features/trips';
import confetti from 'canvas-confetti';
import { AlertTriangle, Loader2, MessageSquarePlus } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useLocation, useOutletContext } from 'react-router-dom';
import type { TripDetailOutletContext } from './TripDetailPage';

const isJustCompleted = (s: unknown): boolean =>
  typeof s === 'object' && s !== null && 'justCompleted' in s;

const CONFETTI_COLORS = [
  '#EF4444',
  '#3B82F6',
  '#10B981',
  '#F59E0B',
  '#8B5CF6',
  '#EC4899',
  '#06B6D4',
  '#F97316',
];

const pluralDays = (n: number): string => {
  if (n % 10 === 1 && n % 100 !== 11) return 'день';
  if (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20)) return 'дня';
  return 'дней';
};

const fmt = (v: number): string =>
  v.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 });

export const TripAnalyticsTab = () => {
  const { trip } = useOutletContext<TripDetailOutletContext>();
  const location = useLocation();
  const fired = useRef(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const { alreadySubmitted } = useFeedback(trip.id, trip.destination);

  useEffect(() => {
    if (!isJustCompleted(location.state) || fired.current) return;
    fired.current = true;

    const originY = 0.3;
    const fire = (angle: number, originX: number, drift: number) =>
      confetti({
        particleCount: 45,
        angle,
        spread: 48,
        startVelocity: 20,
        decay: 0.88,
        gravity: 0.8,
        drift,
        ticks: 100,
        scalar: 0.85,
        shapes: ['square', 'circle'],
        origin: { x: originX, y: originY },
        colors: CONFETTI_COLORS,
        disableForReducedMotion: true,
      });

    fire(125, 0.2, -0.2);
    fire(55, 0.8, 0.2);

    setTimeout(() => setShowFeedback(true), 1200);
  }, [location.state]);

  const {
    loading,
    totalSpent,
    avgPerDay,
    durationDays,
    placesVisited,
    currency,
    budget,
    budgetPct,
    budgetDiff,
    budgetTier,
    categoryBreakdown,
    hasConversionErrors,
  } = useTripAnalytics(trip);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-stone-400" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-5 pb-24 pt-4">
      <div className="flex flex-col gap-3">
        {/* Hero card */}
        <div
          className="relative overflow-hidden rounded-[28px] border border-blue-100 px-6 py-8 text-center dark:border-blue-900/30"
          style={{ background: 'linear-gradient(150deg,#EFF6FF 0%,#DBEAFE 50%,#EDE9FE 100%)' }}
        >
          <div className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-blue-300/20" />
          <div className="pointer-events-none absolute -bottom-8 -left-6 h-28 w-28 rounded-full bg-indigo-300/15" />

          <div className="relative mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border-2 border-blue-400 bg-white/60 dark:border-blue-500 dark:bg-blue-950/40">
            <svg
              className="h-7 w-7 text-blue-500 dark:text-blue-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.2}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>

          <p className="relative text-[22px] font-extrabold tracking-tight text-[#1E3A5F] dark:text-white">
            Поездка завершена
          </p>
          <p className="relative mt-2 text-[14px] font-medium text-blue-400/90 dark:text-blue-400">
            {trip.destination}
          </p>

          <button
            type="button"
            onClick={() => setShowFeedback(true)}
            className="relative mx-auto mt-4 flex items-center gap-2 rounded-[10px] border border-blue-200/70 bg-white/60 px-4 py-2 text-[13px] font-semibold text-blue-600 transition-all active:scale-95 dark:border-blue-700/50 dark:bg-blue-950/30 dark:text-blue-400"
          >
            <MessageSquarePlus className="h-4 w-4" />
            {alreadySubmitted ? 'Редактировать отзыв' : 'Оставить отзыв'}
          </button>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="trip-info-card">
            <p className="mb-2.5 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Длительность
            </p>
            <p className="text-[38px] font-extrabold leading-none tracking-tight text-stone-900 dark:text-white">
              {durationDays}
            </p>
            <p className="mt-1.5 text-[13px] font-medium text-stone-400 dark:text-stone-500">
              {pluralDays(durationDays)}
            </p>
          </div>

          <div className="trip-info-card">
            <p className="mb-2.5 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Мест
            </p>
            <p className="text-[38px] font-extrabold leading-none tracking-tight text-stone-900 dark:text-white">
              {placesVisited}
            </p>
            <p className="mt-1.5 text-[13px] font-medium text-stone-400 dark:text-stone-500">
              посещено
            </p>
          </div>
        </div>

        {/* Spent + avg per day */}
        <div className="trip-info-card">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
            Потрачено
          </p>
          <div className="flex items-baseline gap-2">
            <p className="text-[42px] font-extrabold leading-none tracking-tight text-stone-900 dark:text-white">
              {fmt(totalSpent)}
            </p>
            <p className="pb-1 text-[16px] font-semibold text-stone-400 dark:text-stone-500">
              {currency}
            </p>
          </div>
          <div className="mt-3.5 flex items-center gap-3 border-t border-stone-100 pt-3.5 dark:border-stone-800">
            <div className="flex flex-col gap-0.5">
              <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                В среднем / день
              </p>
              <p className="text-[20px] font-extrabold leading-none tracking-tight text-stone-700 dark:text-stone-300">
                {fmt(avgPerDay)} {currency}
              </p>
            </div>
          </div>
        </div>

        {/* Budget compliance */}
        {budget !== null && budgetPct !== null && budgetDiff !== null && (
          <div
            className={`trip-info-card ${
              budgetTier === 'red'
                ? 'border-red-200 dark:border-red-900/50'
                : budgetTier === 'orange'
                  ? 'border-orange-200 dark:border-orange-800/50'
                  : budgetTier === 'amber'
                    ? 'border-amber-200 dark:border-amber-800/50'
                    : ''
            }`}
          >
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                Бюджет
              </p>
              {budgetTier === 'red' ? (
                <span className="rounded-full border border-red-200 bg-red-50 px-2.5 py-0.5 text-[11px] font-semibold text-red-600 dark:border-red-900/60 dark:bg-red-900/20 dark:text-red-400">
                  Превышен
                </span>
              ) : budgetTier === 'orange' ? (
                <span className="rounded-full border border-orange-200 bg-orange-50 px-2.5 py-0.5 text-[11px] font-semibold text-orange-600 dark:border-orange-800/60 dark:bg-orange-900/20 dark:text-orange-400">
                  Почти всё
                </span>
              ) : budgetTier === 'amber' ? (
                <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-600 dark:border-amber-800/60 dark:bg-amber-900/20 dark:text-amber-400">
                  Больше половины
                </span>
              ) : (
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-600 dark:border-emerald-900/60 dark:bg-emerald-900/20 dark:text-emerald-400">
                  В рамках
                </span>
              )}
            </div>

            <div className="h-2.5 overflow-hidden rounded-full bg-stone-100 dark:bg-stone-700">
              <div
                className={`h-full rounded-full transition-all ${
                  budgetTier === 'red'
                    ? 'bg-red-500'
                    : budgetTier === 'orange'
                      ? 'bg-orange-500'
                      : budgetTier === 'amber'
                        ? 'bg-amber-400'
                        : 'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(Math.round(budgetPct * 100), 100)}%` }}
              />
            </div>

            <p
              className={`mt-2 text-[13px] font-semibold ${
                budgetTier === 'red'
                  ? 'text-red-500 dark:text-red-400'
                  : budgetTier === 'orange'
                    ? 'text-orange-600 dark:text-orange-400'
                    : budgetTier === 'amber'
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-emerald-600 dark:text-emerald-400'
              }`}
            >
              {budgetTier === 'red'
                ? `Перерасход: ${fmt(Math.abs(budgetDiff))} ${currency}`
                : `Сэкономлено: ${fmt(budgetDiff)} ${currency}`}
            </p>
            <p className="mt-0.5 text-[11px] text-stone-400 dark:text-stone-500">
              {fmt(totalSpent)} из {fmt(budget)} {currency} · {Math.round(budgetPct * 100)}%
            </p>
          </div>
        )}

        {/* Category breakdown */}
        {categoryBreakdown.length > 0 && (
          <div className="trip-info-card">
            <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              По категориям
            </p>
            <div className="flex flex-col gap-2.5">
              {categoryBreakdown.map(({ category, amount }) => (
                <div key={category} className="flex items-center justify-between">
                  <span className="text-[13px] font-semibold text-stone-600 dark:text-stone-300">
                    {CATEGORY_META[category as keyof typeof CATEGORY_META]?.label ?? category}
                  </span>
                  <span className="text-[13px] font-bold text-stone-900 dark:text-white">
                    {fmt(amount)} {currency}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Conversion warning */}
        {hasConversionErrors && (
          <div className="flex items-center gap-1.5 rounded-xl bg-amber-50 px-3 py-2 text-xs font-medium text-amber-600 dark:bg-amber-900/20 dark:text-amber-400">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            Некоторые валюты не удалось сконвертировать
          </div>
        )}
      </div>

      <PostTripFeedbackSheet
        open={showFeedback}
        onClose={() => setShowFeedback(false)}
        tripId={trip.id}
        destination={trip.destination}
      />
    </div>
  );
};
