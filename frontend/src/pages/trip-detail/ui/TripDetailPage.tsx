import { expenseApi } from '@/entities/expense';
import type { TripStatus } from '@/entities/trip';
import { profileApi } from '@/features/profile';
import { DestinationValidationCompact } from '@/features/recommendations';
import {
  CancelTripSheet,
  DeleteTripSheet,
  EditTripSheet,
  useTripDetail,
  type TripFormSnapshot,
} from '@/features/trips';
import { localizeDestinationName, useDebouncedValue } from '@/shared/lib';
import { StatusBadge, TabBar } from '@/shared/ui';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, Loader2, MapPin } from 'lucide-react';
import { useState } from 'react';
import { Navigate, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom';

export type TripDetailOutletContext = {
  trip: NonNullable<ReturnType<typeof useTripDetail>['trip']>;
  isStatusChanging: boolean;
  onStatusChange: (status: TripStatus) => Promise<void>;
  onEditOpen: () => void;
  onCancelOpen: () => void;
  onDeleteOpen: () => void;
};

type TabId = 'analytics' | 'info' | 'itinerary' | 'expenses' | 'diary';

const getDurationDays = (startDate?: string, endDate?: string) => {
  if (!startDate || !endDate) return 1;
  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T00:00:00`);
  const diffMs = end.getTime() - start.getTime();
  if (!Number.isFinite(diffMs) || diffMs < 0) return 1;
  return Math.floor(diffMs / 86_400_000) + 1;
};

const getTravelMonth = (startDate?: string) => {
  if (!startDate) return new Date().getMonth() + 1;
  const parsed = new Date(`${startDate}T00:00:00`);
  return Number.isFinite(parsed.getTime()) ? parsed.getMonth() + 1 : new Date().getMonth() + 1;
};

export const TripDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const {
    trip,
    loading,
    handleStatusChange,
    isStatusChanging,
    handleDelete,
    isDeleting,
    invalidateTrip,
  } = useTripDetail(id);
  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: profileApi.getProfile,
    retry: 1,
  });

  const [showEditSheet, setShowEditSheet] = useState(false);
  const [showCancelSheet, setShowCancelSheet] = useState(false);
  const [showDeleteSheet, setShowDeleteSheet] = useState(false);
  const [editSnapshot, setEditSnapshot] = useState<TripFormSnapshot | null>(null);
  const debouncedEditSnapshot = useDebouncedValue(editSnapshot, 450);

  const validationBudget = debouncedEditSnapshot?.budget ?? trip?.budget ?? -1;
  const validationCurrency = debouncedEditSnapshot?.currency ?? trip?.currency ?? 'RUB';
  const validationPeopleCount = debouncedEditSnapshot?.people_count ?? trip?.people_count ?? 1;
  const validationStartDate = debouncedEditSnapshot?.start_date ?? trip?.start_date;
  const validationEndDate = debouncedEditSnapshot?.end_date ?? trip?.end_date;
  const validationDurationDays = getDurationDays(validationStartDate, validationEndDate);
  const validationDestinationId =
    debouncedEditSnapshot?.destination_id ?? trip?.destination_id ?? null;
  const isValidationBudgetUnlimited = validationBudget < 0;
  const needsUsdRate = !!trip && validationBudget > 0 && validationCurrency !== 'USD';
  const { data: validationRates } = useQuery({
    queryKey: ['exchange-rates', validationCurrency],
    queryFn: () => expenseApi.getExchangeRates(validationCurrency),
    enabled: needsUsdRate,
    staleTime: 60 * 60 * 1000,
    retry: 1,
  });
  const validationBudgetUsd = isValidationBudgetUnlimited
    ? null
    : validationCurrency === 'USD'
      ? validationBudget
      : validationBudget === 0
        ? 0
        : validationRates?.rates.USD
          ? validationBudget * validationRates.rates.USD
          : null;
  const validationBudgetPerDayUsd =
    validationBudgetUsd !== null
      ? validationBudgetUsd / Math.max(validationDurationDays * validationPeopleCount, 1)
      : null;

  const handleCancelConfirm = async () => {
    await handleStatusChange('cancelled');
    setShowCancelSheet(false);
  };

  const handleDeleteConfirm = async () => {
    await handleDelete();
    setShowDeleteSheet(false);
  };

  const handleEditSuccess = () => {
    invalidateTrip();
    setShowEditSheet(false);
  };

  const activeTab: TabId = pathname.endsWith('/analytics')
    ? 'analytics'
    : pathname.endsWith('/itinerary')
      ? 'itinerary'
      : pathname.endsWith('/diary')
        ? 'diary'
        : pathname.endsWith('/expenses')
          ? 'expenses'
          : 'info';

  const isCompleted = trip?.status === 'completed';

  const TABS: { id: TabId; label: string }[] = [
    ...(isCompleted ? [{ id: 'analytics' as const, label: 'Итоги' }] : []),
    { id: 'info', label: 'О\u00a0поездке' },
    { id: 'itinerary', label: 'Маршрут' },
    { id: 'expenses', label: 'Расходы' },
    { id: 'diary', label: 'Дневник' },
  ];

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!trip) return null;

  if (pathname === `/trips/${id}`) {
    return <Navigate to={`/trips/${id}/${isCompleted ? 'analytics' : 'info'}`} replace />;
  }

  const context: TripDetailOutletContext = {
    trip,
    isStatusChanging,
    onStatusChange: handleStatusChange,
    onEditOpen: () => setShowEditSheet(true),
    onCancelOpen: () => setShowCancelSheet(true),
    onDeleteOpen: () => setShowDeleteSheet(true),
  };

  return (
    <div className="flex h-full flex-col bg-[hsl(var(--app-bg))]">
      <div
        className="shrink-0 pb-2"
        style={{ paddingTop: 'max(env(safe-area-inset-top, 0px), 20px)' }}
      >
        <div className="flex items-center justify-between">
          <button
            type="button"
            className="flex h-[38px] w-[38px] items-center justify-center"
            onClick={() => navigate('/trips')}
          >
            <ChevronLeft className="h-5 w-5 text-stone-700 dark:text-stone-200" />
          </button>
          <StatusBadge status={trip.status} />
        </div>

        <div className="mt-3">
          <h1
            className={`line-clamp-2 text-[38px] font-extrabold leading-none tracking-tight ${
              trip.status === 'cancelled'
                ? 'text-stone-400 dark:text-stone-500'
                : 'text-stone-900 dark:text-white'
            }`}
            style={{ letterSpacing: '-0.02em' }}
          >
            {localizeDestinationName(trip.destination)}
          </h1>
          {trip.departure_city && (
            <p className="mt-2 flex items-center gap-1 text-[14px] font-medium text-stone-400 dark:text-slate-500">
              <MapPin className="h-3.5 w-3.5 shrink-0" />
              <span className="line-clamp-2">
                {trip.departure_city} → {localizeDestinationName(trip.destination)}
              </span>
            </p>
          )}
        </div>

        <div className="no-scrollbar mt-4 overflow-x-auto border-b border-[hsl(var(--surface-border))]">
          <TabBar
            tabs={TABS}
            active={activeTab}
            onChange={(tabId) => navigate(`/trips/${id}/${tabId}`)}
            className="border-b-0"
          />
        </div>
      </div>

      <Outlet context={context} />

      <EditTripSheet
        open={showEditSheet}
        onOpenChange={setShowEditSheet}
        trip={trip}
        onSuccess={handleEditSuccess}
        onSnapshotChange={setEditSnapshot}
        validationSlot={
          <DestinationValidationCompact
            destinationId={validationDestinationId}
            travelMonth={getTravelMonth(validationStartDate)}
            budgetPerDayUsd={validationBudgetPerDayUsd}
            budgetUnlimited={isValidationBudgetUnlimited}
            citizenshipCode={profile?.citizenship_code}
            durationDays={validationDurationDays}
            riskTolerance={profile?.risk_tolerance}
            preferredLanguage={
              profile?.language_comfort?.find((language) => language !== 'any') ?? null
            }
          />
        }
      />

      <CancelTripSheet
        open={showCancelSheet}
        onOpenChange={setShowCancelSheet}
        destinationName={localizeDestinationName(trip.destination)}
        onConfirm={handleCancelConfirm}
        loading={isStatusChanging}
      />

      <DeleteTripSheet
        open={showDeleteSheet}
        onOpenChange={setShowDeleteSheet}
        destinationName={localizeDestinationName(trip.destination)}
        onConfirm={handleDeleteConfirm}
        loading={isDeleting}
      />
    </div>
  );
};
