import { ConfirmDrawer } from '@/shared/ui';

type DeleteExpenseSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void | Promise<void>;
  loading?: boolean;
};

export const DeleteExpenseSheet = ({
  open,
  onOpenChange,
  onConfirm,
  loading,
}: DeleteExpenseSheetProps) => (
  <ConfirmDrawer
    open={open}
    onOpenChange={onOpenChange}
    variant="delete"
    title="Удалить расход?"
    description="Это действие нельзя отменить. Запись о расходе будет удалена навсегда."
    confirmLabel="Удалить навсегда"
    onConfirm={onConfirm}
    loading={loading}
  />
);
