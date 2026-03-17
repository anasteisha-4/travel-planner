import { TripCard } from '@/entities/trip';
import { useTrips } from '@/features/trips';
import { AppPageHeader, EmptyState, PageContent, PageLayout, TabBar } from '@/shared/ui';
import { Calendar, Plus } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

type Tab = 'active' | 'completed';

export const TripsPage = () => {
  const navigate = useNavigate();
  const { activeTrips, completedTrips, loading } = useTrips();
  const [tab, setTab] = useState<Tab>('active');

  return (
    <PageLayout>
      <AppPageHeader pb="pb-0">
        <div className="flex items-center justify-between pb-4">
          <h1 className="text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
            Поездки
          </h1>
          <button
            type="button"
            onClick={() => navigate('/trips/new')}
            className="flex h-[30px] items-center gap-1.5 rounded-xl bg-primary px-3 text-[13px] font-semibold text-white shadow-[0_4px_12px_rgba(37,99,235,0.3)]"
          >
            <Plus className="h-3.5 w-3.5" />
            Создать
          </button>
        </div>

        <TabBar
          tabs={[
            { id: 'active', label: 'Текущие', count: activeTrips.length },
            { id: 'completed', label: 'Завершенные', count: completedTrips.length },
          ]}
          active={tab}
          onChange={setTab}
        />
      </AppPageHeader>

      <PageContent className="pt-4">
        {loading ? (
          <div className="flex flex-col gap-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="trip-info-card animate-pulse">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div className="flex flex-col gap-1.5">
                    <div className="h-4 w-36 rounded-lg bg-stone-100 dark:bg-stone-800" />
                    <div className="h-3 w-24 rounded-lg bg-stone-100 dark:bg-stone-800" />
                  </div>
                  <div className="h-5 w-20 rounded-full bg-stone-100 dark:bg-stone-800" />
                </div>
                <div className="h-3 w-48 rounded-lg bg-stone-100 dark:bg-stone-800" />
              </div>
            ))}
          </div>
        ) : tab === 'active' ? (
          activeTrips.length === 0 ? (
            <EmptyState icon={Calendar} message="Нет активных поездок" />
          ) : (
            <div className="flex flex-col gap-3">
              {activeTrips.map((trip) => (
                <TripCard key={trip.id} trip={trip} onClick={() => navigate(`/trips/${trip.id}`)} />
              ))}
            </div>
          )
        ) : completedTrips.length === 0 ? (
          <EmptyState icon={Calendar} message="Нет завершенных поездок" />
        ) : (
          <div className="flex flex-col gap-3">
            {completedTrips.map((trip) => (
              <TripCard key={trip.id} trip={trip} onClick={() => navigate(`/trips/${trip.id}`)} />
            ))}
          </div>
        )}
      </PageContent>
    </PageLayout>
  );
};
