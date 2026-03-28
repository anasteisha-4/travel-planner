import { ConfirmDrawer } from '@/shared/ui';

type CancelTripSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  destinationName: string;
  onConfirm: () => void | Promise<void>;
  loading?: boolean;
};

export const CancelTripSheet = ({
  open,
  onOpenChange,
  destinationName,
  onConfirm,
  loading,
}: CancelTripSheetProps) => (
  <ConfirmDrawer
    open={open}
    onOpenChange={onOpenChange}
    variant="warning"
    title="Отменить поездку?"
    description={`Поездка «${destinationName}» будет отменена. Вы сможете восстановить ее позже`}
    confirmLabel="Да, отменить"
    cancelLabel="Оставить поездку"
    onConfirm={onConfirm}
    loading={loading}
  />
);
