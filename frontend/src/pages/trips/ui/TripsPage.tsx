import { TripCard } from '@/entities/trip';
import { useTrips } from '@/features/trips';
import { Button, PageHeader, Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui';
import { Loader2, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const TripsPage = () => {
  const navigate = useNavigate();
  const { activeTrips, completedTrips, loading } = useTrips();

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-4 px-4 pb-20">
      <PageHeader className="justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Поездки</h1>
        <Button size="sm" onClick={() => navigate('/trips/new')} className="h-10">
          <Plus className="mr-1.5 h-4 w-4" />
          Создать
        </Button>
      </PageHeader>

      <Tabs defaultValue="active" className="flex-1">
        <TabsList className="grid h-11 w-full grid-cols-2">
          <TabsTrigger value="active" className="text-sm">
            Текущие ({activeTrips.length})
          </TabsTrigger>
          <TabsTrigger value="completed" className="text-sm">
            Завершённые ({completedTrips.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="mt-4 space-y-3">
          {activeTrips.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <p className="mb-4">Нет активных поездок</p>
              <Button onClick={() => navigate('/trips/new')}>
                <Plus className="mr-2 h-4 w-4" />
                Создать первую поездку
              </Button>
            </div>
          ) : (
            activeTrips.map((trip) => (
              <TripCard key={trip.id} trip={trip} onClick={() => navigate(`/trips/${trip.id}`)} />
            ))
          )}
        </TabsContent>

        <TabsContent value="completed" className="mt-4 space-y-3">
          {completedTrips.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <p>Завершённых поездок пока нет</p>
            </div>
          ) : (
            completedTrips.map((trip) => (
              <TripCard key={trip.id} trip={trip} onClick={() => navigate(`/trips/${trip.id}`)} />
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};
