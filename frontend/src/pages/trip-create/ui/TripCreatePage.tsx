import type { Trip } from '@/entities/trip';
import { TripForm } from '@/features/trips';
import { ArrowLeft } from 'lucide-react';
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
    <div
      className="-mx-4 flex h-[100dvh] flex-col bg-white dark:bg-stone-950"
    >
      <div
        className="shrink-0 px-5 pb-3"
        style={{ paddingTop: 'max(env(safe-area-inset-top, 0px), 20px)' }}
      >
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-stone-200 bg-stone-100 dark:border-stone-700 dark:bg-stone-800"
            onClick={handleCancel}
          >
            <ArrowLeft className="h-4 w-4 text-stone-700 dark:text-stone-200" />
          </button>
          <h1 className="text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
            Новая поездка
          </h1>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 pb-4">
        <TripForm onSuccess={handleSuccess} onCancel={handleCancel} />
      </div>
    </div>
  );
};
