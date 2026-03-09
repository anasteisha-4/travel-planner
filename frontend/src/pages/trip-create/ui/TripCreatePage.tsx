import type { Trip } from '@/entities/trip';
import { TripForm } from '@/features/trips';
import { Button, PageHeader } from '@/shared/ui';
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
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col overflow-y-auto overflow-x-hidden pb-20">
      <PageHeader className="gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)} className="shrink-0">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="flex-1 truncate text-xl font-bold tracking-tight">Новая поездка</h1>
      </PageHeader>
      <div className="px-4">
        <TripForm onSuccess={handleSuccess} onCancel={handleCancel} />
      </div>
    </div>
  );
};
