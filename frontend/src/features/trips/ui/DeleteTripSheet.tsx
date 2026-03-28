import { ConfirmDrawer } from '@/shared/ui';

type DeleteTripSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  destinationName: string;
  onConfirm: () => void | Promise<void>;
  loading?: boolean;
};

export const DeleteTripSheet = ({
  open,
  onOpenChange,
  destinationName,
  onConfirm,
  loading,
}: DeleteTripSheetProps) => (
  <ConfirmDrawer
    open={open}
    onOpenChange={onOpenChange}
    variant="delete"
    title="Удалить поездку?"
    description={`Поездка «${destinationName}» и все ее расходы будут удалены навсегда. Это действие нельзя отменить`}
    confirmLabel="Удалить навсегда"
    onConfirm={onConfirm}
    loading={loading}
  />
);
