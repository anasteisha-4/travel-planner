import type { Trip } from '@/entities/trip';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from '@/shared/ui';
import type { ReactNode } from 'react';
import type { TripFormSnapshot } from '../model/useTripForm';
import { TripForm } from './TripForm';

type EditTripSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  trip: Trip;
  onSuccess: (trip: Trip) => void;
  onSnapshotChange?: (snapshot: TripFormSnapshot) => void;
  validationSlot?: ReactNode;
};

export const EditTripSheet = ({
  open,
  onOpenChange,
  trip,
  onSuccess,
  onSnapshotChange,
  validationSlot,
}: EditTripSheetProps) => (
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
        onSnapshotChange={onSnapshotChange}
        validationSlot={validationSlot}
        asSheet
      />
    </DrawerContent>
  </Drawer>
);
