import type { Trip, TripStatus } from '@/entities/trip';
import { tripApi } from '@/entities/trip';
import { TripForm, TripStatusBadge } from '@/features/trips';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  PageHeader,
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  useToast,
} from '@/shared/ui';
import { ArrowLeft, Calendar, Edit, Loader2, MapPin, Trash2, Users, Wallet } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

const STATUS_TRANSITIONS: Record<TripStatus, { label: string; next: TripStatus }[]> = {
  planned: [
    { label: 'Начать поездку', next: 'active' },
    { label: 'Отменить', next: 'cancelled' },
  ],
  active: [
    { label: 'Завершить', next: 'completed' },
    { label: 'Отменить', next: 'cancelled' },
  ],
  completed: [],
  cancelled: [{ label: 'Восстановить', next: 'planned' }],
};

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
};

export const TripDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [trip, setTrip] = useState<Trip | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

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
    try {
      const updated = await tripApi.updateTrip(id, { status: newStatus });
      setTrip(updated);
    } catch {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось обновить статус' });
    }
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
      setShowDeleteDialog(false);
    }
  };

  const handleEditSuccess = (updatedTrip: Trip) => {
    setTrip(updatedTrip);
    setIsEditing(false);
  };

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!trip) return null;

  const transitions = STATUS_TRANSITIONS[trip.status] ?? [];

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-4 px-4 pb-20">
      <PageHeader className="gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate('/trips')} className="shrink-0">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="flex-1 truncate text-xl font-bold tracking-tight">{trip.title}</h1>
        <TripStatusBadge status={trip.status} />
      </PageHeader>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <MapPin className="h-5 w-5 text-primary" />
            {trip.destination}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Начало</p>
              <p className="flex items-center gap-1.5 text-sm font-medium">
                <Calendar className="h-3.5 w-3.5" />
                {formatDate(trip.start_date)}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Конец</p>
              <p className="flex items-center gap-1.5 text-sm font-medium">
                <Calendar className="h-3.5 w-3.5" />
                {formatDate(trip.end_date)}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Путешественники</p>
              <p className="flex items-center gap-1.5 text-sm font-medium">
                <Users className="h-3.5 w-3.5" />
                {trip.people_count}
              </p>
            </div>
            {trip.budget && (
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Бюджет</p>
                <p className="flex items-center gap-1.5 text-sm font-medium">
                  <Wallet className="h-3.5 w-3.5" />
                  {trip.budget.toLocaleString('ru-RU')} {trip.currency}
                </p>
              </div>
            )}
          </div>

          {trip.notes && (
            <div className="space-y-1 border-t pt-2">
              <p className="text-xs text-muted-foreground">Заметки</p>
              <p className="whitespace-pre-wrap text-sm">{trip.notes}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {transitions.length > 0 && (
        <div className="flex gap-2">
          {transitions.map((t) => (
            <Button
              key={t.next}
              variant={t.next === 'cancelled' ? 'outline' : 'default'}
              className="h-11 flex-1"
              onClick={() => handleStatusChange(t.next)}
            >
              {t.label}
            </Button>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <Button variant="outline" className="h-11 flex-1" onClick={() => setIsEditing(true)}>
          <Edit className="mr-2 h-4 w-4" />
          Редактировать
        </Button>
        <Button
          variant="outline"
          className="h-11 text-destructive"
          onClick={() => setShowDeleteDialog(true)}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      <Sheet open={isEditing} onOpenChange={setIsEditing}>
        <SheetContent side="bottom" className="h-[90dvh] overflow-y-auto rounded-t-2xl">
          <SheetHeader className="pb-4">
            <SheetTitle>Редактировать поездку</SheetTitle>
          </SheetHeader>
          <TripForm
            existingTrip={trip}
            onSuccess={handleEditSuccess}
            onCancel={() => setIsEditing(false)}
          />
        </SheetContent>
      </Sheet>

      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Удалить поездку?</DialogTitle>
            <DialogDescription>
              Это действие нельзя отменить. Поездка «{trip.title}» будет удалена навсегда.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={isDeleting}
              className="flex-1"
            >
              Отмена
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
              className="flex-1"
            >
              {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Удалить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
