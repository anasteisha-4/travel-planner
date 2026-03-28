import type { Trip } from '@/entities/trip';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from '@/shared/ui';
import { TripForm } from './TripForm';

type EditTripSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  trip: Trip;
  onSuccess: (trip: Trip) => void;
};

export const EditTripSheet = ({ open, onOpenChange, trip, onSuccess }: EditTripSheetProps) => (
  <Drawer open={open} onOpenChange={onOpenChange}>
    <DrawerContent className="max-h-[92dvh] overflow-y-auto bg-white px-5 pb-10 dark:bg-stone-950">
      <DrawerHeader className="mb-5 flex-row items-center justify-between">
        <DrawerTitle className="text-[20px] font-extrabold text-stone-900 dark:text-white">
          Редактировать
        </DrawerTitle>
      </DrawerHeader>
      <TripForm
        existingTrip={trip}
        onSuccess={onSuccess}
        onCancel={() => onOpenChange(false)}
        asSheet
      />
    </DrawerContent>
  </Drawer>
);
