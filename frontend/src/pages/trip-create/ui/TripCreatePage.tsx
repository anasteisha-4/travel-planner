import type { Trip } from '@/entities/trip';
import { TripForm } from '@/features/trips';
import { AppPageHeader, PageContent, PageLayout } from '@/shared/ui';
import { ChevronLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const TripCreatePage = () => {
  const navigate = useNavigate();

  const handleSuccess = (trip: Trip) => {
    navigate(`/trips/${trip.id}`, { replace: true });
  };

  const handleCancel = () => {
    navigate(-1);
  };

  return (
    <PageLayout fullScreen>
      <AppPageHeader pb="pb-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="flex h-9 w-9 shrink-0 items-center justify-center"
            onClick={handleCancel}
          >
            <ChevronLeft className="h-5 w-5 text-stone-700 dark:text-stone-200" />
          </button>
          <h1 className="text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
            Новая поездка
          </h1>
        </div>
      </AppPageHeader>

      <PageContent pb="pb-5" className="pt-5">
        <TripForm onSuccess={handleSuccess} />
      </PageContent>
    </PageLayout>
  );
};
