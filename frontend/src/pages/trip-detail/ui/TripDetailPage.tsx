import type { Expense } from '@/entities/expense';
import type { Trip, TripStatus } from '@/entities/trip';
import { tripApi } from '@/entities/trip';
import { ExpenseForm, ExpenseList, ExpenseSummary, useExpenses } from '@/features/expenses';
import { TripForm } from '@/features/trips';
import { Button, Drawer, DrawerContent, DrawerHeader, DrawerTitle, useToast } from '@/shared/ui';
import { ArrowLeft, Edit, Loader2, MapPin, Plus, Trash2, User } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

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

const STATUS_LABEL: Record<TripStatus, string> = {
  planned: 'Запланирована',
  active: 'В пути',
  completed: 'Завершена',
  cancelled: 'Отменена',
};

const STATUS_BADGE_CLASS: Record<TripStatus, string> = {
  planned:
    'border-green-200/60 bg-green-50/80 text-green-700 dark:border-green-800/60 dark:bg-green-900/30 dark:text-green-400',
  active:
    'border-amber-300/50 bg-amber-50/80 text-amber-700 dark:border-amber-700/50 dark:bg-amber-900/30 dark:text-amber-400',
  completed:
    'border-stone-200 bg-stone-100 text-stone-500 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-400',
  cancelled:
    'border-red-200/60 bg-red-50/80 text-red-600 dark:border-red-800/60 dark:bg-red-900/30 dark:text-red-400',
};

type TabId = 'info' | 'expenses';

export const TripDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [trip, setTrip] = useState<Trip | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabId>('info');
  const [showEditSheet, setShowEditSheet] = useState(false);
  const [showCancelSheet, setShowCancelSheet] = useState(false);
  const [showDeleteSheet, setShowDeleteSheet] = useState(false);
  const [isStatusChanging, setIsStatusChanging] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [editingExpense, setEditingExpense] = useState<Expense | undefined>(undefined);
  const [deletingExpenseId, setDeletingExpenseId] = useState<string | null>(null);
  const [isDeletingExpense, setIsDeletingExpense] = useState(false);

  const {
    expenses,
    convertedSummary,
    loading: expensesLoading,
    refetch: refetchExpenses,
    removeExpense,
  } = useExpenses(id ?? '', trip?.currency ?? 'RUB');

  const fetchTrip = useCallback(async () => {
    if (!id) return;
    try {
      const data = await tripApi.getTrip(id);
      setTrip(data);
    } catch {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Поездка не найдена' });
      navigate('/trips', { replace: true });
    } finally {
      setLoading(false);
    }
  }, [id, navigate, toast]);

  useEffect(() => {
    fetchTrip();
  }, [fetchTrip]);

  const handleStatusChange = async (newStatus: TripStatus) => {
    if (!id) return;
    setIsStatusChanging(true);
    try {
      const updated = await tripApi.updateTrip(id, { status: newStatus });
      setTrip(updated);
    } catch {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось обновить статус' });
    } finally {
      setIsStatusChanging(false);
    }
  };

  const handleCancelConfirm = async () => {
    await handleStatusChange('cancelled');
    setShowCancelSheet(false);
  };

  const handleDelete = async () => {
    if (!id) return;
    setIsDeleting(true);
    try {
      await tripApi.deleteTrip(id);
      toast({ title: 'Готово', description: 'Поездка удалена' });
      navigate('/trips', { replace: true });
    } catch {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось удалить поездку' });
    } finally {
      setIsDeleting(false);
      setShowDeleteSheet(false);
    }
  };

  const handleEditSuccess = (updatedTrip: Trip) => {
    setTrip(updatedTrip);
    setShowEditSheet(false);
  };

  const handleEditExpense = (expense: Expense) => {
    setEditingExpense(expense);
    setShowExpenseForm(true);
  };

  const handleExpenseFormClose = (open: boolean) => {
    if (!open) setEditingExpense(undefined);
    setShowExpenseForm(open);
  };

  const handleExpenseDeleteRequest = () => {
    if (editingExpense) setDeletingExpenseId(editingExpense.id);
  };

  const handleDeleteExpense = async () => {
    if (!deletingExpenseId) return;
    setIsDeletingExpense(true);
    try {
      await removeExpense(deletingExpenseId);
      setDeletingExpenseId(null);
    } finally {
      setIsDeletingExpense(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!trip) return null;

  const isCancelled = trip.status === 'cancelled';
  const isCompleted = trip.status === 'completed';
  const isActive = trip.status === 'active';
  const isPlanned = trip.status === 'planned';

  const cardBase = isCancelled ? 'trip-info-card-muted' : 'trip-info-card';

  return (
    <div className="flex h-full flex-col">
      <div
        className="shrink-0 px-5 pb-2"
        style={{ paddingTop: 'max(env(safe-area-inset-top, 0px), 16px)' }}
      >
        <div className="flex items-center justify-between">
          <button
            type="button"
            className="flex h-[38px] w-[38px] items-center justify-center rounded-full border border-stone-200 bg-stone-100 dark:border-stone-700 dark:bg-stone-800"
            onClick={() => navigate('/trips')}
          >
            <ArrowLeft className="h-4 w-4 text-stone-700 dark:text-stone-200" />
          </button>
          <span
            className={`rounded-full border px-3.5 py-1.5 text-[12px] font-semibold ${STATUS_BADGE_CLASS[trip.status]}`}
          >
            {STATUS_LABEL[trip.status]}
          </span>
        </div>

        <div className="mt-3">
          <h1
            className={`text-[38px] font-extrabold leading-none tracking-tight ${
              isCancelled ? 'text-stone-400 dark:text-stone-500' : 'text-stone-900 dark:text-white'
            }`}
            style={{ letterSpacing: '-0.02em' }}
          >
            {trip.destination}
          </h1>
          {trip.departure_city && (
            <p className="mt-2 flex items-center gap-1 text-[14px] font-medium text-stone-400 dark:text-stone-500">
              <MapPin className="h-3.5 w-3.5 shrink-0" />
              {trip.departure_city} → {trip.destination}
            </p>
          )}
        </div>

        <div className="mt-4 flex items-end gap-5 border-b border-stone-200 dark:border-stone-700">
          {(['info', 'expenses'] as TabId[]).map((tab) => (
            <button
              key={tab}
              type="button"
              className={`pb-3 text-[15px] font-semibold transition-colors ${
                activeTab === tab
                  ? 'border-b-[2.5px] border-primary text-primary'
                  : 'text-stone-400 dark:text-stone-500'
              }`}
              onClick={() => setActiveTab(tab)}
            >
              {tab === 'info' ? 'О поездке' : 'Расходы'}
            </button>
          ))}
          <div className="flex-1" />
          {activeTab === 'expenses' && !isCompleted && !isCancelled && (
            <button
              type="button"
              className="mb-2 flex h-[30px] shrink-0 items-center gap-1.5 rounded-xl bg-[#2563EB] px-3 text-[12px] font-semibold text-white shadow-[0_3px_10px_rgba(37,99,235,0.3)]"
              onClick={() => {
                setEditingExpense(undefined);
                setShowExpenseForm(true);
              }}
            >
              <Plus className="h-3.5 w-3.5" />
              Расход
            </button>
          )}
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-5 pb-24 pt-4">
        {activeTab === 'info' && (
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
                  Поездка отменена. Вы можете восстановить её или удалить навсегда.
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
                <p className="text-[12px] font-medium text-stone-400 dark:text-stone-500">
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
                <p className="text-[12px] font-medium text-stone-400 dark:text-stone-500">
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
                <p className="text-[12px] font-medium text-stone-400 dark:text-stone-500">
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
                  onClick={() => handleStatusChange('planned')}
                  disabled={isStatusChanging}
                >
                  {isStatusChanging && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Восстановить поездку
                </Button>
              )}

              {isCompleted && (
                <Button
                  className="h-[52px] w-full rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
                  onClick={() => handleStatusChange('active')}
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
                      onClick={() => handleStatusChange(isActive ? 'completed' : 'active')}
                      disabled={isStatusChanging}
                    >
                      {isStatusChanging && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {isActive ? 'Завершить' : 'Начать поездку'}
                    </Button>
                    <Button
                      variant="outline"
                      className="h-[52px] flex-1 rounded-2xl border-stone-200 bg-stone-100 text-stone-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-200"
                      onClick={() => setShowCancelSheet(true)}
                      disabled={isStatusChanging}
                    >
                      Отменить
                    </Button>
                  </div>
                  {isActive && (
                    <Button
                      variant="outline"
                      className="h-[52px] w-full rounded-2xl border-stone-200 bg-stone-100 text-stone-600 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300"
                      onClick={() => handleStatusChange('planned')}
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
                    onClick={() => setShowEditSheet(true)}
                  >
                    <Edit className="mr-2 h-4 w-4" />
                    Редактировать
                  </Button>
                )}
                <button
                  type="button"
                  className={`flex h-[52px] shrink-0 items-center justify-center rounded-2xl border border-red-100 bg-red-50/70 dark:border-red-900/60 dark:bg-red-900/20 ${isCancelled || isCompleted ? 'w-full flex-1 gap-2' : 'w-[52px]'}`}
                  onClick={() => setShowDeleteSheet(true)}
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
        )}

        {activeTab === 'expenses' && (
          <div className="flex flex-col gap-3">
            {expensesLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-stone-400" />
              </div>
            ) : (
              <>
                {convertedSummary && (
                  <ExpenseSummary summary={convertedSummary} budget={trip.budget} />
                )}
                <ExpenseList
                  expenses={expenses}
                  onEdit={handleEditExpense}
                  readonly={isCompleted || isCancelled}
                />
              </>
            )}
          </div>
        )}
      </div>

      {id && (
        <ExpenseForm
          tripId={id}
          open={showExpenseForm}
          onOpenChange={handleExpenseFormClose}
          existingExpense={editingExpense}
          onSuccess={refetchExpenses}
          onDeleteRequest={editingExpense ? handleExpenseDeleteRequest : undefined}
        />
      )}

      {/* Delete expense confirmation sheet */}
      <Drawer
        open={!!deletingExpenseId}
        onOpenChange={(open) => !open && setDeletingExpenseId(null)}
      >
        <DrawerContent className="bg-white px-5 pb-10 dark:bg-stone-950">
          <div className="mb-6 flex flex-col items-center text-center">
            <div className="confirmation-sheet-icon mb-4 border border-red-100/80 bg-red-50/80 dark:border-red-900/60 dark:bg-red-900/20">
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#EF4444"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="3,6 5,6 21,6" />
                <path d="M19,6l-1,14H6L5,6" />
                <path d="M10,11v6" />
                <path d="M14,11v6" />
                <path d="M9,6V4h6v2" />
              </svg>
            </div>
            <DrawerHeader>
              <DrawerTitle className="text-[22px] font-extrabold text-stone-900 dark:text-white">
                Удалить расход?
              </DrawerTitle>
            </DrawerHeader>
            <p className="mt-1.5 text-sm text-stone-400 dark:text-stone-500">
              Это действие нельзя отменить. Запись о расходе будет удалена навсегда.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <Button
              variant="destructive"
              className="h-[52px] w-full rounded-2xl text-base font-bold"
              onClick={handleDeleteExpense}
              disabled={isDeletingExpense}
            >
              {isDeletingExpense && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Удалить навсегда
            </Button>
            <Button
              variant="outline"
              className="h-[52px] w-full rounded-2xl border-stone-200 bg-stone-100 text-base font-bold text-stone-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-200"
              onClick={() => setDeletingExpenseId(null)}
              disabled={isDeletingExpense}
            >
              Отмена
            </Button>
          </div>
        </DrawerContent>
      </Drawer>

      {/* Edit sheet */}
      <Drawer open={showEditSheet} onOpenChange={setShowEditSheet}>
        <DrawerContent className="max-h-[92dvh] overflow-y-auto bg-white px-5 pb-10 dark:bg-stone-950">
          <DrawerHeader className="mb-5 flex-row items-center justify-between">
            <DrawerTitle className="text-[20px] font-extrabold text-stone-900 dark:text-white">
              Редактировать
            </DrawerTitle>
          </DrawerHeader>
          <TripForm
            existingTrip={trip}
            onSuccess={handleEditSuccess}
            onCancel={() => setShowEditSheet(false)}
            asSheet
          />
        </DrawerContent>
      </Drawer>

      {/* Cancel sheet */}
      <Drawer open={showCancelSheet} onOpenChange={setShowCancelSheet}>
        <DrawerContent className="bg-white px-5 pb-10 dark:bg-stone-950">
          <div className="mb-6 flex flex-col items-center text-center">
            <div className="confirmation-sheet-icon mb-4 border border-amber-200/80 bg-amber-50/80 dark:border-amber-800/60 dark:bg-amber-900/20">
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#D97706"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <DrawerHeader>
              <DrawerTitle className="text-[22px] font-extrabold text-stone-900 dark:text-white">
                Отменить поездку?
              </DrawerTitle>
            </DrawerHeader>
            <p className="mt-1.5 text-sm text-stone-400 dark:text-stone-500">
              Поездка в «{trip.destination}» будет отменена. Вы сможете восстановить её позже.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <button
              type="button"
              className="flex h-[52px] w-full items-center justify-center rounded-2xl border border-amber-300 bg-transparent text-base font-bold text-amber-700 disabled:opacity-50 dark:border-amber-700 dark:text-amber-400"
              onClick={handleCancelConfirm}
              disabled={isStatusChanging}
            >
              {isStatusChanging && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Да, отменить
            </button>
            <Button
              className="h-[52px] w-full rounded-2xl shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
              onClick={() => setShowCancelSheet(false)}
              disabled={isStatusChanging}
            >
              Оставить поездку
            </Button>
          </div>
        </DrawerContent>
      </Drawer>

      {/* Delete sheet */}
      <Drawer open={showDeleteSheet} onOpenChange={setShowDeleteSheet}>
        <DrawerContent className="bg-white px-5 pb-10 dark:bg-stone-950">
          <div className="mb-6 flex flex-col items-center text-center">
            <div className="confirmation-sheet-icon mb-4 border border-red-100/80 bg-red-50/80 dark:border-red-900/60 dark:bg-red-900/20">
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#EF4444"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="3,6 5,6 21,6" />
                <path d="M19,6l-1,14H6L5,6" />
                <path d="M10,11v6" />
                <path d="M14,11v6" />
                <path d="M9,6V4h6v2" />
              </svg>
            </div>
            <DrawerHeader>
              <DrawerTitle className="text-[22px] font-extrabold text-stone-900 dark:text-white">
                Удалить поездку?
              </DrawerTitle>
            </DrawerHeader>
            <p className="mt-1.5 text-sm text-stone-400 dark:text-stone-500">
              Поездка в «{trip.destination}» и все её расходы будут удалены навсегда. Это действие
              нельзя отменить.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <Button
              variant="destructive"
              className="h-[52px] w-full rounded-2xl text-base font-bold"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Удалить навсегда
            </Button>
            <Button
              variant="outline"
              className="h-[52px] w-full rounded-2xl border-stone-200 bg-stone-100 text-base font-bold text-stone-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-200"
              onClick={() => setShowDeleteSheet(false)}
              disabled={isDeleting}
            >
              Отмена
            </Button>
          </div>
        </DrawerContent>
      </Drawer>
    </div>
  );
};
