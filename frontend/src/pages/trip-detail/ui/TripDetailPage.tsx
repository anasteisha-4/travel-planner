import type { TripStatus } from '@/entities/trip';
import { CancelTripSheet, DeleteTripSheet, EditTripSheet, useTripDetail } from '@/features/trips';
import { StatusBadge, TabBar } from '@/shared/ui';
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

type TabId = 'analytics' | 'info' | 'expenses' | 'diary';

export const TripDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const { trip, loading, handleStatusChange, isStatusChanging, handleDelete, isDeleting, invalidateTrip } =
    useTripDetail(id);

  const [showEditSheet, setShowEditSheet] = useState(false);
  const [showCancelSheet, setShowCancelSheet] = useState(false);
  const [showDeleteSheet, setShowDeleteSheet] = useState(false);

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
    : pathname.endsWith('/diary')
      ? 'diary'
      : pathname.endsWith('/expenses')
        ? 'expenses'
        : 'info';

  const isCompleted = trip?.status === 'completed';

  const TABS: { id: TabId; label: string }[] = [
    ...(isCompleted ? [{ id: 'analytics' as const, label: 'Итоги' }] : []),
    { id: 'info', label: 'О\u00a0поездке' },
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
    <div className="flex h-full flex-col">
      <div
        className="shrink-0 px-5 pb-2"
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
            className={`text-[38px] font-extrabold leading-none tracking-tight ${
              trip.status === 'cancelled'
                ? 'text-stone-400 dark:text-stone-500'
                : 'text-stone-900 dark:text-white'
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

        <div className="mt-4 border-b border-stone-200 dark:border-stone-700">
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
      />

      <CancelTripSheet
        open={showCancelSheet}
        onOpenChange={setShowCancelSheet}
        destinationName={trip.destination}
        onConfirm={handleCancelConfirm}
        loading={isStatusChanging}
      />

      <DeleteTripSheet
        open={showDeleteSheet}
        onOpenChange={setShowDeleteSheet}
        destinationName={trip.destination}
        onConfirm={handleDeleteConfirm}
        loading={isDeleting}
      />
    </div>
  );
};
