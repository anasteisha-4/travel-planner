import type { PlaceVisit } from '@/entities/place';
import { Button, ConfirmDrawer, Drawer, DrawerContent, DrawerHeader, DrawerTitle } from '@/shared/ui';
import { Calendar, Edit2, ExternalLink, Trash2 } from 'lucide-react';
import { useState } from 'react';

const formatDate = (dateStr: string): string => {
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(y, m - 1, d));
};

const openInYandexMaps = (lat: string, lon: string) => {
  window.open(`https://yandex.ru/maps/?pt=${lon},${lat}&z=16`, '_blank', 'noopener,noreferrer');
};

type PlaceDetailSheetProps = {
  place: PlaceVisit | null;
  onClose: () => void;
  onEdit: (place: PlaceVisit) => void;
  onDelete: (placeId: string) => Promise<void>;
};

export const PlaceDetailSheet = ({ place, onClose, onEdit, onDelete }: PlaceDetailSheetProps) => {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!place) return;
    setDeleting(true);
    try {
      await onDelete(place.id);
      setConfirmDelete(false);
    } finally {
      setDeleting(false);
    }
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setConfirmDelete(false);
      onClose();
    }
  };

  return (
    <>
      <Drawer open={!!place && !confirmDelete} onOpenChange={handleOpenChange}>
        <DrawerContent className="bg-white px-5 pb-10 dark:bg-[hsl(var(--surface-elevated))]">
          {place && (
            <>
              <DrawerHeader className="mb-4 pb-0">
                <DrawerTitle className="text-[22px] font-extrabold leading-tight text-stone-900 dark:text-white">
                  {place.name}
                </DrawerTitle>
              </DrawerHeader>

              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2.5 text-[14px] text-stone-500 dark:text-stone-400">
                  <Calendar className="h-4 w-4 shrink-0 text-stone-400" />
                  {formatDate(place.visited_at)}
                </div>

                {place.notes && (
                  <div className="mt-1 rounded-xl bg-stone-50 px-4 py-3 dark:bg-[hsl(var(--surface-elevated))]">
                    <p className="text-[14px] leading-relaxed text-stone-600 dark:text-stone-300">
                      {place.notes}
                    </p>
                  </div>
                )}
              </div>

              <div className="mt-6 flex flex-col gap-2.5">
                <div className="flex gap-2.5">
                  <Button
                    variant="outline"
                    className="h-[52px] flex-1 rounded-2xl border-stone-200 bg-stone-100 text-stone-700 dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))] dark:text-stone-200"
                    onClick={() => onEdit(place)}
                  >
                    <Edit2 className="mr-2 h-4 w-4" />
                    Изменить
                  </Button>
                  <Button
                    variant="outline"
                    className="h-[52px] flex-1 rounded-2xl border-stone-200 bg-stone-100 text-stone-700 dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))] dark:text-stone-200"
                    onClick={() => openInYandexMaps(place.latitude, place.longitude)}
                  >
                    <ExternalLink className="mr-2 h-4 w-4" />
                    На карте
                  </Button>
                </div>
                <button
                  type="button"
                  onClick={() => setConfirmDelete(true)}
                  className="flex h-[52px] w-full items-center justify-center gap-2 rounded-2xl border border-red-100 bg-red-50/70 text-[15px] font-semibold text-red-500 dark:border-red-900/60 dark:bg-red-900/20 dark:text-red-400"
                >
                  <Trash2 className="h-4 w-4" />
                  Удалить место
                </button>
              </div>
            </>
          )}
        </DrawerContent>
      </Drawer>

      <ConfirmDrawer
        open={!!place && confirmDelete}
        onOpenChange={(open) => !open && setConfirmDelete(false)}
        variant="delete"
        title="Удалить место?"
        description={`«${place?.name ?? ''}» будет удалено из дневника навсегда`}
        confirmLabel="Удалить навсегда"
        onConfirm={handleDelete}
        loading={deleting}
      />
    </>
  );
};
