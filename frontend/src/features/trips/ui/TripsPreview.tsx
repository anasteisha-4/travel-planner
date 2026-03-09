import type { Trip } from '@/entities/trip';
import { TripCard, tripApi } from '@/entities/trip';
import { useIsOnline } from '@/shared/lib';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/shared/ui';
import { Calendar, MapPin, Plus } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export const TripsPreview = () => {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const isOnline = useIsOnline();

  useEffect(() => {
    const fetchTrips = async () => {
      try {
        const data = await tripApi.getTrips();
        setTrips(data.slice(0, 3));
      } catch {
        setTrips([]);
      } finally {
        setLoading(false);
      }
    };
    fetchTrips();
  }, []);

  return (
    <div className="space-y-4">
      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <MapPin className="h-5 w-5 text-primary" /> Поездки
            </CardTitle>
            {trips.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="text-xs text-primary"
                onClick={() => navigate('/trips')}
              >
                Все поездки
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="flex justify-center py-6">
              <div className="flex flex-col items-center">
                <div className="mb-2 h-8 w-8 rounded-full bg-primary/20" />
                <div className="h-3 w-24 rounded bg-primary/20" />
              </div>
            </div>
          ) : trips.length === 0 ? (
            <div className="py-6 text-center">
              <div className="mx-auto mb-5 flex h-[72px] w-[72px] items-center justify-center rounded-full bg-primary/10">
                <Calendar className="h-8 w-8 text-primary" />
              </div>
              <h3 className="mb-4 text-[19px] font-semibold leading-tight text-foreground">
                Нет поездок
              </h3>
              <Button
                className="h-12 w-full rounded-xl text-[17px] font-medium shadow-sm transition-transform active:scale-[0.98]"
                onClick={() => navigate('/trips/new')}
                disabled={!isOnline}
              >
                <Plus className="mr-2 h-5 w-5" />
                Спланировать поездку
              </Button>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                {trips.map((trip) => (
                  <TripCard
                    key={trip.id}
                    trip={trip}
                    onClick={() => navigate(`/trips/${trip.id}`)}
                  />
                ))}
              </div>
              <Button
                variant="outline"
                className="h-11 w-full"
                onClick={() => navigate('/trips/new')}
                disabled={!isOnline}
              >
                <Plus className="mr-2 h-4 w-4" />
                Новая поездка
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
