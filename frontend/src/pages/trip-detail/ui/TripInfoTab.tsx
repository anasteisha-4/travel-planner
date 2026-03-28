import type { TripDetailOutletContext } from './TripDetailPage';
import { Button } from '@/shared/ui';
import { Edit, Loader2, Trash2, User } from 'lucide-react';
import { useNavigate, useOutletContext } from 'react-router-dom';

const formatDateFull = (dateStr: string) => {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
  } catch {
    return dateStr;
  }
};

const formatYear = (dateStr: string) => {
  if (!dateStr) return '';
  try {
    return new Date(dateStr + 'T00:00:00').getFullYear().toString();
  } catch {
    return '';
  }
};

const getDaysDiff = (start: string, end: string) => {
  try {
    const s = new Date(start + 'T00:00:00');
    const e = new Date(end + 'T00:00:00');
    return Math.round((e.getTime() - s.getTime()) / (1000 * 60 * 60 * 24));
  } catch {
    return null;
  }
};

const CURRENCY_LABEL: Record<string, string> = {
  RUB: 'Рубль',
  USD: 'Доллар',
  EUR: 'Евро',
  GBP: 'Фунт',
  CNY: 'Юань',
  TRY: 'Лира',
};

export const TripInfoTab = () => {
  const navigate = useNavigate();
  const { trip, isStatusChanging, onStatusChange, onEditOpen, onCancelOpen, onDeleteOpen } =
    useOutletContext<TripDetailOutletContext>();

  const isCancelled = trip.status === 'cancelled';
  const isCompleted = trip.status === 'completed';
  const isActive = trip.status === 'active';
  const isPlanned = trip.status === 'planned';

  const cardBase = isCancelled ? 'trip-info-card-muted' : 'trip-info-card';

  return (
    <div className="flex-1 overflow-y-auto px-5 pb-24 pt-4">
      <div className="flex flex-col gap-3">
        {isCancelled && (
          <div className="flex items-start gap-2.5 rounded-2xl border border-red-200 bg-red-50/60 px-4 py-3 dark:border-red-900/50 dark:bg-red-900/20">
            <svg
              className="mt-0.5 h-4 w-4 shrink-0 text-red-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
              />
            </svg>
            <p className="text-[13px] font-medium text-red-600 dark:text-red-400">
              Поездка отменена. Вы можете восстановить ее или удалить навсегда
            </p>
          </div>
        )}

        {/* Dates card */}
        <div className={`${cardBase} flex gap-0`}>
          <div className="flex-1">
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Начало
            </p>
            <p className="text-[20px] font-bold leading-snug text-stone-900 dark:text-white">
              {formatDateFull(trip.start_date)}
            </p>
            <p className="mt-1.5 text-[12px] font-medium text-stone-400 dark:text-stone-500">
              {formatYear(trip.start_date)}
            </p>
          </div>
          <div className="mx-[20px] w-px self-stretch bg-stone-200 dark:bg-stone-700" />
          <div className="flex-1">
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Конец
            </p>
            <p className="text-[20px] font-bold leading-snug text-stone-900 dark:text-white">
              {formatDateFull(trip.end_date)}
            </p>
            <p className="mt-1.5 text-[12px] font-medium text-stone-400 dark:text-stone-500">
              {formatYear(trip.end_date)}
              {(() => {
                const d = getDaysDiff(trip.start_date, trip.end_date);
                if (d === null) return null;
                const label =
                  d % 10 === 1 && d % 100 !== 11
                    ? 'день'
                    : d % 10 >= 2 && d % 10 <= 4 && (d % 100 < 10 || d % 100 >= 20)
                      ? 'дня'
                      : 'дней';
                return (
                  <>
                    {' '}
                    · {d} {label}
                  </>
                );
              })()}
            </p>
          </div>
        </div>

        <div className="flex gap-3">
          <div className={`${cardBase} flex-1`}>
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Путешественники
            </p>
            <div className="flex items-center gap-1.5">
              <User className="h-5 w-5 text-[#2563EB]" />
              <p className="text-[26px] font-bold leading-none text-stone-900 dark:text-white">
                {trip.people_count}
              </p>
            </div>
            <p className="mt-0.5 text-[12px] font-medium text-stone-400 dark:text-stone-500">
              чел.
            </p>
          </div>

          <div className={`${cardBase} flex-1`}>
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Бюджет
            </p>
            <p className="text-[22px] font-bold leading-none text-stone-900 dark:text-white">
              {trip.budget ? trip.budget.toLocaleString('ru-RU') : '-'}
            </p>
            <p className="mt-1.5 text-[12px] font-medium text-stone-400 dark:text-stone-500">
              {trip.currency} · {CURRENCY_LABEL[trip.currency] ?? trip.currency}
            </p>
          </div>
        </div>

        {trip.notes && (
          <div className={cardBase}>
            <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              Заметки
            </p>
            <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-stone-700 dark:text-stone-300">
              {trip.notes}
            </p>
          </div>
        )}

        {/* Action buttons */}
        <div className="mt-1 flex flex-col gap-2.5">
          {isCancelled && (
            <Button
              className="h-[52px] w-full rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
              onClick={() => onStatusChange('planned')}
              disabled={isStatusChanging}
            >
              {isStatusChanging && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Восстановить поездку
            </Button>
          )}

          {isCompleted && (
            <Button
              className="h-[52px] w-full rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
              onClick={() => onStatusChange('active')}
              disabled={isStatusChanging}
            >
              {isStatusChanging && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Продолжить поездку
            </Button>
          )}

          {(isActive || isPlanned) && (
            <>
              <div className="flex gap-2.5">
                <Button
                  className="h-[52px] flex-1 rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
                  onClick={async () => {
                    const next = isActive ? 'completed' : 'active';
                    await onStatusChange(next);
                    if (next === 'completed')
                      navigate(`/trips/${trip.id}/analytics`, { state: { justCompleted: true } });
                  }}
                  disabled={isStatusChanging}
                >
                  {isStatusChanging && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {isActive ? 'Завершить' : 'Начать поездку'}
                </Button>
                <Button
                  variant="outline"
                  className="h-[52px] flex-1 rounded-2xl border-stone-200 bg-stone-100 text-stone-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-200"
                  onClick={onCancelOpen}
                  disabled={isStatusChanging}
                >
                  Отменить
                </Button>
              </div>
              {isActive && (
                <Button
                  variant="outline"
                  className="h-[52px] w-full rounded-2xl border-stone-200 bg-stone-100 text-stone-600 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300"
                  onClick={() => onStatusChange('planned')}
                  disabled={isStatusChanging}
                >
                  Вернуться к планированию
                </Button>
              )}
            </>
          )}

          <div className="flex gap-2.5">
            {!isCancelled && !isCompleted && (
              <Button
                variant="ghost"
                className="h-[52px] flex-1 rounded-2xl border border-stone-200 text-stone-700 hover:bg-stone-100 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"
                onClick={onEditOpen}
              >
                <Edit className="mr-2 h-4 w-4" />
                Редактировать
              </Button>
            )}
            <button
              type="button"
              className={`flex h-[52px] shrink-0 items-center justify-center rounded-2xl border border-red-100 bg-red-50/70 dark:border-red-900/60 dark:bg-red-900/20 ${isCancelled || isCompleted ? 'w-full flex-1 gap-2' : 'w-[52px]'}`}
              onClick={onDeleteOpen}
            >
              <Trash2 className="h-4 w-4 text-red-500 dark:text-red-400" />
              {(isCancelled || isCompleted) && (
                <span className="text-[15px] font-semibold text-red-500 dark:text-red-400">
                  Удалить поездку
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
