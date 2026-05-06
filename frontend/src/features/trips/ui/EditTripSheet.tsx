import type { Trip } from '@/entities/trip';
import { AdaptiveSheet } from '@/shared/ui';
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
  <AdaptiveSheet
    open={open}
    onOpenChange={onOpenChange}
    title="Редактировать поездку"
    description="Изменение дат, бюджета и деталей поездки"
    bodyClassName="pb-6"
  >
    <TripForm
      existingTrip={trip}
      onSuccess={onSuccess}
      onCancel={() => onOpenChange(false)}
      onSnapshotChange={onSnapshotChange}
      validationSlot={validationSlot}
      asSheet
    />
  </AdaptiveSheet>
);
