import type { PlaceVisit } from '@/entities/place';
import type { LngLat } from '@/shared/lib';
import { AppInput, DateInput, Drawer, DrawerContent, DrawerHeader, DrawerTitle, FieldLabel } from '@/shared/ui';
import { Button } from '@/shared/ui';
import { Loader2 } from 'lucide-react';

import { useAddPlace } from '../model/useAddPlace';

type AddPlaceSheetProps = {
  open: boolean;
  tripId: string;
  defaultDate: string;
  initialCoords?: LngLat | null;
  initialName?: string | null;
  editingPlace?: PlaceVisit | null;
  onClose: () => void;
  onSuccess: (place: PlaceVisit) => void;
};

export const AddPlaceSheet = ({ open, tripId, defaultDate, initialCoords, initialName, editingPlace, onClose, onSuccess }: AddPlaceSheetProps) => {
  const {
    name, setName,
    visitedAt, setVisitedAt,
    notes, setNotes,
    submit,
    submitting,
    isValid,
  } = useAddPlace(tripId, defaultDate, editingPlace, open, initialCoords, initialName);

  const handleSubmit = async () => {
    const result = await submit();
    if (result) {
      onSuccess(result);
      onClose();
    }
  };

  return (
    <Drawer open={open} onOpenChange={(v) => !v && onClose()}>
      <DrawerContent className="flex max-h-[88dvh] flex-col bg-white p-0 dark:bg-[hsl(var(--surface-elevated))]">
        <DrawerHeader className="shrink-0 px-5 pb-0 pt-4">
          <DrawerTitle className="text-[20px] font-extrabold text-stone-900 dark:text-white">
            {editingPlace ? 'Редактировать место' : 'Добавить место'}
          </DrawerTitle>
        </DrawerHeader>

        <div className="flex-1 overflow-y-auto px-5 pb-2 pt-4">
          <div className="flex flex-col gap-4">
            <div>
              <FieldLabel>Название</FieldLabel>
              <AppInput
                placeholder="Токийская башня"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div>
              <FieldLabel>Дата посещения</FieldLabel>
              <DateInput
                value={visitedAt}
                placeholder="Выберите дату"
                onChange={(e) => setVisitedAt(e.target.value)}
              />
            </div>

            <div>
              <FieldLabel>Заметки</FieldLabel>
              <textarea
                className="h-20 w-full resize-none rounded-[14px] border border-stone-200 bg-stone-100 px-3.5 py-3 text-[15px] font-semibold text-stone-900 outline-none placeholder:font-normal placeholder:text-stone-400 focus:border-[1.5px] focus:border-primary dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))] dark:text-white dark:placeholder:text-stone-500"
                placeholder="Впечатления, что запомнилось..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="shrink-0 px-5 pb-8 pt-3">
          <Button
            className="h-[52px] w-full rounded-2xl text-base font-bold shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
            onClick={handleSubmit}
            disabled={!isValid || submitting}
          >
            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {editingPlace ? 'Сохранить изменения' : 'Добавить место'}
          </Button>
        </div>
      </DrawerContent>
    </Drawer>
  );
};
